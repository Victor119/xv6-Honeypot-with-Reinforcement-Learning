import os
import pandas as pd


if __name__ == "__main__":
    # Path catre datasetul deja curatat
    base = r"C:\Users\victor\Documents\dissertation_victor\Agent_RL\dataset\raw\SunnyThakur25"

    input_dataset = os.path.join(base, "linux_datatset_cleaned.jsonl")
    output_dataset = os.path.join(base, "critical_linux_curated_cleaned.jsonl")

    print("BASE =", base)
    print("INPUT DATASET =", input_dataset)
    print("OUTPUT DATASET =", output_dataset)
    print("SCRIPT =", os.path.abspath(__file__))

    # Verifica existenta fisierului de intrare
    if not os.path.exists(input_dataset):
        raise FileNotFoundError(
            f"Dataset not found: {input_dataset}"
        )

    # Citeste datasetul JSON
    df = pd.read_json(input_dataset, lines=True)

    # Verifica existenta coloanei label
    if "label" not in df.columns:
        raise ValueError(
            "Column 'label' was not found in curated_cleaned.json."
        )

    # Pastreaza doar randurile cu label = very_low
    df_very_low = df[df["label"] == "critical"].copy()

    # Salveaza rezultatul ca JSON
    df_very_low.to_json(
        output_dataset,
        orient="records",
        lines=True,
        force_ascii=False
    )

    print(f"Original rows: {len(df)}")
    print(f"low rows: {len(df_very_low)}")
    print(f"low dataset saved to: {output_dataset}")
    print(f"Remaining columns: {list(df_very_low.columns)}")
