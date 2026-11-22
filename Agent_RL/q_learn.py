import argparse
import json
import random
import shlex
import struct
import sys
from collections import Counter

import numpy as np

ACTIONS = ["ALLOW", "CONDITIONAL", "BLOCK"]
N_ACTIONS = len(ACTIONS)


def calculate_reward_simple(action, severity):
    # severity: 0, 1, 2, 3, 4
    # action: 0 (ALLOW), 1 (CONDITIONAL), 2 (BLOCK)
    
    # --- REGULA 1: Nivel 0 si 1 -> ALLOW (0) ---
    if severity in [0, 1]:
        if action == 0:
            return 1.0   
        else:
            return -0.5  

    # --- REGULA 2: Nivel 2 si 3 -> CONDITIONAL (1) ---
    elif severity in [2, 3]:
        if action == 1:
            return 1.0    
        else:
            return -0.5

    # --- REGULA 3: Nivel 4 -> BLOCK (2) ---
    elif severity == 4:
        if action == 2:
            return 1.0 
        else:
            return -5.0   
    
    return 0.0

ACTION_MAP = {
    "ALLOW": 0,
    "CONDITIONAL": 1,
    "BLOCK": 2
}

SEVERITY_MAP = {
    "very_low": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4
}

REWARD_TABLE = {}
for sev_str, sev_int in SEVERITY_MAP.items():
    REWARD_TABLE[sev_str] = {}
    for act_str, act_int in ACTION_MAP.items():
        REWARD_TABLE[sev_str][act_str] = calculate_reward_simple(act_int, sev_int)

"""
REWARD_TABLE = {
    'very_low': {'ALLOW': 1.0, 'CONDITIONAL': -0.5, 'BLOCK': -0.5},
    'low':      {'ALLOW': 1.0, 'CONDITIONAL': -0.5, 'BLOCK': -0.5},
    'medium':   {'ALLOW': -0.5, 'CONDITIONAL': 1.0, 'BLOCK': -0.5},
    'high':     {'ALLOW': -0.5, 'CONDITIONAL': 1.0, 'BLOCK': -0.5},
    'critical': {'ALLOW': -5.0, 'CONDITIONAL': -5.0, 'BLOCK': 1.0}
}
"""

file_path = r"C:\Users\victor\Documents\dissertation_victor\q_learning_RL_agent\dataset\curated_cleaned.jsonl"

# ==========================================
# 1. Tokenize command string
# ==========================================

def tokenize_command(command: str):
    # Folosim un lexer care intelege operatorii de Linux/Bash
    lexer = shlex.shlex(command, posix=True, punctuation_chars='|;&<>')
    
    # Nu trata '#' automat ca inceput de comentariu
    lexer.commenters = ""
    
    # IMPORTANT: whitespace-ul separa tokenii si nu devine token
    lexer.whitespace_split = True
    
    tokens = list(lexer)
    
    # Eliminam orice token gol / doar whitespace
    tokens = [
        token
        for token in tokens
        if token.strip() != ""
    ]
    
    return tokens

# ---------------------------------------------------------------------------
# 2. Feature hashing -- inlocuieste vocabularul dinamic al TfidfVectorizer
#    cu o dimensiune FIXA (hashing trick, ca in Vowpal Wabbit). Hash propriu
#    (FNV-1a) in loc de hash() din Python, pentru ca hash() e randomizat intre
#    rulari (PYTHONHASHSEED) -- am avea nevoie de indecsi STABILI, reproductibili
#    in C.
# ---------------------------------------------------------------------------

# valoarea hash pentru token dat ca input va fi mereu acelasi hash (determinist) - algo FNV-1a
def hash_token(token: str, n_features: int) -> int:
    h = 2166136261
    for byte in token.encode("utf-8"):
        h ^= byte
        h = (h * 16777619) & 0xFFFFFFFF
    return h % n_features

# Input: the tokens extracted from the given command
def featurize(tokens, n_features: int) -> np.ndarray:
    # Initialize a zero vector for the fixed-size feature space
    vec = np.zeros(n_features, dtype=np.float32)
    
    # Map each token to a hashed index and increment its frequency (Bag-of-Words)
    for tok in tokens:
        vec[hash_token(tok, n_features)] += 1.0
        
    # We must normalize because if we compare a short command vs. a long command:
    # Command A (short): rm file.txt
    # Command B (long): rm file.txt; rm file2.txt; rm file3.txt ...
    # 
    # Although both commands essentially do a similar thing, the second command 
    # would get an exaggeratedly high (negative) score just because it is longer.
    # This affects the learning process because it would penalize the model 
    # much more than the reward we provided. We don't want a minor mistake 
    # to result in a massive penalty simply due to the command length.
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


