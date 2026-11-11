"""Builds the Fabric notebooks (.ipynb), one set per domain.

Each domain has its own workspace ("Solvi Core") and lakehouse ("Core") and owns its tables. Other domains read what they need
through OneLake shortcuts named domain + table, e.g. coredimcustomer. SHORTCUTS.md lists every shortcut to create.
Run order: core -> sales -> supply -> delivery -> assets -> hseq.
"""
import nbformat as nbf, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = ["core", "sales", "supply", "delivery", "assets", "hseq"]
NAME = {"core": "Core", "sales": "Sales", "supply": "Supply", "delivery": "Delivery", "assets": "Assets", "hseq": "HSEQ"}
OWNER = {"core": "Data platform team", "sales": "Sales lead", "supply": "Purchasing", "delivery": "Project planning",
         "assets": "Service manager", "hseq": "Quality and HSE manager"}

def common(domain):
    return f'''# Domain: {domain} · owner: {OWNER[domain]}
# Attach this notebook to the lakehouse "{NAME[domain]}" in the workspace "Solvi {NAME[domain]}".
DOMAIN = "{domain}"
LANDING_PATH = f"Files/landing/{{DOMAIN}}"   # upload this domain's CSV files here
TABLE_FORMAT = "delta"
LOCAL_PREFIX = ""                            # local testing sets this to the domain name
AS_OF = "2026-10-31"                         # demo data ends here; use the current date with live data

from pyspark.sql import functions as F, Window as W

def write_table(df, name):
    (df.write.format(TABLE_FORMAT).mode("overwrite").option("overwriteSchema", "true").saveAsTable(LOCAL_PREFIX + name))
    print(f"wrote {{name:<30}} {{df.count():>9,}} rows")

def read_table(name):                         # a table this domain owns
    return spark.read.table(LOCAL_PREFIX + name)

def read_shared(domain, name):                # another domain's table, through a OneLake shortcut named domain + name
    return spark.read.table(f"{{domain}}{{name}}")'''

