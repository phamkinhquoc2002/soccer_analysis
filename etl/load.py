import os
import sqlite3
import pandas as pd

def ingest(db_path: str, staging_dir: str, file_name:str, table_name: str) -> None:
    conn = sqlite3.connect(db_path)
    staging_file_path = os.path.join(staging_dir, file_name)
    df = pd.read_csv(staging_file_path)
    df.to_sql(name=table_name, con=conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", type=str)
    parser.add_argument("--staging-dir", type=str)
    parser.add_argument("--file-name", type=str)
    parser.add_argument("--table-name", type=str)
    args = parser.parse_args()
    ingest(db_path=args.db_path, staging_dir=args.staging_dir, file_name=args.file_name, table_name=args.table_name)
    