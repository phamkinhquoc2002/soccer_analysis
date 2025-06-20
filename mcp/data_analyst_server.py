import os
import numpy as np
import pandas as pd
from typing import Literal, List
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from scipy.spatial.distance import cosine
from mcp.server import FastMCP
from dotenv import load_dotenv
from sqlite_manager import SQLiteManager
from concurrent.futures import ProcessPoolExecutor

load_dotenv()

DB_PATH = os.environ['DB_PATH']
STAGING_LAYER = os.environ['STAGING_LAYER']

def similarity_calculate(vec_1: np.ndarray, vec_2: np.ndarray, metric: Literal["cosine", "euclidean"]):
    if metric == "cosine":
        return 1 - cosine(vec_1, vec_2)
    elif metric == "euclidean":
        return np.linalg.norm(vec_1 - vec_2)
    else:
        raise ValueError("Wrong Metric!")
    

class DataAnalystServer:

    def __init__(self, db_path: str, staging_layer=str):
        if db_path is None:
            db_path="soccer_analysis"
        self.staging_layer = staging_layer
        self.db_manager = SQLiteManager(db_path=db_path, save_dir=self.staging_layer)
        self.mcp = FastMCP("analyst_server")
        self._setup_tools()

    def _setup_tools(self):        
        @self.mcp.tool()
        def PCA_analyze(query: str, features: list[str]) -> str:
            """
            Perform Principal Component Analysis (PCA) on selected features of a DataFrame.
            Used when user want to perform analysis over a group of players.
            
            Parameters:
            query: SQL query string used to extract data from the database.

            Returns:
            str: Full file path (directory + filename) where the PCA CSV is saved.
            """
            try:
                self.db_manager.query_executor(query=query, filename="pearson.csv")
                df = pd.read_csv(
                    os.path.join(self.staging_layer, "pearson.csv")
                )
                
                if "Player" not in df.columns:
                    raise ValueError("You need to extract 'Player' column in the query")

                features = [feature for feature in list(df.columns) if str(df[feature].dtype) == "int64" or str(df[feature].dtype) == "float64"]
                
                X_values = df[features].values
                scaler = StandardScaler()
                scaled_values = scaler.fit_transform(X_values)

                pca_converter = PCA(n_components=2)
                principal_components = pca_converter.fit_transform(scaled_values)
                pca_df = pd.DataFrame(principal_components, columns=['PCA1', 'PCA2'])
                pca_df["Player"] = df["Player"]

                save_dir = os.path.join(self.staging_layer, "pca.csv")
                pca_df.to_csv(save_dir)
                return save_dir
            except Exception as e:
                return f"There is an error while trying to calculate the PCA of the data: {e}"
            
        @self.mcp.tool()
        def similarity_score(queries: List[str], metric: Literal["cosine", "euclidean"]) -> dict:
            """
            Compute Similarity Score between one player vs other players over a set of metrics.

            Parameters:
            query: Two SQL queries. The first one is to retrieve data for the player that you want to compare, 
            the second is to retrieve data for the set of players that play the same position as the first player.

            Returns:
            dict: Similarity Scores.
            """
            try: 
                with self.db_manager.get_connetion() as conn:
                    cursor = conn.cursor()
                    cursor.execute(queries[0])
                    rel = list(cursor.fetchall()[0])
                
                self.db_manager.query_executor(query=queries[1], filename="comparision.csv")
                df = pd.read_csv(
                    os.path.join(self.staging_layer, "comparision.csv")
                )
                df.loc[len(df)] = rel

                if "Player" not in df.columns:
                    raise ValueError("You need to extract 'Player' column in the query")

                features = [feature for feature in list(df.columns) if str(df[feature].dtype) == "int64" or str(df[feature].dtype) == "float64"]
                X_values = df[features].values
                scaler = StandardScaler()
                scaled_values = scaler.fit_transform(X_values)
                scaled_values = list(scaled_values)

                similarity_scores = {"Player": df["Player"].to_list(), "Similarity_Score": []}
                metrics = [metric * df.shape[0]]
                player_to_compare = [scaled_values[len(df)] * df.shape[0]]
                with ProcessPoolExecutor(max_workers=16) as executor:
                    similarity_scores["Similarity_Score"].extend(executor.map(similarity_calculate, scaled_values, player_to_compare, metrics))
                return similarity_scores
            except Exception as e:
                return f"There is an error while trying to calculate the similarity score between players: {e}"

    def run(self):
        self.mcp.run(transport="stdio")

if __name__ == "__main__":
    data_analyst_server = DataAnalystServer(db_path=DB_PATH, staging_layer=STAGING_LAYER)
    data_analyst_server.run()