# --------------------------------------------------------------------------- silver contracts
SCHEMA = {
  "site":            {"site_id":"string","municipality":"string","region":"string","country":"string","latitude":"double","longitude":"double","station_id":"string"},
  "weather_station": {"station_id":"string","name":"string","latitude":"double","longitude":"double"},
  "weather_daily":   {"station_id":"string","date":"date","irradiation_kwh_m2":"double","temp_c":"double","precip_mm":"double","snow_depth_cm":"double"},
  "weather_forecast":{"station_id":"string","issued_date":"date","date":"date","temp_min_c":"double","temp_max_c":"double","wind_ms":"double","precip_mm":"double"},
  "product":         {"product_code":"string","product_name":"string","category":"string","unit":"string","list_price_nok":"decimal(12,2)","abc_class":"string"},
  "customer":        {"customer_id":"string","customer_name":"string","segment":"string","site_id":"string","lead_source":"string","created_date":"date"},
  "seller":          {"seller_id":"string","seller_name":"string","sales_area":"string"},
  "proposal":        {"proposal_id":"string","customer_id":"string","seller_id":"string","created_date":"date","sent_date":"date","valid_until":"date","status":"string","decided_date":"date","loss_reason":"string","proposed_kwp":"double","proposal_total_nok":"decimal(14,2)"},
  "proposal_line":   {"proposal_id":"string","line_no":"int","product_code":"string","qty":"double","unit_price_nok":"decimal(12,2)","line_total_nok":"decimal(14,2)"},
  "activity":        {"activity_id":"string","proposal_id":"string","seller_id":"string","activity_date":"date","activity_type":"string","status":"string"},
  "sales_order":     {"order_id":"string","proposal_id":"string","customer_id":"string","order_date":"date","order_status":"string","order_total_nok":"decimal(14,2)"},
  "sales_order_line":{"order_id":"string","line_no":"int","proposal_id":"string","proposal_line_no":"int","product_code":"string","qty":"double","unit_price_nok":"decimal(12,2)","line_total_nok":"decimal(14,2)"},
  "invoice":         {"invoice_id":"string","order_id":"string","invoice_date":"date","amount_nok":"decimal(14,2)","invoice_type":"string"},
  "legacy_customer":   {"old_customer_no":"string","name":"string","municipality":"string"},
  "legacy_product":    {"old_item_no":"string","description":"string","category":"string"},
  "legacy_order_line": {"legacy_order_no":"string","line_no":"int","old_customer_no":"string","order_date":"date","old_item_no":"string","qty":"double","amount_nok":"decimal(14,2)"},
  "customer_xref":     {"old_customer_no":"string","customer_id":"string"},
  "product_xref":      {"old_item_no":"string","product_code":"string"},
  "supplier":        {"supplier_id":"string","supplier_name":"string","supplier_type":"string","country":"string"},
  "supplier_prequal":{"supplier_id":"string","valid_from":"date","valid_to":"date"},
  "battery_delivery":{"delivery_id":"string","order_id":"string","supplier_id":"string","batch_no":"string","delivered_date":"date","packaging_damage":"int","shock_indicator_tripped":"int","inspected_at_receipt":"int","temp_excursion":"int","storage_days":"int"},
  "crew":            {"crew_id":"string","crew_name":"string","crew_type":"string","supplier_id":"string"},
  "certification":   {"crew_id":"string","certification":"string","valid_from":"date","valid_to":"date"},
  "job":             {"job_id":"string","order_id":"string","installation_id":"string","delivery_id":"string","crew_id":"string","planned_date":"date","job_date":"date","status":"string","location":"string","ventilation_check_done":"int","sja_done":"int","battery_temp_c":"double","acclimatised":"int","commissioning_complete":"int"},
  "installation":    {"installation_id":"string","order_id":"string","customer_id":"string","site_id":"string","installed_date":"date","grid_connected_date":"date","kwp":"double","battery_kwh":"double","orientation":"string","tilt_deg":"int"},
  "production_daily":{"installation_id":"string","date":"date","kwh":"double"},
  "service_visit":   {"visit_id":"string","installation_id":"string","visit_date":"date","visit_type":"string","hours":"double","cost_nok":"decimal(12,2)"},
  "fault_log_truth": {"installation_id":"string","fault_start":"date","fault_end":"date","fault_type":"string"},
  "compliance_requirement": {"requirement_id":"string","requirement_name":"string","applies_to":"string","due_days":"int","recurring":"int"},
  "compliance_item": {"item_id":"string","installation_id":"string","requirement_id":"string","due_date":"date","submitted_date":"date"},
  "inspection_deviation": {"deviation_id":"string","installation_id":"string","found_date":"date","source":"string","category":"string","severity":"string","closed_date":"date"},
  "risk_rule":       {"factor_code":"string","factor":"string","category":"string","weight":"int","stops_work":"int"},
  "hse_event":       {"event_id":"string","job_id":"string","event_date":"date","event_type":"string","severity":"string","description":"string","reported_by":"string"},
  "hse_action":      {"action_id":"string","job_id":"string","action_date":"date","risk_level":"string","action":"string","completed":"int"},
}
DOMAIN_TABLES = {
  "core": ["site","weather_station","weather_daily","weather_forecast","product","customer"],
  "sales": ["seller","proposal","proposal_line","activity","sales_order","sales_order_line","invoice",
            "legacy_customer","legacy_product","legacy_order_line","customer_xref","product_xref"],
  "supply": ["supplier","supplier_prequal","battery_delivery"],
  "delivery": ["crew","certification","job"],
  "assets": ["installation","production_daily","service_visit","fault_log_truth"],
  "hseq": ["compliance_requirement","compliance_item","inspection_deviation","risk_rule","hse_event","hse_action"],
}
TABLE_DOMAIN = {t: d for d, ts in DOMAIN_TABLES.items() for t in ts}
KEYS = {"site":["site_id"],"weather_station":["station_id"],"weather_daily":["station_id","date"],"weather_forecast":["station_id","date"],
        "product":["product_code"],"customer":["customer_id"],"seller":["seller_id"],"proposal":["proposal_id"],"proposal_line":["proposal_id","line_no"],
        "activity":["activity_id"],"sales_order":["order_id"],"sales_order_line":["order_id","line_no"],"invoice":["invoice_id"],
        "legacy_customer":["old_customer_no"],"legacy_product":["old_item_no"],"legacy_order_line":["legacy_order_no","line_no"],
        "customer_xref":["old_customer_no"],"product_xref":["old_item_no"],"supplier":["supplier_id"],"supplier_prequal":["supplier_id","valid_from"],"battery_delivery":["delivery_id"],
        "crew":["crew_id"],"certification":["crew_id","valid_from"],"job":["job_id"],"installation":["installation_id"],
        "production_daily":["installation_id","date"],"service_visit":["visit_id"],"fault_log_truth":["installation_id","fault_start"],"compliance_requirement":["requirement_id"],
        "compliance_item":["item_id"],"inspection_deviation":["deviation_id"],"risk_rule":["factor_code"],"hse_event":["event_id"],"hse_action":["action_id"]}
