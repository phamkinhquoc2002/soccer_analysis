import os
import time
import pandas as pd
from random import uniform
from urllib.request import Request, urlopen

def generate_season_name(season_range: int) -> list[str]:
    return [f"{i}-{i+1}" for i in range(2017, season_range)]

def generate_url(seasons: list[str], stats:str) -> list[str]:
    urls = []
    for season in seasons:
        urls.append(f"https://fbref.com/en/comps/Big5/{season}/{stats}/players/{season}-Big-5-European-Leagues-Stats")
    return urls

def scrape_season(url: str, attr_id: str, season: str, ingestion_dir: str) -> None:
    try:
        headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        )
        }
        req = Request(url, headers=headers)
        with urlopen(req, timeout=15) as res:
            html = res.read()
        df_raw = pd.read_html(html, attrs={"id": attr_id}, header=1)[0]
        output_path = os.path.join(ingestion_dir, f"{attr_id}_{season}.csv")
        df_raw.to_csv(output_path, index=False)
        print(f"[+] Saved: {output_path}")
    except Exception as e:
        print(f"[!] Failed for {season}: {url} — {e}")

def web_scrape(season_range: int, stats: str, attr_id: str, ingestion_dir: str) -> None:
    seasons = generate_season_name(season_range)
    urls = generate_url(seasons, stats)
    for season, url in zip(seasons, urls):
        scrape_season(url, attr_id, season,ingestion_dir)
        sleep_time = uniform(3, 6)
        time.sleep(sleep_time)

if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--season-range", type=int)
    parser.add_argument("--stats", type=str)
    parser.add_argument("--attr-id", type=str)
    parser.add_argument("--ingestion-dir", type=str)
    args = parser.parse_args()

    if not os.path.exists(args.ingestion_dir):
        os.makedirs(args.ingestion_dir)
    web_scrape(season_range=args.season_range, stats=args.stats, attr_id=args.attr_id, ingestion_dir=args.ingestion_dir)