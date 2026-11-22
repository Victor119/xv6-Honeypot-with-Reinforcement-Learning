import os
import pandas as pd

def severity_to_label(severity_vi):
    """
    Map severity_vi values to the agent's action labels.

    0: 'very_low',
    1: 'low',
    2: 'medium',
    3: 'high',
    4: 'critical'
    """

    if severity_vi == 0:
        return "very_low"
    elif severity_vi == 1:
        return "low"
    elif severity_vi == 2:
        return "medium"
    elif severity_vi == 3:
        return "high"
    elif severity_vi == 4:
        return "critical"
    else:
        raise ValueError(
            f"Unknown severity_vi value: {severity_vi}. "
            f"Expected one of: 0, 1, 2, 3, 4."
        )

if __name__ == "__main__":

    # Paths
    base = r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\dataset\raw\zyw-286"

    raw_dataset = os.path.join(base, "curated.jsonl")
    output_dataset = os.path.join(base, "curated_cleaned.jsonl")

    print("BASE =", base)
    print("RAW DATASET =", raw_dataset)
    print("SCRIPT =", os.path.abspath(__file__))

    # Columns to remove
    columns_to_drop = [
        "session_id",
        "period",
        "turn_index",
        "response",
        "system_change",
        "response_source",
    ]

    # Check that input file exists
    if not os.path.exists(raw_dataset):
        raise FileNotFoundError(f"Dataset not found: {raw_dataset}")

    # Read JSONL
    df = pd.read_json(raw_dataset, lines=True)

    # Keep only columns that actually exist in the dataset
    cols_to_remove = [col for col in columns_to_drop if col in df.columns]

    # Drop columns
    df = df.drop(columns=cols_to_remove)
    
    if "severity_vi" in df.columns:
        # change from numberic to alphabet label
        df["severity_vi"] = df["severity_vi"].apply(severity_to_label)
        
        # rename the column from severity_vi into label
        df = df.rename(columns={"severity_vi": "label"})

    # Save cleaned dataset as JSONL
    df.to_json(
        output_dataset,
        orient="records",
        lines=True,
        force_ascii=False
    )

    print(f"Original shape: {df.shape[0]} rows")
    print(f"Removed columns: {cols_to_remove}")
    print(f"Cleaned dataset saved to: {output_dataset}")
    print(f"Remaining columns: {list(df.columns)}")