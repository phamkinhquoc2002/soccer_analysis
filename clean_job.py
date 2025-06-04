from pyspark.sql import SparkSession
import os

def create_spark_session(app_name="clean_job") -> SparkSession:
    return SparkSession.builder.master("local[*]").appName(app_name).getOrCreate()

def generate_file_names(start=2017, end=2025, folder_path="./data") -> list:
    return [os.path.join(folder_path, f"{i}_{i+1}.csv") for i in range(start, end)]

def column_deduplicate(cols_list):
    new_list = []
    for col in cols_list:
        if col not in new_list:
            new_list.append(col)
        elif col in new_list:
            col = col + "_90"
            new_list.append(col)
    return new_list

def column_clean(spark: SparkSession, file_names: list, base_output_path:str):
    for file_name in file_names:
        df_raw = spark.read.option("header", "false").csv(file_name)

        header_rows = df_raw.collect()[1]
        filtered_cols = [str(col) if col is not None else f"_c{i}" for i, col in enumerate(header_rows)]
        df = df_raw.rdd.zipWithIndex().filter(lambda row: row[1] > 1).map(lambda row: row[0]).collect()
        final_df = spark.createDataFrame(df, schema=column_deduplicate(filtered_cols))

        base_name = os.path.basename(file_name).replace(".csv", "_cleaned")
        output_path = os.path.join(base_output_path, base_name)
        final_df.write.option("header", "true").mode('overwrite').csv(output_path)
    return "Finish processing!"
        

def main(input_path, output_path):
    spark = create_spark_session()
    files = generate_file_names(folder_path=input_path)
    column_clean(spark, files, output_path)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-path', type=str)
    parser.add_argument('--output-path', type=str)
    args = parser.parse_args()
    main(args.input_path, args.output_path)