FKS = [  # (child, column, parent, column) - the parent may live in another domain
  ("customer","site_id","site","site_id"), ("site","station_id","weather_station","station_id"),
  ("weather_forecast","station_id","weather_station","station_id"),
  ("proposal","customer_id","customer","customer_id"), ("proposal","seller_id","seller","seller_id"),
  ("proposal_line","proposal_id","proposal","proposal_id"), ("proposal_line","product_code","product","product_code"),
  ("activity","proposal_id","proposal","proposal_id"), ("sales_order","proposal_id","proposal","proposal_id"),
  ("sales_order_line","order_id","sales_order","order_id"), ("sales_order_line","product_code","product","product_code"),
  ("invoice","order_id","sales_order","order_id"),
  ("legacy_order_line","old_customer_no","legacy_customer","old_customer_no"), ("legacy_order_line","old_item_no","legacy_product","old_item_no"),
  ("customer_xref","customer_id","customer","customer_id"), ("product_xref","product_code","product","product_code"),
  ("battery_delivery","supplier_id","supplier","supplier_id"), ("supplier_prequal","supplier_id","supplier","supplier_id"), ("battery_delivery","order_id","sales_order","order_id"),
  ("crew","supplier_id","supplier","supplier_id"), ("certification","crew_id","crew","crew_id"),
  ("job","crew_id","crew","crew_id"), ("job","delivery_id","battery_delivery","delivery_id"), ("job","order_id","sales_order","order_id"),
  ("installation","order_id","sales_order","order_id"), ("installation","customer_id","customer","customer_id"), ("installation","site_id","site","site_id"),
  ("production_daily","installation_id","installation","installation_id"), ("service_visit","installation_id","installation","installation_id"),
  ("compliance_item","installation_id","installation","installation_id"), ("compliance_item","requirement_id","compliance_requirement","requirement_id"),
  ("inspection_deviation","installation_id","installation","installation_id"),
  ("hse_event","job_id","job","job_id"), ("hse_action","job_id","job","job_id"),
]
RANGES = [
  ("weather_daily","irradiation_kwh_m2 BETWEEN 0 AND 9"), ("weather_forecast","temp_min_c <= temp_max_c"),
  ("production_daily","kwh >= 0"), ("installation","kwp > 0 AND kwp < 1000"), ("proposal_line","qty > 0 AND unit_price_nok >= 0"),
  ("proposal","status IN ('Open','Won','Lost','Expired')"), ("proposal","sent_date >= created_date"),
  ("inspection_deviation","severity IN ('High','Medium','Low')"), ("inspection_deviation","closed_date IS NULL OR closed_date >= found_date"),
  ("legacy_order_line","order_date < '2023-01-01'"),
  ("job","status IN ('Done','Planned')"), ("job","status = 'Planned' OR installation_id IS NOT NULL"),
  ("battery_delivery","storage_days >= 0"), ("certification","valid_to > valid_from"),
  ("hse_event","event_type IN ('Incident','Near miss','Good catch')"), ("risk_rule","weight BETWEEN 1 AND 5"),
]

# Shared tables each domain reads from others (each one is a OneLake shortcut in the consuming lakehouse)
NEEDS_GOLD = {
  "sales": [("core","dimproduct")],
  "supply": [],
  "delivery": [],
  "assets": [("core","dimsite"), ("core","factweatherdaily")],
  "hseq": [("assets","diminstallation"), ("delivery","factjob"), ("supply","factbatterydelivery"), ("supply","dimsupplier"),
           ("delivery","dimcrew"), ("supply","factsupplierprequal"), ("core","dimsite"), ("core","dimcustomer"), ("core","factweatherforecast"), ("sales","factorderline")],
}

def silver_needs(domain):
    out = set()
    for c, cc, p, pc in FKS:
        if TABLE_DOMAIN[c] == domain and TABLE_DOMAIN[p] != domain:
            out.add((TABLE_DOMAIN[p], f"silver{p.replace('_', '')}"))
    return sorted(out)

