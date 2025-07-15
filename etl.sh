#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status
set -o pipefail

export SEASON_RANGE=$1
export DB_PATH="./etl/soccer_analysis.db"
export INGESTION_DIR='./etl/ingestion'
export STAGING_DIR='./etl/staging'

echo "===START THE ETL PROCESS==="
echo "$(date)"

echo "=== STEP 1: Extract data from the web ==="
echo "=== Possession Data ==="
python3 etl/extract.py --season-range $SEASON_RANGE --stats "possession" --attr-id "stats_possession" --ingestion-dir $INGESTION_DIR 
echo "=== Goal Creation Data ==="
python3 etl/extract.py --season-range $SEASON_RANGE --stats "gca" --attr-id "stats_gca" --ingestion-dir $INGESTION_DIR
echo "=== Passing Data ==="
python3 etl/extract.py --season-range $SEASON_RANGE --stats "passing" --attr-id "stats_passing" --ingestion-dir $INGESTION_DIR
echo "=== Standard Data ==="
python3 etl/extract.py --season-range $SEASON_RANGE --stats "stats" --attr-id "stats_standard" --ingestion-dir $INGESTION_DIR

echo "=== STEP 2: Clean raw data ==="
find $INGESTION_DIR -name "*.csv" | tee >> "$INGESTION_DIR/ingestion_file_paths.txt"
python3 etl/transform.py --ingestion-dir $INGESTION_DIR --staging-dir $STAGING_DIR

echo "=== STEP 3: Load data into the database ==="
find $STAGING_DIR -name "*.csv" | tee >> "$STAGING_DIR/staging_file_paths.txt"
python3 etl/load.py --db-path $DB_PATH --staging-dir $STAGING_DIR