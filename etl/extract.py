import os
import pandas as pd

def web_scrap(url: str, id: str, ingestion_dir: str, file_name: str) -> None:
    df_raw = pd.read_html(url, attrs={"id": id})[0]
    if not file_name.endswith(".csv"):
        raise ValueError("Output should be a csv file!")
    output_dir = os.path.join(ingestion_dir, file_name)
    df_raw.to_csv(output_dir)
    
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str)
    parser.add_argument("--id", type=str)
    parser.add_argument("--ingestion-dir", type=str)
    parser.add_argument("--file-name", type=str)
    
    args = parser.parse_args()
    web_scrap(url=args.url, id=args.id, ingestion_dir=args.ingestion_dir, output_filename=args.file_name)