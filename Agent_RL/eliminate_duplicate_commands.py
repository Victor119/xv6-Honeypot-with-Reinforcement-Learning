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
    base = r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\dataset"

    input_dataset = os.path.join(base,"train", "train.jsonl")
    
    commands_train = []

    with open(input_dataset, "r", encoding="utf-8") as f:
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

    input_dataset_validation = os.path.join(base_validation,"validation", "validation.jsonl")
    
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
        
    # ------------------------------------------------------------
    # CASE 1:
    # The command appears in TEST and VALIDATION
    # -> remove it from VALIDATION
    # ------------------------------------------------------------

    validation_remove_case1 = test_set & validation_set

    # ------------------------------------------------------------
    # CASE 2:
    # The command appears in TRAIN and TEST
    # -> remove it from TRAIN
    # ------------------------------------------------------------

    train_remove_case2 = train_set & test_set

    # ------------------------------------------------------------
    # CASE 3:
    # The command appears in TRAIN and VALIDATION
    # -> remove it from VALIDATION
    #
    # EXCEPTION:
    # If it also appears in TEST, it is already handled by CASE 4
    # ------------------------------------------------------------

    validation_remove_case3 = (train_set & validation_set) - test_set

    # ------------------------------------------------------------
    # CASE 4:
    # The command appears in TRAIN + VALIDATION + TEST
    # -> remove it from both TRAIN and VALIDATION
    # ------------------------------------------------------------

    common_all_three = train_set & validation_set & test_set

    train_remove = train_remove_case2

    validation_remove = (
        validation_remove_case1
        | validation_remove_case3
        | common_all_three
    )

    # ============================================================
    # OUTPUT FILES
    # ============================================================

    train_cleaned = os.path.join(base, "train", "train_cleaned.jsonl")
    validation_cleaned = os.path.join(
        base, "validation", "validation_cleaned.jsonl"
    )

    # ============================================================
    # CLEAN TRAIN DATASET
    # ============================================================

    removed_train, kept_train = remove_commands_from_jsonl(
        input_dataset,
        train_cleaned,
        train_remove
    )

    # ============================================================
    # CLEAN VALIDATION DATASET
    # ============================================================

    removed_validation, kept_validation = remove_commands_from_jsonl(
        input_dataset_validation,
        validation_cleaned,
        validation_remove
    )