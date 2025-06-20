import os
import pandas as pd

def web_scrap(url: str, id: str, save_dir: str, output_filename: str) -> None:
    df_raw = pd.read_html(url, attrs={"id": id})[0]
    if not output_filename.endswith(".csv"):
        raise ValueError("Output should be a csv file!")
    output_dir = os.path.join(save_dir, output_filename)
    df_raw.to_csv(output_dir)
    
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str)
    parser.add_argument("--id", type=str)
    parser.add_argument("--save-dir", type=str)
    parser.add_argument("--output-filename", type=str)
    
    args = parser.parse_args()
    web_scrap(url=args.url, id=args.id, save_dir=args.save_dir, output_filename=args.output_filename)