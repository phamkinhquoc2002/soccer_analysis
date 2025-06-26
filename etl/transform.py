import os
import pandas as pd

def generate_file_names(ingestion_dir:str, file_names: list[str]) -> list[str]:
    return [os.path.join(ingestion_dir, file_name) for file_name in file_names]

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
    file_name = os.path.basename(file_name).replace(".csv", "_cleaned.csv")
    output_path = os.path.join(staging_dir, file_name)
    final_df.to_csv(output_path, index=False)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--ingestion_file_path', type=str)
    parser.add_argument('--staging_dir', type=str)
    args = parser.parse_args()
    clean(args.ingestion_file_path, args.staging_dir)