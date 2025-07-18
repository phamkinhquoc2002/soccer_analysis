import os
import logging
from typing import List
import pandas as pd
import sqlite3
from resources import metrics_resource
from mcp.server import FastMCP

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SQLiteManager:
    """
    Handles direct interactions with the SQLite database, including executing queries and retrieving table schemas.
    """
    def __init__(self, db_path: str, serving_dir: str):
        """
        Initialize the SQLiteManager.
        Args:
            db_path (str): Path to the SQLite database file.
            serving_dir (str): Directory where result CSVs will be saved.
        """
        self.DB_PATH = db_path
        self.SERVING_DIR = serving_dir

    def get_connetion(self):
        """
        Establish a new SQLite connection.
        Returns:
            sqlite3.Connection: SQLite connection object.
        """
        return sqlite3.connect(self.DB_PATH)

    def query_executor(self, query: str, file_name: str) -> str:
        """
        Execute an SQL query and save the resulting data table as a CSV file in the serving directory.
        Args:
            query (str): SQL query to execute.
            file_name (str): Name of the CSV file to save results.
        Returns:
            str: File name if successful, or error message if failed.
        Raises:
            ValueError: If file_name does not end with .csv
        """
        if not file_name.endswith(".csv"):
            return "You must change your filename into a csv filename."
        with self.get_connetion() as conn:
            try:
                df = pd.read_sql_query(query, conn)
                final_df_dir = os.path.join(self.SERVING_DIR, file_name)
                df.to_csv(final_df_dir)
                return file_name
            except Exception as e:
                return f"There is an error during query execution: {e}"

    def get_schema(self, table_name: str) -> str:
        """
        Retrieve the schema (column info) of a given table.
        Args:
            table_name (str): Name of the table.
        Returns:
            str: Schema information or error message.
        """
        with self.get_connetion() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(f'PRAGMA table_info("{table_name}")')
                rows = cursor.fetchall()
                return f"Info about {table_name}:\n" + "\n".join(str(row) for row in rows)
            except Exception as e:
                return f"There is an error during schema extraction: {e}"
            
    def get_list_tables(self) -> str:
        """
        Retrieve the tables info in the database.
        Returns:
        str: Tables information in the database.
        """
        with self.get_connetion() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                rows = cursor.fetchall()
                if not rows:
                    return "There was no info about the tables in the database"
                return "The tables in the database are:\n" + "\n".join(str(row) for row in rows)
            except Exception as e:
                return f"There is an error during schema extraction: {e}"

class DatabaseServer:
    """
    MCP server that exposes database management tools for agent-based workflows.
    Registers tools for querying the database, retrieving schema, and fetching metric info.
    """
    def __init__(self, db_path: str, serving_dir: str):
        """
        Initialize the DatabaseServer.
        Args:
            db_path (str): Path to the SQLite database file.
            serving_dir (str): Directory where result CSVs will be saved.
        """
        self.DB_PATH = db_path
        self.SERVING_PATH = serving_dir
        self.mcp = FastMCP("analyst_server")
        self._get_db()
        self._setup_tools()

    def _get_db(self):
        """
        Initialize the SQLiteManager instance.
        """
        self.db_manager = SQLiteManager(db_path=self.DB_PATH, 
                                        serving_dir=self.SERVING_PATH)
    def _setup_tools(self):
        """
        Register available tools with the MCP server for agent use.
        Tools:
            - query: Execute SQL and save results as CSV.
            - get_schema_info: Retrieve table schema.
            - get_metrics_info: Lookup metric descriptions.
        """

        @self.mcp.tool()
        async def query(query: str, file_name: str):
            """
            Execute an SQL query and save the result as a CSV file.
            Args:
                query (str): SQL query to execute.
                file_name (str): Name of the CSV file to save results.
            Returns:
                str: File name if successful, or error message if failed.
            """
            file_name = self.db_manager.query_executor(query=query, file_name=file_name)
            return file_name

        @self.mcp.tool()
        async def get_schema_info(table_name: str):
            """
            Retrieve the schema information for a specified table.
            Args:
                table_name (str): Name of the table.
            Returns:
                str: Schema information or error message.
            """
            schema = self.db_manager.get_schema(table_name=table_name)
            return schema

        @self.mcp.tool()
        def get_metrics_info(metrics: List[str]) -> str:
            """
            Get descriptions for a list of metric names using the metrics resource. Sometimes, when you get the info of the table you want to inspect, some metrics just dont make sense, 
            please use this to understand what each column name means.
            Args:
                metrics (List[str]): List of metric names.
            Returns:
                str: Metric descriptions, one per line.
            """
            metric_info_retrieved = []
            for metric in metrics:
                if metric in metrics_resource:
                    metric_info_retrieved.append(f"{metric} stands for {metrics_resource[metric]}")
                else:
                    metric_info_retrieved.append(f"""Can't find any information related to metric {metric} in the database. There are two reasons:
                    1. The metric name is incorrect.
                    2. The metric is not available in the database.
                    For the first case, you should inspect the schema of the table to understand what are the metrics were stored there.""")
            return '\n'.join(metric_info_retrieved)
        
        @self.mcp.tool()
        def get_tables_list() -> str:
            """
            Get general info of all the table in the database.
            Returns:
                str: Tables Information.
            """
            tables_info = self.db_manager.get_list_tables()
            return tables_info
            
    def run(self):
        """
        Start the MCP server and listen for incoming agent requests.
        """
        logger.info("Starting DatabaseServer...")
        self.mcp.run(transport="stdio")
        
if __name__=="__main__":
    DB_PATH = os.environ.get("DB_PATH", "soccer_analysis")
    SERVING_DIR = os.environ.get("SERVING_DIR")
    if not SERVING_DIR:
        logger.error("SERVING_DIR environment variable must be set!")
        raise EnvironmentError("SERVING_DIR environment variable must be set!")
    try:
        database_server = DatabaseServer(db_path=DB_PATH, serving_dir=SERVING_DIR)
        database_server.run()
    except Exception as e:
        logger.exception(f"Failed to start DatabaseServer: {e}")