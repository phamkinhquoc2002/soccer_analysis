import os
import pandas as pd
import sqlite3

class SQLiteManager:
    def __init__(self, db_path: str, save_dir: str):
        #Path to the SQLite Database
        self.DB_PATH = db_path
        self.SAVE_DIR = save_dir

    def get_connetion(self):
        return sqlite3.connect(self.DB_PATH)

    def query_executor(self, query: str, filename: str) -> str:
        """Execute a query and save the return data table in serving stage directory. """
        if not filename.endswith(".csv"):
            raise ValueError("You must change your filename into a csv filename.")
        with self.get_connetion() as conn:
            try:
                df = pd.read_sql_query(query, conn)
                final_df_dir = os.path.join(self.SAVE_DIR, filename)
                df.to_csv(final_df_dir)
                return final_df_dir
            except Exception as e:
                return f"There is an error during query execution: {e}"
            
    def get_schema(self, table_name: str) -> str:
        """Return the schema of the table."""
        with self.get_connetion() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    f'PRAGMA table_info({table_name})'
                )
                rows = cursor.fetchall()
                if not rows:
                    raise ValueError(f"There was no info about the table {table_name}")
                return "\n".join(row for row in rows)
            except Exception as e:
                return f"There is an error during schema extraction: {e}"