# ---------------------------------------------------------------------------
# 3. Politica liniara Q(s, a) = w_a . phi(s) + b_a
# ---------------------------------------------------------------------------

class LinearQPolicy:
    def __init__(self, n_features: int, n_actions: int = N_ACTIONS):
            # numarul total de token l-am setat sa fie fix la 4096 chiar daca noi defapt am avea mai putini sau poate mai multi
            # dar ideea este ca trebuie sa mearga pentru xv6 asa ca trebuie ceva micut
            self.n_features = n_features
            
            # 3 actiuni = {allow, conditional, block}
            self.n_actions = n_actions
            
            #                feature 1   feature 2   feature 3   ... feature 1000
            #ALLOW           w11         w12         w13              ...
            #CONDITIONAL     w21         w22         w23              ...
            #BLOCK           w31         w32         w33              ...
            self.W = np.zeros((n_actions, n_features), dtype=np.float32)
            
            # b[0] → bias ALLOW
            # b[1] → bias CONDITIONAL
            # b[2] → bias BLOCK
            self.b = np.zeros(n_actions, dtype=np.float32)

    def q_values(self, phi: np.ndarray) -> np.ndarray:
        return self.W @ phi + self.b

    # cum alege actiunea - aici e mecanismul epsilon-greedy
    # Explorarea este necesara pentru ca agentul sa nu aleaga mereu aceeasi actiune.
    def act(self, phi: np.ndarray, epsilon: float) -> int:
        if random.random() < epsilon:
            return random.randrange(self.n_actions)
        return int(np.argmax(self.q_values(phi)))

    def update(self, phi: np.ndarray, action: int, reward: float, alpha: float):
        # Factor discount = 0 ==> favorizeaza alegerile imediate
        # Pentru clasificarea comenzilor tale, o comanda este tratata practic ca un context independent.
        # Nu exista ceva de tipul: comanda 1 → actiune → stare 2 → actiune → stare 3 → ...
        
        # Cat de departe este predictia mea actuala de recompensa pe care am primit-o?
        td_error = reward - self.q_values(phi)[action]
        
        # Foarte important: se actualizeaza doar randul pentru actiunea aleasa.
        # Caracteristica care are valoarea mai mare în phi primeste o modificare mai mare.
        self.W[action] += alpha * td_error * phi
        
        # Bias-ul este ajustat in aceeasi directie.
        self.b[action] += alpha * td_error

    # salveaza modelul
    def save(self, path: str):
        with open(path, "wb") as f:
            f.write(struct.pack("<II", self.n_actions, self.n_features))
            f.write(self.W.astype("<f4").tobytes())
            f.write(self.b.astype("<f4").tobytes())

    @classmethod
    def load(cls, path: str) -> "LinearQPolicy":
        with open(path, "rb") as f:
            n_actions, n_features = struct.unpack("<II", f.read(8))
            w_bytes = f.read(n_actions * n_features * 4)
            b_bytes = f.read(n_actions * 4)
        policy = cls(n_features, n_actions)
        policy.W[:] = np.frombuffer(w_bytes, dtype="<f4").reshape(n_actions, n_features)
        policy.b[:] = np.frombuffer(b_bytes, dtype="<f4")
        return policy
    
    def save_as_c_header(self, filepath: str, scale_factor: int = 10000):
        """
        Exportă greutățile și bias-urile într-un format C compatibil cu xv6,
        transformând numerele float în întregi (Fixed-Point Arithmetic).
        Formateaza fisierul punand 16 valori pe rand, pentru a evita limitarea VS Code
        legata de lungimea maxima a unei linii.
        """
        # Fortam formatul utf-8
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("#ifndef POLICY_WEIGHTS_H\n#define POLICY_WEIGHTS_H\n\n")
            f.write(f"#define N_FEATURES {self.n_features}\n")
            f.write(f"#define N_ACTIONS {self.n_actions}\n")
            f.write(f"#define SCALE_FACTOR {scale_factor}\n\n")
            
            f.write("int W[N_ACTIONS][N_FEATURES] = {\n")
            for i in range(self.n_actions):
                f.write("    {\n")
                row_vals = [str(int(val * scale_factor)) for val in self.W[i]]
                
                # Punem cate 16 numere pe un singur rand ca sa poata fi citit in VS Code
                for j in range(0, len(row_vals), 16):
                    chunk = row_vals[j:j+16]
                    f.write("        " + ", ".join(chunk))
                    
                    # Daca nu suntem la ultimul chunk, punem virgula si trecem la rand nou
                    if j + 16 < len(row_vals):
                        f.write(",\n")
                    else:
                        f.write("\n")
                
                f.write("    }")
                if i < self.n_actions - 1:
                    f.write(",\n")
                else:
                    f.write("\n")
            f.write("};\n\n")
            
            b_vals = [str(int(val * scale_factor)) for val in self.b]
            f.write("int b[N_ACTIONS] = {\n    " + ", ".join(b_vals) + "\n};\n\n")
            
            f.write("#endif\n")

