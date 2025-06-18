import numpy as np
import pandas as pd
from collections import defaultdict
from typing import Optional, List
from scipy.stats import pearsonr
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from mcp.server import FastMCP

mcp = FastMCP("analyst_server")

scaler = StandardScaler()

@mcp.tool()
def pearson_correlate_analyzer(df: pd.DataFrame) -> pd.DataFrame:
    """
        Compute the Pearson correlation coefficient between two arrays.

    Parameters:
        df (pd.DataFrane): Input Dataframe.

    Returns:
        pd.Dataframe: Pearson correlation coefficient between all variables in the dataframe.

    Raises:
        ValueError: If X and Y have different lengths or are not 1-dimensional.

    Example Use Cases: Identify which stats correlate most strongly with goals, assists, xG, xA, etc.

    Example:
        >>> pearson_correlate([1, 2, 3], [4, 5, 6])
        1.0
    """
    features = df.columns
    scores = defaultdict(list)
    for i in range(0, len(features), 1):
        x = df[features[i]]
        for j in range(0, len(features), 1):
            y = df[features[j]]
            if type(x) != np.ndarray:
                x = np.asarray(x)
            if type(y) != np.ndarray:
                y = np.asarray(y)
            pearson_score = pearsonr(x, y)
            weighted_r = round(pearson_score.statistic * (1-pearson_score.pvalue), 2)
            scores[features[i]].append(weighted_r)    
    return pd.DataFrame(dict(scores), index=features)

@mcp.tool()
def PCA_analyzer(df: pd.DataFrame, features: Optional[List[str]] = None) -> float:
    """
    Perform Principal Component Analysis (PCA) on selected features of a DataFrame.

    Parameters:
        df (pd.DataFrame): Input DataFrame.
        features (Optional[List[str]]): List of column names to include in PCA. If None, use all columns.

    Returns:
        pd.DataFrame: PCA-ed Output Dataframe.
    """
    players = list(df["Player"])
    if features is not None:
        X_values = df[features].values
    scaled_values = scaler.fit_transform(X_values)
    pca_converter = PCA(n_components=2)
    principal_components = pca_converter.fit_transform(scaled_values)
    pca_df = pd.DataFrame(principal_components, columns=features)
    assert len(players) == pca_df.shape[0], "The number of players must be equal to the number of rows in the normalized DataFrame"
    pca_df["Player"] = df["Player"]
    return pca_df

@mcp.tool()
def k_means_analyzer(df: pd.DataFrame, ):
    pass

if __name__ == "__main__":
    mcp.run(transport="stdio")