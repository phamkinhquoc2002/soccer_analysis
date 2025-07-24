from mcp.server import FastMCP
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VisualizationServer:
    def __init__(self, db_path: str, serving_dir: str):
        if not db_path:
            logger.warning("DB_PATH not provided. Using default 'soccer_analysis'.")
            db_path = "soccer_analysis"
        if not serving_dir:
            raise ValueError("SERVING_DIR must be provided!")
        self.SERVING_DIR = serving_dir
        self.mcp = FastMCP("visualization_server")
        self._setup_tools()
        
    def _setup_tools(self):
              
       @self.mcp.tool()
       def scatter_plot(input_file_name: str, 
                        title: str, 
                        x:str, 
                        y:str, 
                        output_file_name: str) -> str:
            """
            Generate a labeled scatter plot from a CSV file, focusing on top-performing data points.
            
            Args:
            
            input_file_name (str): Name of the input CSV file located in the serving directory.
            title (str): Title for the scatter plot.
            x (str): Column name to be used on the x-axis.
            y (str): Column name to be used on the y-axis.
            output_file_name (str): File name to save the generated plot image.
            
            Returns:
            dict: A dictionary with 'status' and 'message'. On success, 'message' contains the path to the image.
              On failure, 'message' contains the error description.
              """
            file_path = os.path.join(self.SERVING_DIR, input_file_name)
            if not os.path.isfile(file_path):
                logger.error(f"❌: Input file not found: {file_path}")
                return f"Input file not found: {input_file_name}"
            df = pd.read_csv(file_path)

            if "Player" not in df.columns:
                logger.error("No 'Player' column found within the dataset.")
                return "No 'Player' column found within the dataset."
            try:
                df[x] = (df[x] - df[x].min()) / (df[x].max() - df[x].min())
                df[y] = (df[y] - df[y].min()) / (df[y].max() - df[y].min())
                percentile_70_x = df[x].quantile(0.7)
                percentile_70_y = df[x].quantile(0.7)
                clean_df = df[
                    (
                        (df[x] >= df[x].quantile(0.7)) | (df[y] >= df[x].quantile(0.7))
                        )
                        ]
                plt.figure(figsize=(10, 6))
                ax = sns.scatterplot(data=clean_df, x=x, y=y, s=60)
                for _, row in df.iterrows():
                    if row[x] >= percentile_70_x or row[y] >= percentile_70_y:
                        ax.text(x=row[x] + 0.01, y=row[x] - 0.01, s=row['Player'], fontsize=8, ha='center', va='center')

                plt.title(title or f"{y} vs {x}")
                plt.xlabel(x)
                plt.ylabel(y)
                plt.grid(True)
                plt.savefig(output_file_name)
                plt.close()
                return output_file_name
            except Exception as e:
                logger.error(f"❌: {e}")
                return f"❌: {e}"
        
    def run(self):
        logger.info("Starting VisualizationServer...")
        self.mcp.run(transport="stdio")
        
if __name__=="__main__":
    DB_PATH = os.environ.get("DB_PATH", "soccer_analysis")
    SERVING_DIR = os.environ.get("SERVING_DIR")
    if not SERVING_DIR:
        logger.error("SERVING_DIR environment variable must be set!")
        raise EnvironmentError("SERVING_DIR environment variable must be set!")
    try:
        database_server = VisualizationServer(db_path=DB_PATH, serving_dir=SERVING_DIR)
        database_server.run()
    except Exception as e:
        logger.exception(f"Failed to start VisualizationServer: {e}")       