# --------------------------------------------------------------------------- bronze + silver (generic per domain)
def bronze(domain):
    return [("md", f"# {NAME[domain]} 1 · Bronze\nLoads this domain's raw CSV files into `bronze*` tables, unchanged except for load metadata. Solvi is fictional; all data is generated."),
            ("code", common(domain)),
            ("code", f'''SOURCES = {json.dumps(DOMAIN_TABLES[domain])}
load_ts = F.current_timestamp()
for src in SOURCES:
    df = (spark.read.option("header", True).option("inferSchema", False).csv(f"{{LANDING_PATH}}/{{src}}.csv")
              .withColumn("_source_file", F.lit(f"{{src}}.csv")).withColumn("_loaded_at", load_ts))
    write_table(df, f"bronze{{src.replace('_', '')}}")''')]

def silver(domain):
    ts = DOMAIN_TABLES[domain]
    schema = {t: SCHEMA[t] for t in ts}; keys = {t: KEYS[t] for t in ts}
    fks = [f for f in FKS if TABLE_DOMAIN[f[0]] == domain]
    fks_src = [(c, cc, p, pc, TABLE_DOMAIN[p]) for c, cc, p, pc in fks]
    ranges = [r for r in RANGES if TABLE_DOMAIN[r[0]] == domain]
    return [("md", f"# {NAME[domain]} 2 · Silver\nTyped and checked. The **quality gate** runs every rule first; if one fails, nothing is written and silver keeps the previous version. Checks against other domains read their silver tables through shortcuts."),
            ("code", common(domain)),
            ("code", f'''SCHEMA = {json.dumps(schema, indent=1)}
KEYS = {json.dumps(keys)}
FKS = {json.dumps(fks_src)}      # child, column, parent, column, parent's domain
RANGES = {json.dumps(ranges)}

def clean(name):
    df = read_table(f"bronze{{name.replace('_', '')}}")
    return df.select(*[F.nullif(F.trim(F.col(c)), F.lit("")).cast(t).alias(c) for c, t in SCHEMA[name].items()])
silver = {{n: clean(n) for n in SCHEMA}}
def parent(table, dom):
    return silver[table] if dom == DOMAIN else read_shared(dom, f"silver{{table.replace('_', '')}}")

results = []
for t, keys in KEYS.items():
    df = silver[t]
    results += [(t, "key not null", df.filter(" OR ".join(f"{{k}} IS NULL" for k in keys)).count()),
                (t, "key unique", df.groupBy(*keys).count().filter("count > 1").count())]
for c, cc, p, pc, dom in FKS:
    orphans = silver[c].filter(F.col(cc).isNotNull()).join(parent(p, dom).select(F.col(pc).alias(cc)), cc, "left_anti").count()
    results.append((c, f"{{cc}} -> {{dom}}.{{p}}", orphans))
for t, cond in RANGES:
    results.append((t, cond, silver[t].filter(f"NOT ({{cond}})").count()))
dq = (spark.createDataFrame(results, "table string, rule string, failing_rows long")
        .withColumn("passed", F.col("failing_rows") == 0).withColumn("checked_at", F.current_timestamp()))
display(dq.orderBy("passed", "table"))
failed = dq.filter("NOT passed").count()
if failed:
    raise Exception(f"Quality gate failed in {{DOMAIN}}: {{failed}} rule(s). Nothing written to silver.")'''),
            ("code", '''for name, df in silver.items():
    write_table(df, f"silver{name.replace('_', '')}")
write_table(dq, "silverdqlog")''')]

