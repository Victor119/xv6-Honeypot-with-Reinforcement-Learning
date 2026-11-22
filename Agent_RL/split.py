import os
from pathlib import Path

# primele 0-80% din linii sunt in train, urmatoarele 10% din linii in validatation si ultimele 10% sunt in test

def create_single_file_splits():
    # Gaseste calea absoluta catre folderul unde se afla split.py (Agent_RL)
    base_dir = Path(__file__).parent
    
    input_path = base_dir / "dataset" / "raw"
    output_path = base_dir / "dataset"

    # Definim folderele și căile către cele 3 fișiere finale
    train_file = output_path / "train" / "train.jsonl"
    val_file = output_path / "validation" / "validation.jsonl"
    test_file = output_path / "test" / "test.jsonl"

    # Cream folderele daca nu exista
    for f in [train_file, val_file, test_file]:
        f.parent.mkdir(parents=True, exist_ok=True)
        # Stergem fișierele vechi daca exista, ca sa nu duplicam datele la rulari multiple
        if f.exists():
            f.unlink()

    # Lista explicita cu fisierele permise (exact structura mentionata)
    target_files = [
        "ShellRisk-Bench/shellrisk_low.jsonl",
        "SunnyThakur25/high_linux_curated_cleaned.jsonl",
        "SunnyThakur25/critical_linux_curated_cleaned.jsonl",
        "zyw-286/very_low_curated_cleaned.jsonl",
        "zyw-286/low_curated_cleaned.jsonl",
        "zyw-286/medium_curated_cleaned.jsonl",
        "zyw-286/high_curated_cleaned.jsonl",
        "zyw-286/critical_curated_cleaned.jsonl"
    ]
    
    # Construim caile complete doar pentru fisierele tinta
    jsonl_files = [input_path / f for f in target_files]
    
    if not jsonl_files:
        print(f"Nu s-au gasit fisiere .jsonl in folderul {input_path}")
        return

    # Deschidem cele 3 fisiere finale in modul 'a' (append / adaugare la final)
    with open(train_file, 'a', encoding='utf-8') as f_train, \
        open(val_file, 'a', encoding='utf-8') as f_val, \
        open(test_file, 'a', encoding='utf-8') as f_test:
        
        for file_path in jsonl_files:
            # Citim fisierul curent
            with open(file_path, 'r', encoding='utf-8') as f_in:
                lines = f_in.readlines()
            
            total_rows = len(lines)
            if total_rows == 0:
                continue

            # Calculam unde taiem (80% si 90%)
            train_cut = int(total_rows * 0.8)
            val_cut = train_cut + int(total_rows * 0.1)

            # Facem push (scriem) direct liniile in fisierele mari
            f_train.writelines(lines[:train_cut])           # 0 -> 80%
            f_val.writelines(lines[train_cut:val_cut])      # 80% -> 90%
            f_test.writelines(lines[val_cut:])              # 90% -> 100%
            
            print(f"S-au adaugat datele din: {file_path.name}")

    print("\nGata! Totul a fost extras si unit cu succes.")

if __name__ == "__main__":
    create_single_file_splits()