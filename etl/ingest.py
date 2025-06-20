import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.environ["DB_PATH"]

def db_ingest(csv_dir: str, table_name: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_csv(csv_dir)
    df.to_sql(name=table_name, con=conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", type=str)
    parser.add_argument("--table-name", type=str)
    args = parser.parse_args()
    db_ingest(csv_dir=args.csv_dir, table_name=args.table_name)
    