# --------------------------------------------------------------------------- gold per domain
GOLD = {}
GOLD["core"] = [
("md", "Shared master data. Everyone reads these through shortcuts; nobody copies them."),
("code", '''dim_date = (spark.sql("SELECT explode(sequence(to_date('2012-01-01'), to_date('2027-12-31'), interval 1 day)) AS date")
  .select(F.date_format("date","yyyyMMdd").cast("int").alias("date_key"), "date", F.year("date").alias("year"),
          F.quarter("date").alias("quarter"), F.month("date").alias("month_no"), F.date_format("date","MMM").alias("month"),
          F.date_format("date","yyyy-MM").alias("year_month"), F.weekofyear("date").alias("iso_week")))
write_table(dim_date, "dimdate")
site = read_table("silversite")
write_table(site, "dimsite")
write_table(read_table("silvercustomer").join(site, "site_id"), "dimcustomer")
write_table(read_table("silverproduct"), "dimproduct")
write_table(read_table("silverweatherdaily"), "factweatherdaily")
write_table(read_table("silverweatherforecast"), "factweatherforecast")'''),
]
GOLD["sales"] = [
("md", "## Proposal outcome per proposed product\nEvery proposed line gets exactly one outcome, valued at the signed price."),
("code", '''q, ql = read_table("silverproposal"), read_table("silverproposalline")
so, sol = read_table("silversalesorder"), read_table("silversalesorderline")
write_table(read_table("silverseller"), "dimseller")
ol = (sol.filter(F.col("proposal_line_no").isNotNull())
        .select("proposal_id", F.col("proposal_line_no").alias("line_no"), F.col("product_code").alias("ordered_product"),
                F.col("qty").alias("ordered_qty"), F.col("line_total_nok").alias("ordered_value_nok")))
fql = (ql.join(q.select("proposal_id","customer_id","seller_id","created_date","status","loss_reason"), "proposal_id")
         .join(so.select("proposal_id","order_status"), "proposal_id", "left").join(ol, ["proposal_id","line_no"], "left"))
outcome = (F.when(F.col("status") == "Open", "Open").when(F.col("status") != "Won", "Proposal not accepted")
  .when(F.col("order_status") == "Cancelled", "Contract cancelled").when(F.col("ordered_product").isNull(), "Component dropped")
  .when(F.col("ordered_product") != F.col("product_code"), "Component swapped").when(F.col("ordered_qty") < F.col("qty"), "System downsized")
  .when(F.col("ordered_qty") > F.col("qty"), "System expanded").otherwise("Installed as proposed"))
fact_proposal_line = (fql.withColumn("outcome", outcome)
  .withColumn("ordered_value_nok", F.coalesce("ordered_value_nok", F.lit(0)).cast("decimal(14,2)"))
  .withColumn("changed_value_nok", F.when(F.col("outcome").isin("Proposal not accepted","Component dropped","System downsized","Contract cancelled"),
              F.greatest(F.lit(0), F.col("line_total_nok") - F.col("ordered_value_nok"))).otherwise(F.lit(0)).cast("decimal(14,2)")))
write_table(fact_proposal_line, "factproposalline")'''),
("md", "## Proposals and follow-up"),
("code", '''acts = read_table("silveractivity")
first_fu = acts.filter("status = 'Completed'").groupBy("proposal_id").agg(F.min("activity_date").alias("first_followup_date"))
fact_proposal = (q.join(first_fu, "proposal_id", "left")
  .withColumn("days_to_first_followup", F.datediff("first_followup_date", "sent_date"))
  .withColumn("age_days", F.when(F.col("status") == "Open", F.datediff(F.lit(AS_OF), "sent_date")))
  .withColumn("is_signed", (F.col("status") == "Won").cast("int")))
write_table(fact_proposal, "factproposal")
write_table(sol.join(so.select("order_id","customer_id","order_date","order_status"), "order_id"), "factorderline")
write_table(read_table("silverinvoice").join(so.select("order_id","customer_id"), "order_id"), "factinvoice")'''),
("md", "## Sales history across both ERP systems\nThe old ERP is frozen. Its lines are mapped to current numbers through crosswalk tables; lines that cannot be mapped keep their old numbers and are flagged, never dropped."),
("code", '''leg = (read_table("silverlegacyorderline").join(read_table("silverlegacyproduct"), "old_item_no", "left")
  .join(read_table("silverproductxref"), "old_item_no", "left").join(read_table("silvercustomerxref"), "old_customer_no", "left")
  .select(F.lit("Legacy ERP").alias("source"), F.col("legacy_order_no").alias("order_no"), "order_date", "customer_id", "old_customer_no",
          "product_code", "old_item_no", "description", "category", "qty", "amount_nok"))
cur = (sol.join(so.filter("order_status <> 'Cancelled'").select("order_id","customer_id","order_date"), "order_id")
  .join(read_shared("core", "dimproduct").select("product_code", F.col("product_name").alias("description"), "category"), "product_code")
  .select(F.lit("Current ERP").alias("source"), F.col("order_id").alias("order_no"), "order_date", "customer_id",
          F.lit(None).cast("string").alias("old_customer_no"), "product_code", F.lit(None).cast("string").alias("old_item_no"),
          "description", "category", "qty", F.col("line_total_nok").alias("amount_nok")))
fact_sales_history = leg.unionByName(cur).withColumn("customer_mapped", F.col("customer_id").isNotNull())
write_table(fact_sales_history, "factsaleshistory")'''),
]
GOLD["supply"] = [
("code", '''write_table(read_table("silversupplier"), "dimsupplier")
write_table(read_table("silverbatterydelivery"), "factbatterydelivery")
write_table(read_table("silversupplierprequal"), "factsupplierprequal")'''),
]
GOLD["delivery"] = [
("md", "Crews and jobs. Certification validity is checked against the job date here, where the crew data is owned."),
("code", '''crew, cert, job = read_table("silvercrew"), read_table("silvercertification"), read_table("silverjob")
write_table(crew, "dimcrew")
certified = (job.alias("j").join(cert.alias("c"), (F.col("j.crew_id") == F.col("c.crew_id")) &
             F.col("j.job_date").between(F.col("c.valid_from"), F.col("c.valid_to")), "left")
             .groupBy("j.job_id").agg((F.count("c.crew_id") > 0).alias("crew_certified")))
prior = W.partitionBy("crew_id").orderBy("job_date", "job_id")
fact_job = (job.join(certified, "job_id")
  .withColumn("crew_prior_jobs", F.row_number().over(prior) - 1)
  .withColumn("days_late", F.datediff("job_date", "planned_date")))
write_table(fact_job, "factjob")'''),
]
GOLD["assets"] = [
("code", '''site = read_shared("core", "dimsite").select("site_id","municipality","country","station_id")
dim_installation = read_table("silverinstallation").join(site, "site_id").withColumn("has_battery", F.col("battery_kwh") > 0)
write_table(dim_installation, "diminstallation")
write_table(read_table("silverservicevisit"), "factservicevisit")'''),
("md", "## Production vs. expected\nExpected = kWp × irradiation × reference performance × orientation × age. Snow days are not counted as missing output."),
("code", '''orient = spark.createDataFrame([("S",1.0),("SE",0.95),("SW",0.95),("E/W",0.84)], "orientation string, orient_factor double")
inst = dim_installation.select("installation_id","station_id","kwp","orientation","grid_connected_date").join(orient, "orientation")
wx = read_shared("core", "factweatherdaily").select("station_id","date","irradiation_kwh_m2","snow_depth_cm")
prod = (read_table("silverproductiondaily").join(inst, "installation_id").join(wx, ["station_id","date"], "left")
  .withColumn("expected_kwh", F.round(F.col("kwp") * F.col("irradiation_kwh_m2") * 0.82 * F.col("orient_factor")
                                       * (1 - 0.005 * F.datediff("date","grid_connected_date") / 365.0), 2))
  .withColumn("snow_on_panels", F.col("snow_depth_cm") > 2))
w7 = W.partitionBy("installation_id").orderBy("date").rowsBetween(-6, 0)
fact_production_daily = (prod.withColumn("kwh_7d", F.sum("kwh").over(w7))
  .withColumn("expected_7d", F.sum(F.when(~F.col("snow_on_panels"), F.col("expected_kwh"))).over(w7))
  .withColumn("ratio_7d", F.when(F.col("expected_7d") > 5, F.round(F.col("kwh_7d") / F.col("expected_7d"), 3)))
  .withColumn("underperforming", (F.col("ratio_7d") < 0.7) & ~F.col("snow_on_panels"))
  .select("installation_id","date","kwh","expected_kwh","snow_on_panels","ratio_7d","underperforming"))
write_table(fact_production_daily, "factproductiondaily")'''),
("md", "Demo-only check against the generator's answer key."),
("code", '''truth = read_table("silverfaultlogtruth")
flagged = read_table("factproductiondaily").filter("underperforming").select("installation_id","date")
hits = (truth.alias("t").join(flagged.alias("f"), (F.col("t.installation_id") == F.col("f.installation_id")) &
        F.col("f.date").between(F.col("t.fault_start"), F.date_add(F.col("t.fault_end"), 6)), "left")
        .groupBy("t.installation_id","t.fault_start","t.fault_type").agg((F.count("f.date") > 0).alias("detected")))
display(hits.groupBy("fault_type").agg(F.avg(F.col("detected").cast("int")).alias("detection_rate"), F.count("*").alias("faults")))'''),
]
GOLD["hseq"] = [
("md", "## Compliance: is every installation audit-ready?"),
("code", '''inst = read_shared("assets", "diminstallation")
write_table(read_table("silvercompliancerequirement"), "dimcompliancerequirement")
ci = (read_table("silvercomplianceitem").withColumn("status",
        F.when(F.col("submitted_date").isNotNull() & (F.col("submitted_date") <= F.col("due_date")), "On time")
         .when(F.col("submitted_date").isNotNull(), "Late").when(F.col("due_date") < F.lit(AS_OF), "Overdue").otherwise("Not yet due")))
write_table(ci, "factcomplianceitem")
dev = (read_table("silverinspectiondeviation").withColumn("is_open", F.col("closed_date").isNull())
        .withColumn("days_open", F.datediff(F.coalesce("closed_date", F.lit(AS_OF).cast("date")), "found_date")))
write_table(dev, "factinspectiondeviation")
overdue = ci.filter("status = 'Overdue'").groupBy("installation_id").agg(F.count("*").alias("overdue_items"))
open_high = dev.filter("is_open AND severity = 'High'").groupBy("installation_id").agg(F.count("*").alias("open_high_deviations"))
audit = (inst.select("installation_id").join(overdue, "installation_id", "left").join(open_high, "installation_id", "left")
         .fillna(0, ["overdue_items","open_high_deviations"])
         .withColumn("audit_ready", (F.col("overdue_items") == 0) & (F.col("open_high_deviations") == 0)))
write_table(audit, "factauditreadiness")'''),
("md", """## Battery risk: act on conditions, not on counts
Counting days since the last incident tells nobody what to do on Tuesday. Instead every battery job is checked for the conditions that
make incidents likely, across the whole chain: supplier, transport, storage, crew, site and planning. The factors, weights and
stop rules live in `risk_rule`, owned by quality, so they can be changed without touching code.

- **Red**: a stop factor is present, or the score is 6 or more. Fix it before work starts.
- **Yellow**: score 3 to 5. Supervisor check and toolbox talk before start.
- **Green**: proceed."""),
("code", '''rules = read_table("silverriskrule")
job = read_shared("delivery", "factjob")
dl = read_shared("supply", "factbatterydelivery")
crew = read_shared("delivery", "dimcrew")
orders = read_shared("sales", "factorderline").select("order_id","customer_id").distinct()
site = read_shared("core", "dimcustomer").select("customer_id","site_id","municipality","country")
stations = read_shared("core", "dimsite").select("site_id","station_id")
fc = read_shared("core", "factweatherforecast").select(F.col("station_id").alias("fc_station"), F.col("date").alias("fc_date"), "temp_min_c")

PREQUAL = read_shared("supply", "factsupplierprequal")   # subcontractor safety prequalification windows, owned by purchasing

j = (job.join(dl.select("delivery_id","supplier_id","packaging_damage","shock_indicator_tripped","inspected_at_receipt","temp_excursion","storage_days"), "delivery_id")
        .join(crew.select("crew_id", F.col("supplier_id").alias("subcontractor_id"), "crew_type"), "crew_id")
        .join(orders, "order_id").join(site, "customer_id").join(stations, "site_id")
        .join(fc, (F.col("station_id") == F.col("fc_station")) & (F.col("job_date") == F.col("fc_date")), "left").drop("fc_station", "fc_date"))
pq = (j.select("job_id","subcontractor_id","job_date").join(PREQUAL, (F.col("subcontractor_id") == PREQUAL.supplier_id) &
        F.col("job_date").between(F.col("valid_from"), F.col("valid_to")), "left")
        .groupBy("job_id").agg((F.count("valid_from") > 0).alias("prequal_ok")))
j = j.join(pq, "job_id")
done = F.col("status") == "Done"
indoor = F.col("location") != "Outdoor cabinet"
flags = {   # factor_code -> condition. Planned jobs use what is known now: delivery, crew, site and the forecast.
  "DAMAGE_UNCHECKED": ((F.col("packaging_damage") == 1) | (F.col("shock_indicator_tripped") == 1)) & (F.col("inspected_at_receipt") == 0),
  "PKG_DAMAGE": F.col("packaging_damage") == 1, "SHOCK": F.col("shock_indicator_tripped") == 1,
  "NOT_INSPECTED": F.col("inspected_at_receipt") == 0, "TEMP_EXCURSION": F.col("temp_excursion") == 1,
  "LONG_STORAGE": F.col("storage_days") > 60,
  "PREQUAL_EXPIRED": F.col("subcontractor_id").isNotNull() & ~F.col("prequal_ok"),
  "UNCERTIFIED": ~F.col("crew_certified"), "NEW_CREW": F.col("crew_prior_jobs") < 3,
  "COLD_BATTERY": done & (F.col("battery_temp_c") < 5) & (F.col("acclimatised") == 0),
  "FROST_FORECAST": ~done & (F.col("temp_min_c") < 0),
  "NO_VENT_CHECK": done & indoor & (F.col("ventilation_check_done") == 0),
  "GARAGE": F.col("location") == "Garage",
  "NO_SJA": F.when(done, F.col("sja_done") == 0).otherwise(F.lit(False)),
  "LATE": F.when(done, F.col("days_late") > 14).otherwise(F.lit(False)),
}
present = None
for code, cond in flags.items():
    part = j.filter(F.coalesce(cond, F.lit(False))).select("job_id", F.lit(code).alias("factor_code"))
    present = part if present is None else present.unionByName(part)
fact_job_risk_factor = present.join(rules, "factor_code")
write_table(fact_job_risk_factor, "factjobriskfactor")

score = fact_job_risk_factor.groupBy("job_id").agg(F.sum("weight").alias("risk_score"), F.max("stops_work").alias("has_stop_factor"),
                                                   F.concat_ws(", ", F.sort_array(F.collect_list("factor_code"))).alias("factors"))
fact_job_risk = (j.select("job_id","job_date","status","order_id","customer_id","municipality","country","crew_id","crew_type","supplier_id","subcontractor_id","location")
  .join(score, "job_id", "left").fillna({"risk_score": 0, "has_stop_factor": 0, "factors": ""})
  .withColumn("risk_level", F.when((F.col("has_stop_factor") == 1) | (F.col("risk_score") >= 6), "Red")
                             .when(F.col("risk_score") >= 3, "Yellow").otherwise("Green")))
write_table(fact_job_risk, "factjobrisk")
write_table(read_table("silverhseevent"), "facthseevent")
write_table(read_table("silverhseaction"), "facthseaction")'''),
("md", "## Proof: do the factors predict events?\nEvents per 100 jobs by risk level, before and after the rule was introduced on 1 April 2026."),
("code", '''ev = read_table("facthseevent").filter("event_type <> 'Good catch'").groupBy("job_id").agg(F.count("*").alias("events"))
r = read_table("factjobrisk").filter("status = 'Done'").join(ev, "job_id", "left").fillna({"events": 0})
display(r.withColumn("period", F.when(F.col("job_date") >= "2026-04-01", "After rule").otherwise("Before rule"))
         .groupBy("period", "risk_level").agg(F.count("*").alias("jobs"), F.round(F.sum("events") / F.count("*") * 100, 1).alias("events_per_100_jobs"))
         .orderBy("period", "risk_level"))'''),
]

