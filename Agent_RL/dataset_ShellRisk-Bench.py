import os
import pandas as pd


if __name__ == "__main__":

    # Paths
    base = r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\dataset\raw\ShellRisk-Bench"

    raw_dataset_test = os.path.join(
        base, "test-00000-of-00001.parquet"
    )

    raw_dataset_train = os.path.join(
        base, "train-00000-of-00001.parquet"
    )

    # Final output
    output_dataset = os.path.join(
        base, "shellrisk_low.jsonl"
    )

    # --------------------------------------------------
    # Load TRAIN
    # --------------------------------------------------
    print("Loading TRAIN dataset...")
    df_train = pd.read_parquet(raw_dataset_train)

    print("Original TRAIN shape:", df_train.shape)

    # Keep only command and label
    df_train = df_train[["command", "label"]]

    # Keep only not_risky
    df_train = df_train[df_train["label"] == "not_risky"].copy()

    # Rename label
    df_train["label"] = "low"

    #print("Filtered TRAIN shape:", df_train.shape)

    # --------------------------------------------------
    # Load TEST
    # --------------------------------------------------
    print("\nLoading TEST dataset...")
    df_test = pd.read_parquet(raw_dataset_test)

    print("Original TEST shape:", df_test.shape)

    # Keep only command and label
    df_test = df_test[["command", "label"]]

    # Keep only not_risky
    df_test = df_test[df_test["label"] == "not_risky"].copy()

    # Rename label
    df_test["label"] = "low"

    #print("Filtered TEST shape:", df_test.shape)

    # --------------------------------------------------
    # Combine TRAIN + TEST
    # --------------------------------------------------
    df_combined = pd.concat(
        [df_train, df_test],
        ignore_index=True
    )

    print("\nCombined dataset shape:", df_combined.shape)

    # Remove possible duplicate commands
    df_combined = df_combined.drop_duplicates(
        subset=["command"]
    ).reset_index(drop=True)

    print("After removing duplicates:", df_combined.shape)

    # --------------------------------------------------
    # Save as JSON
    # --------------------------------------------------
    df_combined.to_json(
        output_dataset,
        orient="records",
        lines=True,
        force_ascii=False
    )

    print("\nJSON saved to:")
    print(output_dataset)
