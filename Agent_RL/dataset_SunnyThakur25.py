import os
import pandas as pd


if __name__ == "__main__":

    # Paths
    base = r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\dataset\raw\SunnyThakur25"
    
    raw_dataset = os.path.join(base, "linux_window_priv_escalation_datatset.jsonl")
    output_dataset = os.path.join(base, "linux_datatset_cleaned.jsonl")

    print("BASE =", base)
    print("RAW DATASET =", raw_dataset)
    print("SCRIPT =", os.path.abspath(__file__))
    
    # Columns to remove
    columns_to_drop = [
        "id",
        "description",
        "category",
        "mapped_technique",
        "reference" 
    ]
    
    # column ramase: "platform", "command", "severity"

    # Check that input file exists
    if not os.path.exists(raw_dataset):
        raise FileNotFoundError(f"Dataset not found: {raw_dataset}")

    # Read JSONL
    df = pd.read_json(raw_dataset, lines=True)
    
    # Keep only Linux entries 
    df = df[df["platform"].str.strip().str.lower() == "linux"].copy()
    
    # Keep only the required columns
    cols_to_remove = [col for col in columns_to_drop if col in df.columns]

    # Drop columns
    df = df.drop(columns=cols_to_remove)
    
    # rename the column from severity into label
    df = df.rename(columns={"severity": "label"})
    
    # Convert label values to lowercase 
    df["label"] = df["label"].astype(str).str.strip().str.lower()
    
    # Remove platform column before saving 
    df = df.drop(columns=["platform"])
    
    # Save cleaned dataset as JSONL 
    df.to_json(output_dataset, orient="records", lines=True, force_ascii=False) 
    
    print(f"Cleaned dataset saved to: {output_dataset}") 
    print(f"Number of Linux entries: {len(df)}")


