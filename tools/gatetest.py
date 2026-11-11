"""Proves the quality gate works: feeds one impossible value to the Core domain and expects silver to refuse it.

Usage from the repo root, after python generator/generate.py:  python tools/gatetest.py
Exits with 0 when the gate stopped the bad data, and 1 when it let it through.
"""
import csv
import json
import os
import shutil
import sys
import tempfile

from pyspark.sql import SparkSession

work = tempfile.mkdtemp(prefix="solvigate")
shutil.copytree("data/core", os.path.join(work, "core"))

# one day of sunshine that is physically impossible: 99 kWh per square metre
path = os.path.join(work, "core", "weather_daily.csv")
rows = list(csv.reader(open(path, encoding="utf-8")))
col = rows[0].index("irradiation_kwh_m2")
rows[1][col] = "99"
csv.writer(open(path, "w", encoding="utf-8", newline="")).writerows(rows)

spark = (SparkSession.builder.master("local[2]").config("spark.sql.warehouse.dir", os.path.join(work, "wh"))
         .config("spark.sql.shuffle.partitions", "4").getOrCreate())
spark.sparkContext.setLogLevel("ERROR")
g = {"spark": spark, "display": lambda df: df.show(20, truncate=False)}

for step, layer in (("1", "bronze"), ("2", "silver")):
    cells = json.load(open(f"notebooks/core/core-{step}-{layer}.ipynb", encoding="utf-8"))["cells"]
    for c in cells:
        if c["cell_type"] != "code":
            continue
        src = ("".join(c["source"]).replace('TABLE_FORMAT = "delta"', 'TABLE_FORMAT = "parquet"')
               .replace('LOCAL_PREFIX = ""', 'LOCAL_PREFIX = "gate"')
               .replace('LANDING_PATH = f"Files/landing/{DOMAIN}"', f'LANDING_PATH = r"{os.path.join(work, "core")}"'))
        try:
            exec(src, g)
        except Exception as e:
            if layer == "silver" and "Quality gate failed" in str(e):
                print(f"\nOK: the quality gate stopped the bad value. {e}")
                sys.exit(0)
            raise

print("\nFAILED: an impossible irradiation value got through to silver.")
sys.exit(1)