# ---------------------------------------------------------------------------
# 4. Dataset (acelasi format JSONL: {"command": ..., "label": ...})
# ---------------------------------------------------------------------------

def load_dataset(path: str):
    samples = []
    skipped = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            try:
                tokens = tokenize_command(data["command"])
            except ValueError:
                skipped += 1
                continue
            if not tokens:
                skipped += 1
                continue
            samples.append((tokens, data["label"]))
    if skipped:
        print(f"[info] {skipped} comenzi ignorate (sintaxa invalida / goale)")
    return samples


# ---------------------------------------------------------------------------
# 5. Bucla de antrenare
# ---------------------------------------------------------------------------

def train(
    dataset_path: str,
    out_path: str,
    n_features: int,
    epochs: int,
    alpha: float,
    eps_start: float,
    eps_end: float,
    seed: int,
    history_csv: str | None = None,
):
    random.seed(seed)
    np.random.seed(seed)

    samples = load_dataset(dataset_path)
    print(f"Comenzi incarcate: {len(samples)}")

    labels_seen = Counter(label for _, label in samples)
    unknown = set(labels_seen) - set(REWARD_TABLE)
    if unknown:
        print(f"[atentie] etichete fara intrare in REWARD_TABLE (recompensa=0): {sorted(unknown)}")
    print("Distributie etichete:", dict(labels_seen))

    policy = LinearQPolicy(n_features, N_ACTIONS)
    history = []

    for epoch in range(epochs):
        random.shuffle(samples)
        epsilon = eps_start + (eps_end - eps_start) * (epoch / max(1, epochs - 1))
        total_reward = 0.0

        for tokens, label in samples:
            # Pentru o comanda, mai intai obtii vectorul de caracteristici
            phi = featurize(tokens, n_features)
            
            action = policy.act(phi, epsilon)
            
            # Ia recompensa corespunzatoare etichetei reale (label) si actiunii pe care a ales-o agentul (action). 
            # Daca nu gasesti recompensa, foloseste 0.0
            reward = REWARD_TABLE.get(label, {}).get(ACTIONS[action], 0.0)
            
            policy.update(phi, action, reward, alpha)
            
            total_reward += reward

        avg_reward = total_reward / max(1, len(samples))
        
        history.append((epoch + 1, epsilon, avg_reward))
        print(f"Epoca {epoch + 1:02d}/{epochs} | epsilon={epsilon:.3f} | recompensa medie={avg_reward:.3f}")

    policy.save(out_path)
    print(f"\nPolitica antrenata (W, b) salvata in: {out_path}")

    if history_csv:
        with open(history_csv, "w", encoding="utf-8") as f:
            f.write("epoch,epsilon,avg_reward\n")
            for row in history:
                f.write(f"{row[0]},{row[1]:.4f},{row[2]:.4f}\n")
        print(f"Istoric antrenare (pentru grafic in disertatie) salvat in: {history_csv}")

    return policy


def predict(policy: LinearQPolicy, command: str):
    tokens = tokenize_command(command)
    phi = featurize(tokens, policy.n_features)
    q = policy.q_values(phi)
    best = int(np.argmax(q))
    return ACTIONS[best], dict(zip(ACTIONS, (float(x) for x in q)))

