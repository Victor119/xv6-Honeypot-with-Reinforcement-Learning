import json
import os
import shlex

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

# ========================================== 
# 2. Extrage comenzile invalide 
# ========================================== 
def get_invalid_commands(path: str): 
    invalid_commands = [] 
    with open(path, "r", encoding="utf-8") as f: 
        for line_number, line in enumerate(f, start=1): 
            line = line.strip() 
            
            if not line: 
                continue 
            
            data = json.loads(line) 
            command = data["command"] 
            
            try: 
                tokens = tokenize_command(command) 
                
            except ValueError: 
                invalid_commands.append(command) 
                continue 
            
            # aici prindem comenzile care au character doar space
            if not tokens: 
                invalid_commands.append(command) 
            
    return invalid_commands

# ============================================================
# FUNCTION TO REMOVE COMMANDS FROM JSONL
# ============================================================

def remove_commands_from_jsonl(input_file, output_file, commands_to_remove):

    removed = 0
    kept = 0

    with open(input_file, "r", encoding="utf-8") as infile, \
            open(output_file, "w", encoding="utf-8") as outfile:

        for line in infile:

            if not line.strip():
                continue

            data = json.loads(line)
            command = data.get("command")

            if command in commands_to_remove:
                removed += 1
            else:
                outfile.write(line)
                kept += 1

    return removed, kept


if __name__ == "__main__":

    total_invalid_commands = []

    # ==========================================
    # TRAIN
    # ==========================================

    base_train = r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\dataset"

    input_dataset_train = os.path.join(
        base_train,
        "train",
        "train_cleaned.jsonl"
    )

    invalid_train_commands = get_invalid_commands(input_dataset_train)

    for command in invalid_train_commands:
        if command not in total_invalid_commands:
            total_invalid_commands.append(command)

    print(f"Numar comenzi invalide dupa TRAIN: {len(total_invalid_commands)}")


    # ==========================================
    # VALIDATION
    # ==========================================

    base_validation = r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\dataset"

    input_dataset_validation = os.path.join(
        base_validation,
        "validation",
        "validation_cleaned.jsonl"
    )

    invalid_validation_commands = get_invalid_commands(input_dataset_validation)

    for command in invalid_validation_commands:
        if command not in total_invalid_commands:
            total_invalid_commands.append(command)

    print(f"Numar comenzi invalide dupa VALIDATION: {len(total_invalid_commands)}")


    # ==========================================
    # TEST
    # ==========================================

    base_test = r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\dataset"

    input_dataset_test = os.path.join(
        base_test,
        "test",
        "test.jsonl"
    )

    invalid_test_commands = get_invalid_commands(input_dataset_test)

    for command in invalid_test_commands:
        if command not in total_invalid_commands:
            total_invalid_commands.append(command)

    print(f"Numar comenzi invalide dupa TEST: {len(total_invalid_commands)}")
    
    # ========================================== 
    # # ELIMINARE COMENZI INVALIDE 
    # ==========================================
    
    # TRAIN
    output_dataset_train = os.path.join(base_train, "train", "train_cleaned_v2.jsonl" )
    
    removed, kept = remove_commands_from_jsonl(input_dataset_train, output_dataset_train, total_invalid_commands)
    
    # VALIDATION
    output_dataset_validation = os.path.join(base_validation, "validation", "validation_cleaned_v2.jsonl" )
    
    removed, kept = remove_commands_from_jsonl(input_dataset_validation, output_dataset_validation, total_invalid_commands)
    
    # TEST
    output_dataset_test = os.path.join(base_test, "test", "test_cleaned_v2.jsonl" )
    
    removed, kept = remove_commands_from_jsonl(input_dataset_test, output_dataset_test, total_invalid_commands)
