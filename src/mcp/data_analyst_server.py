import os
import logging
import pandas as pd
import numpy as np
from typing import Literal, Annotated, List
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA as SKPCA
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from mcp.server import FastMCP

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def scale(df: pd.DataFrame) -> np.ndarray:
    """
    Standard scale all numeric values in the DataFrame.
    """
    features = df.select_dtypes(include=["int64", "float64"]).columns
    X_values = df[features].values
    scaler = StandardScaler()
    scaled_values = scaler.fit_transform(X_values)
    return scaled_values

class DataAnalystServer:
    """
    Analyst server for performing PCA and similarity analysis on soccer data.
    """
    def __init__(self, db_path: str, serving_dir: str):
        if not db_path:
            logger.warning("DB_PATH not provided. Using default 'soccer_analysis'.")
            db_path = "soccer_analysis"
        if not serving_dir:
            raise ValueError("SERVING_DIR must be provided!")
        self.SERVING_DIR = serving_dir
        self.mcp = FastMCP("analyst_server")
        self._setup_tools()

    def pca_analysis(self, input_file_name: str, output_file_name: str, n_components: int = 2) -> dict:
        """
        Perform Principal Component Analysis (PCA) on selected features of a DataFrame.
        Returns a dict with status and message or output file name.
        """
        try:
            file_path = os.path.join(self.SERVING_DIR, input_file_name)
            if not os.path.isfile(file_path):
                logger.error(f"Input file not found: {file_path}")
                return {"status": "error", "message": f"Input file not found: {input_file_name}"}

            df = pd.read_csv(file_path)
            if "Player" not in df.columns:
                logger.error("No 'Player' column found within the dataset.")
                return "❌:No 'Player' column found within the dataset."

            scaled_values = scale(df)

            if n_components > scaled_values.shape[1]:
                logger.error("n_components greater than number of features.")
                return "❌:n_components greater than number of features."
            pca_converter = SKPCA(n_components=n_components)
            principal_components = pca_converter.fit_transform(scaled_values)
            columns = [f'PCA{i+1}' for i in range(n_components)]

            pca_df = pd.DataFrame(principal_components, columns=columns)
            pca_df["Player"] = df["Player"]
            save_dir = os.path.join(self.SERVING_DIR, output_file_name)
            pca_df.to_csv(save_dir, index=False)
            logger.info(f"PCA Dataset saved to {save_dir}.")

            return output_file_name
        except Exception as e:
            logger.exception("Exception during PCA analysis")
            return f"❌:Exception during PCA: {e}"

    def similarity_analysis(self, input_file_name: str, output_file_name: str, metric: Literal["cosine", "euclidean"]) -> dict:
        """
        Compute similarity score between players over selected metrics.
        Returns a dict with status and message or output file name.
        """
        try:
            file_path = os.path.join(self.SERVING_DIR, input_file_name)
            if not os.path.isfile(file_path):
                logger.error(f"Input file not found: {file_path}")
                return f"❌:Input file not found: {input_file_name}"
            df = pd.read_csv(file_path)
            if "Player" not in df.columns:
                logger.error("No 'Player' column found within the dataset.")
                return "No 'Player' column found within the dataset."
            scaled_values = scale(df)

            if metric == "cosine":
                sim_matrix = cosine_similarity(scaled_values)
            elif metric == "euclidean":
                dist_matrix = euclidean_distances(scaled_values)
                sim_matrix = 1 / (1 + dist_matrix)
            else:
                logger.error(f"Unsupported metric: {metric}")
                return f"❌:Unsupported metric: {metric}"

            player_names = df["Player"].values
            df_similar_scores = pd.DataFrame(sim_matrix, index=player_names, columns=player_names)
            save_dir = os.path.join(self.SERVING_DIR, output_file_name)
            df_similar_scores.to_csv(save_dir, index=True)
            logger.info(f"Similarity Score Dataset saved to {save_dir}.")

            return output_file_name
        except Exception as e:
            logger.exception("Exception during similarity analysis")
            return f"❌:Exception during similarity analysis: {e}"
    
    def dataset_inspect(self, input_file_name: str, selected_metrics: List[str]) -> str:
        """
        Inspect the dataset. Perform general analysis to gain more insights about the dataset.
        """
        try:
            file_path = os.path.join(self.SERVING_DIR, input_file_name)
            if not os.path.isfile(file_path):
                logger.error(f"Input file not found: {file_path}")
                return f"❌:Input file not found: {input_file_name}"
            df = pd.read_csv(file_path)
            if "Player" not in df.columns:
                logger.error("No 'Player' column found within the dataset.")
                return "No 'Player' column found within the dataset."
            
            analysis_report = "GENERAL ANALYSIS REPORT"
            for metric in selected_metrics:
                analysis_report += f"Top 5 Player in terms of {metric}\n===///GENERAL STATS OF {metric}///===\n"
                analysis_report += f"- Median: {df[metric].median()}\n- 75 percentile: {df[metric].quantile(0.75)} - 90 quantile: {df[metric].quantile(0.9)}"
                std_stat = df[metric].std()
                mean_stat = df[metric].mean()
                for _, row in df[["Player", metric]].sort_values(by=metric, ascending=False).head().iterrows():
                    analysis_report += f"- Player: {row["Player"]} - {metric} Values: {row[metric]}\n"
                    outlier_check_result = self.detect_outlier(row[metric], mean_stat, std_stat)
                    if "non-outlier":
                        analysis_report += f"- Player: {row["Player"]} - {metric} Values: {row[metric]}\n"
                    else:
                        analysis_report += f"- Player: {row["Player"]} - {metric} Values: {row[metric]}\n-**OUTLIER DETECTED**: {outlier_check_result}"
            return analysis_report
        except Exception as e:
            logger.exception("Exception during general analysis")
            return f"❌:Exception during general analysis: {e}"
        
    def detect_outlier(self, mean_value, stat_value, std) -> str:
        """
        Detect outliers. Used to check if a performance is above average or not.
        """
        try:
            z_outlier = (stat_value - mean_value) / std
            if z_outlier > 3.5:
                return "Exceptionally Rare Stat - Elite"
            elif z_outlier > 4.0:
                return "Generationally Rare Stat - Legend"
            elif z_outlier > 4.5:
                return "Once-in-a-lifetime Rare Stat - GOAT tier"
            else:
                return "non-outlier"
            
        except Exception as e:
            logger.error(f"❌ Exception during outlier check: {e}")
            return f"❌:Exception during outlier check: {e}"

    def _setup_tools(self):
        @self.mcp.tool()
        def PCA_tool(input_file_name: str, output_file_name: str, n_components: int = 2) -> dict:
            """
            Tool: Perform PCA analysis. Return a dict with status and output file or error message.
            """
            return self.pca_analysis(input_file_name, output_file_name, n_components)

        @self.mcp.tool()
        def similarity_tool(input_file_name: str, output_file_name: str, metric: Literal["cosine", "euclidean"]) -> dict:
            """
            Tool: Compute similarity scores. Return a dict with status and output file or error message.
            """
            return self.similarity_analysis(input_file_name, output_file_name, metric)
        
        @self.mcp.tool()
        def general_analysis_tool(input_file_name: str, selected_metrics: Annotated[List[str], "List of selected metrics to perform general analysis"]):
            """
            Tool: Perform general analysis over the dataset. Return an analysis report of top 5 players in each selected metrics
            """
            return self.dataset_inspect(input_file_name=input_file_name, selected_metrics=selected_metrics)

    def run(self):
        logger.info("Starting DataAnalystServer...")
        self.mcp.run(transport="stdio")

if __name__ == "__main__":
    DB_PATH = os.environ.get("DB_PATH", "soccer_analysis")
    SERVING_DIR = os.environ.get("SERVING_DIR")
    if not SERVING_DIR:
        logger.error("❌:SERVING_DIR environment variable must be set!")
        raise EnvironmentError("❌:SERVING_DIR environment variable must be set!")
    try:
        data_analyst_server = DataAnalystServer(db_path=DB_PATH, serving_dir=SERVING_DIR)
        data_analyst_server.run()
    except Exception as e:
        logger.exception(f"❌:Failed to start DataAnalystServer: {e}")