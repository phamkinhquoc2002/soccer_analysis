import os
import pandas as pd

def rename(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if str(col).endswith(".1"):
            df.rename(columns={ col:(str(col).split(".")[0] + "_90")}, inplace=True) 
    return df
    
def clean(ingestion_file_path: str, staging_dir:str) -> None:
    df_raw = pd.read_csv(ingestion_file_path, header=1)
    df_filtered = rename(df_raw)
    df_filtered.drop(columns="Unnamed: 0", inplace=True)
    df_filtered.fillna(0.0)

    final_df=df_filtered[df_filtered["Rk"] != "Rk"]
    ingestion_file_name = ingestion_file_path.split("/")[-1]

    staging_file_name = ingestion_file_name.replace(".csv", "_cleaned.csv")
    output_path = os.path.join(staging_dir, staging_file_name)
    final_df.to_csv(output_path, index=False)
    print(f"[+] Saved: {output_path}")

def main(ingestion_dir: str, staging_dir: str) -> None:
    with open(ingestion_dir + "/ingestion_file_paths.txt", "r") as f:
        paths = f.read().splitlines()
    for path in paths:
        clean(path, staging_dir)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingestion-dir", type=str)
    parser.add_argument("--staging-dir", type=str)
    args = parser.parse_args()
    if not os.path.exists(args.staging_dir):
        os.makedirs(args.staging_dir)
    main(ingestion_dir=args.ingestion_dir, staging_dir=args.staging_dir)