def gold(domain):
    return [("md", f"# {NAME[domain]} 3 · Gold\nOwned by: {OWNER[domain]}. Reads from other domains only through shortcuts."),
            ("code", common(domain))] + GOLD[domain]

def save(path, cells):
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(c) if k == "md" else nbf.v4.new_code_cell(c) for k, c in cells]
    nb.metadata = {"kernelspec": {"name": "synapse_pyspark", "display_name": "Synapse PySpark", "language": "Python"}, "language_info": {"name": "python"}}
    os.makedirs(os.path.dirname(path), exist_ok=True); nbf.write(nb, path)

for dom in ORDER:
    save(os.path.join(HERE, dom, f"{dom}-1-bronze.ipynb"), bronze(dom))
    save(os.path.join(HERE, dom, f"{dom}-2-silver.ipynb"), silver(dom))
    save(os.path.join(HERE, dom, f"{dom}-3-gold.ipynb"), gold(dom))
    print("wrote", dom)

# shortcut list
lines = ["# OneLake shortcuts", "", "Create these in each consuming lakehouse. Name = source domain + table, like `coredimsite`. Read-only; the source domain owns the data.", "",
         "| In lakehouse | Shortcut name | Points to |", "|---|---|---|"]
for dom in ORDER:
    for src, tbl in silver_needs(dom) + NEEDS_GOLD.get(dom, []):
        lines.append(f"| {NAME[dom]} | {src}{tbl} | {NAME[src]} / {tbl} |")
open(os.path.join(HERE, "SHORTCUTS.md"), "w").write("\n".join(lines) + "\n")
print("wrote SHORTCUTS.md")
