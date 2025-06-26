import os
import sqlite3
import pandas as pd

def ingest(db_path: str, path: str) -> None:
    conn = sqlite3.connect(db_path)
    df = pd.read_csv(path)
    df.to_sql(name=path.split("/")[-1].replace("_cleaned.csv", ""), con=conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()

def main(db_path: str, staging_dir: str, paths: list[str]) -> None:
    for path in paths:
        ingest(db_path, path)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", type=str)
    parser.add_argument("--staging-dir", type=str)
    args = parser.parse_args()
    with open(args.staging_dir + "/staging_file_paths.txt", "r") as f:
        paths = f.read().splitlines()
    main(db_path=args.db_path, staging_dir=args.staging_dir, paths=paths)
    