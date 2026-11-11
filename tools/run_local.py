"""Runs every domain notebook locally in order with PySpark (parquet instead of Delta, one local catalog).
Usage from the repo root:  python generator/generate.py && python notebooks/build_notebooks.py && python tools/run_local.py"""
import json, sys
from pyspark.sql import SparkSession
spark = (SparkSession.builder.master("local[4]").config("spark.sql.warehouse.dir","/tmp/solvi_wh")
         .config("spark.driver.memory","4g").config("spark.sql.shuffle.partitions","8").getOrCreate())
spark.sparkContext.setLogLevel("ERROR")
def display(df): df.show(40, truncate=False)
for dom in ["core","sales","supply","delivery","assets","hseq"]:
    for step in ["01","02","03"]:
        name = {"01":"bronze","02":"silver","03":"gold"}[step]
        print(f"===== {dom} {name}", flush=True)
        g = {"spark": spark, "display": display}
        cells = json.load(open(f"./notebooks/{dom}/{step}_{dom}_{name}.ipynb"))["cells"]
        for c in cells:
            if c["cell_type"] != "code": continue
            src = "".join(c["source"]).replace('TABLE_FORMAT = "delta"','TABLE_FORMAT = "parquet"') \
                    .replace('LOCAL_PREFIX = ""', 'LOCAL_PREFIX = f"{DOMAIN}_"') \
                    .replace('LANDING_PATH = f"Files/landing/{DOMAIN}"', 'LANDING_PATH = f"./data/{DOMAIN}"')
            exec(src, g)