# ---------------------------------------------------------------------------
# 6. Evaluare model (Validation)
# ---------------------------------------------------------------------------
def evaluate_model(policy: LinearQPolicy, validation_path: str):
    print(f"\n[EVALUARE] Incarcare dataset din: {validation_path}")
    
    validation_samples = load_dataset(validation_path)
    
    if not validation_samples:
        print("[EVALUARE] Nu s-au gasit comenzi valide pentru evaluare.")
        return

    correct_predictions = 0
    total_predictions = len(validation_samples)
    
    # Lista cu toate label-urile originale din validation_cleaned.jsonl
    original_labels = [label for _, label in validation_samples]
    
    # Mapare label -> actiunea corecta
    expected_action = {
        "very_low": "ALLOW",
        "low": "ALLOW",
        "medium": "CONDITIONAL",
        "high": "CONDITIONAL",
        "critical": "BLOCK"
    }

    # Iteram direct prin sample-urile deja curățate
    for tokens, original_label in validation_samples:
        # Preluăm logica din funcția predict(), dar aplicată direct pe tokenii deja extrași
        phi = featurize(tokens, policy.n_features)
        q = policy.q_values(phi)
        best = int(np.argmax(q))
        predicted_action = ACTIONS[best]
        
        # Contorizam
        if predicted_action == expected_action[original_label]:
            correct_predictions += 1

    # Calculam acuratetea finala
    accuracy = (correct_predictions / total_predictions) * 100.0
    
    print(
        f"[REZULTAT] Precizie (Accuracy): "
        f"{accuracy:.2f}% "
        f"({correct_predictions}/{total_predictions} comenzi clasificate corect)"
    )

# ---------------------------------------------------------------------------
# 7. CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Antreneaza politica RL (linear Q-learning) pentru syscall_dispatcher.")
    parser.add_argument("--dataset", default=r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\dataset\train\train_cleaned_v2.jsonl")
    
    parser.add_argument("--test", default=r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\dataset\test\test_cleaned_v2.jsonl", help="Calea catre dataset-ul de validare")
    
    # Am pastrat salvarea binara pentru eventuale teste viitoare in Python
    parser.add_argument("--out-bin", default=r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\policy.bin", help="Calea pentru salvarea modelului Python (.bin)")
    
    # Adaugam argumentul pentru output-ul de productie (xv6)
    parser.add_argument("--out-header", default=r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\policy_weights.h", help="Calea pentru fisierul C header necesar in xv6")
    
    parser.add_argument("--history-csv", default=r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\training_history.csv")
    
    # default setam la 4096 de features
    parser.add_argument("--features", type=int, default=4096, help="dimensiunea fixa a starii (hashing trick)")
    
    # default antrenam pentru 30 epoci
    parser.add_argument("--epochs", type=int, default=200)
    
    # learning rate = 5% 
    # Asta înseamnă ca la fiecare exemplu, modelul se deplaseaza doar 5% catre recompensa observata.
    # Q_nou = Q_vechi + 0.05(r-Q_vechi)
    # rata mica face actualizarile sa fie mai conservatoare si reduce riscul ca o singura comanda sa modifice prea mult greutatile.
    parser.add_argument("--alpha", type=float, default=0.05)
    
    # O valoare mai mare a parametrului epsilon din cadrul metodei epsilon-greedy indica o explorare mai mare a spatiului.
    
    # Ideea este ca la început vrei ca agentul sa incerce variante diferite, iar pe masura ce invata vrei sa se bazeze din ce in ce mai mult pe ce a invatat.
    
    # 30% → alege o actiune aleatoriu (EXPLORE)
    # 70% → alege actiunea cu Q cea mai mare (EXPLOIT)
    parser.add_argument("--eps-start", type=float, default=0.3)
    
    # 2% → explorare aleatorie
    # 98% → exploatarea modelului
    parser.add_argument("--eps-end", type=float, default=0.02)
    
    # Algoritmii care generează numere „aleatoare” in calculator sunt, de fapt, pseudo-aleatori. 
    # Daca pornesc de la aceeasi valoare initială (seed), genereaza aceeasi secventa.
    # cu --seed 42 poti obtine aceeasi secventa aleatoare si, in conditii identice, antrenarea devine reproductibila.
    parser.add_argument("--seed", type=int, default=42)
    
    args = parser.parse_args()

    policy = train(
        dataset_path=args.dataset,
        out_path=args.out_bin,
        n_features=args.features,
        epochs=args.epochs,
        alpha=args.alpha,
        eps_start=args.eps_start,
        eps_end=args.eps_end,
        seed=args.seed,
        history_csv=args.history_csv,
    )

    # 2. Generam livrabilul final pentru sistemul C / xv6
    print("\n[LIVRABIL] Exportam matricea de antrenare pentru C (Fixed-Point Arithmetic)...")
    policy.save_as_c_header(args.out_header)
    print(f"[SUCCES] Fisierul header a fost generat in: {args.out_header}")
    print("Muta acest fisier in directoul sursei xv6 alaturi de rl_agent.c !")
    
    evaluate_model(policy, args.test)

if __name__ == "__main__":
    sys.exit(main())

