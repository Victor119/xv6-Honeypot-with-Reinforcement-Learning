import json
import os
import pandas as pd
import sys


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
    sys.stdout.reconfigure(encoding="utf-8")
    
    # Path catre datasetul deja curatat
    base_train = r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\dataset"

    input_dataset_train = os.path.join(base_train,"train", "train_cleaned.jsonl")
    
    commands_train = []

    with open(input_dataset_train, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            data = json.loads(line)

            if "command" in data:
                commands_train.append(data["command"])

    # Path catre datasetul deja curatat
    base_test = r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\dataset"

    input_dataset_test = os.path.join(base_test,"test", "test.jsonl")
    
    commands_test = []

    with open(input_dataset_test, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            data = json.loads(line)

            if "command" in data:
                commands_test.append(data["command"])
    
    # Path catre datasetul deja curatat
    base_validation = r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\dataset"

    input_dataset_validation = os.path.join(base_validation,"validation", "validation_cleaned.jsonl")
    
    commands_validation = []

    with open(input_dataset_validation, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            data = json.loads(line)

            if "command" in data:
                commands_validation.append(data["command"])
    
    # Convertim listele in set-uri pentru comparare rapida
    train_set = set(commands_train)
    test_set = set(commands_test)
    validation_set = set(commands_validation)

    # Comenzi care apar in cel putin doua dintre cele trei dataseturi
    repeated_commands = sorted(
        (train_set & test_set) |
        (train_set & validation_set) |
        (test_set & validation_set)
    )

    print(f"Au fost gasite {len(repeated_commands)} comenzi repetate intre dataseturi.")

    # Afisam comenzile repetate
    for command in repeated_commands:
        print(command)