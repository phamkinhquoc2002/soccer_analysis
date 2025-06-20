import os
import pandas as pd

def generate_file_names(folder_path:str, tag: str) -> list[str]:
    return [os.path.join(folder_path, f"{tag}_{i}_{i+1}.csv") for i in range(2017, 2025)]

def rename(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if str(col).endswith(".1"):
            df.rename(columns={ col:(str(col).split(".")[0] + "_90")}, inplace=True) 
    return df
    
def column_clean(file_names: list, base_output_path:str) -> None:
    for file_name in file_names:
        df_raw = pd.read_csv(file_name, header=1)
        df_filtered = rename(df_raw)
        df_filtered.drop(columns="Unnamed: 0", inplace=True)
        df_filtered.fillna(0.0)

        final_df=df_filtered[df_filtered["Rk"] != "Rk"]
        base_name = os.path.basename(file_name).replace(".csv", "_cleaned.csv")
        output_path = os.path.join(base_output_path, base_name)
        final_df.to_csv(output_path, index=False)
        
def main(input_path: str, output_path: str, tag: str) -> None:
    files = generate_file_names(folder_path=input_path, tag=tag)
    column_clean(files, output_path)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-path', type=str)
    parser.add_argument('--output-path', type=str)
    parser.add_argument('--tag', type=str)
    args = parser.parse_args()
    main(args.input_path, args.output_path)