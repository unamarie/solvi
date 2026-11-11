"""Writes the Solvi semantic model as TMDL, in Direct Lake mode on the lh_consume lakehouse.

Run from the repo root:  python fabric/build_model.py
Output: fabric/Solvi.SemanticModel/  (deployed by solvi_fabric.py, which fills in the SQL endpoint)
Column lists come from fabric/gold_schema.json, written from a local run of the gold notebooks.
"""
import json
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "Solvi.SemanticModel")
SCHEMA = json.load(open(os.path.join(HERE, "gold_schema.json"), encoding="utf-8"))

TABLES = [
    "dim_date", "dim_customer", "dim_site", "dim_product", "dim_installation", "dim_crew", "dim_supplier", "dim_seller",
    "dim_compliance_requirement",
    "fact_job_risk", "fact_job_risk_factor", "fact_hse_event", "fact_hse_action",
    "fact_production_daily", "fact_service_visit",
    "fact_compliance_item", "fact_inspection_deviation", "fact_audit_readiness",
    "fact_proposal", "fact_proposal_line",
]

# many side -> one side. Kept as a clean star: no two paths between the same tables.
RELATIONSHIPS = [
    ("dim_customer.site_id", "dim_site.site_id"),
    ("dim_installation.site_id", "dim_site.site_id"),
    ("fact_job_risk.job_date", "dim_date.date"),
    ("fact_job_risk.customer_id", "dim_customer.customer_id"),
    ("fact_job_risk.crew_id", "dim_crew.crew_id"),
    ("fact_job_risk.supplier_id", "dim_supplier.supplier_id"),
    ("fact_job_risk_factor.job_id", "fact_job_risk.job_id"),
    ("fact_hse_event.job_id", "fact_job_risk.job_id"),
    ("fact_hse_action.job_id", "fact_job_risk.job_id"),
    ("fact_production_daily.date", "dim_date.date"),
    ("fact_production_daily.installation_id", "dim_installation.installation_id"),
    ("fact_service_visit.visit_date", "dim_date.date"),
    ("fact_service_visit.installation_id", "dim_installation.installation_id"),
    ("fact_compliance_item.due_date", "dim_date.date"),
    ("fact_compliance_item.installation_id", "dim_installation.installation_id"),
    ("fact_compliance_item.requirement_id", "dim_compliance_requirement.requirement_id"),
    ("fact_inspection_deviation.found_date", "dim_date.date"),
    ("fact_inspection_deviation.installation_id", "dim_installation.installation_id"),
    ("fact_audit_readiness.installation_id", "dim_installation.installation_id"),
    ("fact_proposal.created_date", "dim_date.date"),
    ("fact_proposal.customer_id", "dim_customer.customer_id"),
    ("fact_proposal.seller_id", "dim_seller.seller_id"),
    ("fact_proposal_line.proposal_id", "fact_proposal.proposal_id"),
    ("fact_proposal_line.product_code", "dim_product.product_code"),
]

PCT, NUM, DEC, KWH, NOK, DATE = "0.0%", "#,0", "#,0.0", "#,0 \"kWh\"", "#,0 \"kr\"", "yyyy-mm-dd"
# table: [(name, DAX, format, folder)]
MEASURES = {
    "fact_job_risk": [
        ("As of date", 'DATE ( 2026, 10, 31 )', DATE, "Settings"),
        ("Battery jobs", 'CALCULATE ( COUNTROWS ( fact_job_risk ), fact_job_risk[status] = "Done" )', NUM, "Risk"),
        ("Red jobs", 'CALCULATE ( [Battery jobs], fact_job_risk[risk_level] = "Red" )', NUM, "Risk"),
        ("Yellow jobs", 'CALCULATE ( [Battery jobs], fact_job_risk[risk_level] = "Yellow" )', NUM, "Risk"),
        ("Red job share", 'DIVIDE ( [Red jobs], [Battery jobs] )', PCT, "Risk"),
        ("Planned jobs", 'CALCULATE ( COUNTROWS ( fact_job_risk ), fact_job_risk[status] = "Planned" )', NUM, "Risk"),
        ("Planned red jobs", 'CALCULATE ( [Planned jobs], fact_job_risk[risk_level] = "Red" )', NUM, "Risk"),
        ("Average risk score", 'AVERAGE ( fact_job_risk[risk_score] )', DEC, "Risk"),
    ],
    "fact_job_risk_factor": [
        ("Risk factors found", 'COUNTROWS ( fact_job_risk_factor )', NUM, "Risk"),
        ("Stop factors found", 'CALCULATE ( COUNTROWS ( fact_job_risk_factor ), fact_job_risk_factor[stops_work] = 1 )', NUM, "Risk"),
    ],
    "fact_hse_event": [
        ("Incidents", 'CALCULATE ( COUNTROWS ( fact_hse_event ), fact_hse_event[event_type] = "Incident" )', NUM, "HSE"),
        ("Near misses", 'CALCULATE ( COUNTROWS ( fact_hse_event ), fact_hse_event[event_type] = "Near miss" )', NUM, "HSE"),
        ("Good catches", 'CALCULATE ( COUNTROWS ( fact_hse_event ), fact_hse_event[event_type] = "Good catch" )', NUM, "HSE"),
        ("Events per 100 jobs", 'DIVIDE ( [Incidents] + [Near misses], [Battery jobs] ) * 100', DEC, "HSE"),
        ("Days since last incident",
         'VAR last_incident = CALCULATE ( MAX ( fact_hse_event[event_date] ), fact_hse_event[event_type] = "Incident", REMOVEFILTERS () ) '
         'RETURN IF ( NOT ISBLANK ( last_incident ), DATEDIFF ( last_incident, [As of date], DAY ) )', NUM, "HSE"),
    ],
    "fact_hse_action": [
        ("Required actions", 'COUNTROWS ( fact_hse_action )', NUM, "HSE"),
        ("Actions completed share", 'DIVIDE ( CALCULATE ( COUNTROWS ( fact_hse_action ), fact_hse_action[completed] = 1 ), [Required actions] )', PCT, "HSE"),
    ],
    "fact_production_daily": [
        ("Production kWh", 'SUM ( fact_production_daily[kwh] )', KWH, "Production"),
        ("Expected kWh", 'SUM ( fact_production_daily[expected_kwh] )', KWH, "Production"),
        ("Performance ratio", 'DIVIDE ( [Production kWh], [Expected kWh] )', PCT, "Production"),
        ("Underperforming installations",
         'CALCULATE ( DISTINCTCOUNT ( fact_production_daily[installation_id] ), fact_production_daily[underperforming] = TRUE () )', NUM, "Production"),
    ],
    "fact_service_visit": [
        ("Service visits", 'COUNTROWS ( fact_service_visit )', NUM, "Service"),
        ("Service cost", 'SUM ( fact_service_visit[cost_nok] )', NOK, "Service"),
    ],
    "fact_compliance_item": [
        ("Compliance items", 'COUNTROWS ( fact_compliance_item )', NUM, "Compliance"),
        ("Overdue items", 'CALCULATE ( COUNTROWS ( fact_compliance_item ), fact_compliance_item[status] = "Overdue" )', NUM, "Compliance"),
        ("On-time share",
         'DIVIDE ( CALCULATE ( COUNTROWS ( fact_compliance_item ), fact_compliance_item[status] = "On time" ), '
         'CALCULATE ( COUNTROWS ( fact_compliance_item ), fact_compliance_item[status] IN { "On time", "Late" } ) )', PCT, "Compliance"),
    ],
    "fact_inspection_deviation": [
        ("Open deviations", 'CALCULATE ( COUNTROWS ( fact_inspection_deviation ), fact_inspection_deviation[is_open] = TRUE () )', NUM, "Compliance"),
        ("Open high deviations",
         'CALCULATE ( [Open deviations], fact_inspection_deviation[severity] = "High" )', NUM, "Compliance"),
        ("Average days open", 'AVERAGE ( fact_inspection_deviation[days_open] )', DEC, "Compliance"),
    ],
    "fact_audit_readiness": [
        ("Audit-ready share",
         'DIVIDE ( CALCULATE ( COUNTROWS ( fact_audit_readiness ), fact_audit_readiness[audit_ready] = TRUE () ), COUNTROWS ( fact_audit_readiness ) )', PCT, "Compliance"),
    ],
    "fact_proposal": [
        ("Proposals", 'COUNTROWS ( fact_proposal )', NUM, "Sales"),
        ("Won proposals", 'CALCULATE ( COUNTROWS ( fact_proposal ), fact_proposal[status] = "Won" )', NUM, "Sales"),
        ("Win rate",
         'DIVIDE ( [Won proposals], CALCULATE ( COUNTROWS ( fact_proposal ), fact_proposal[status] IN { "Won", "Lost", "Expired" } ) )', PCT, "Sales"),
        ("Proposal value", 'SUM ( fact_proposal[proposal_total_nok] )', NOK, "Sales"),
        ("Median days to first follow-up", 'MEDIAN ( fact_proposal[days_to_first_followup] )', DEC, "Sales"),
    ],
    "fact_proposal_line": [
        ("Proposed line value", 'SUM ( fact_proposal_line[line_total_nok] )', NOK, "Sales"),
        ("Ordered value", 'SUM ( fact_proposal_line[ordered_value_nok] )', NOK, "Sales"),
        ("Change from proposal", 'SUM ( fact_proposal_line[changed_value_nok] )', NOK, "Sales"),
    ],
}

TYPE = {"string": "string", "date": "dateTime", "int": "int64", "bigint": "int64", "double": "double", "boolean": "boolean"}


def tmdl_type(spark_type):
    return "decimal" if spark_type.startswith("decimal") else TYPE[spark_type]


def tag(*parts):
    """Stable lineage tags, so a rebuild does not look like a new model to Fabric."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "solvi/" + "/".join(parts)))


def name(n):
    return f"'{n}'" if not n.replace("_", "").isalnum() else n


def table(t):
    lines = [f"table {t}", f"\tlineageTag: {tag(t)}"]
    if t == "dim_date":
        lines.append("\tdataCategory: Time")
    lines.append("")
    for m, dax, fmt, folder in MEASURES.get(t, []):
        lines += [f"\tmeasure {name(m)} = {dax}", f'\t\tformatString: {fmt}', f"\t\tdisplayFolder: {folder}",
                  f"\t\tlineageTag: {tag(t, 'm', m)}", ""]
    for col, st in SCHEMA[t]["cols"]:
        dt = tmdl_type(st)
        lines += [f"\tcolumn {name(col)}", f"\t\tdataType: {dt}"]
        if dt == "dateTime":
            lines.append("\t\tformatString: yyyy-mm-dd")
        if t == "dim_date" and col == "date":
            lines.append("\t\tisKey")
        lines += [f"\t\tlineageTag: {tag(t, col)}", "\t\tsummarizeBy: none", f"\t\tsourceColumn: {col}", ""]
    lines += [f"\tpartition {t} = entity", "\t\tmode: directLake", "\t\tsource", f"\t\t\tentityName: {t}",
              "\t\t\tschemaName: dbo", "\t\t\texpressionSource: DatabaseQuery", ""]
    return "\n".join(lines)


def build():
    d = os.path.join(OUT, "definition")
    os.makedirs(os.path.join(d, "tables"), exist_ok=True)
    for f in os.listdir(os.path.join(d, "tables")):
        os.remove(os.path.join(d, "tables", f))
    w = lambda p, s: open(os.path.join(OUT, p), "w", encoding="utf-8", newline="\n").write(s)
    w("definition.pbism", json.dumps({"version": "4.0", "settings": {}}, indent=2) + "\n")
    w("definition/database.tmdl", "database\n\tcompatibilityLevel: 1604\n")
    w("definition/model.tmdl", "model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
      "\tsourceQueryCulture: en-US\n\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
      + "".join(f"ref table {t}\n" for t in TABLES))
    w("definition/expressions.tmdl",
      "expression DatabaseQuery =\n\t\tlet\n\t\t    database = Sql.Database(\"{{SQL_SERVER}}\", \"{{SQL_ENDPOINT_ID}}\")\n"
      f"\t\tin\n\t\t    database\n\tlineageTag: {tag('DatabaseQuery')}\n")
    w("definition/relationships.tmdl", "\n".join(
        f"relationship {tag('rel', a, b)}\n\tfromColumn: {a}\n\ttoColumn: {b}\n" for a, b in RELATIONSHIPS))
    for t in TABLES:
        w(f"definition/tables/{t}.tmdl", table(t))
    print(f"wrote {OUT} ({len(TABLES)} tables, {sum(len(v) for v in MEASURES.values())} measures, {len(RELATIONSHIPS)} relationships)")


def check():
    """Catch typos before Fabric does: every relationship and measure reference must exist."""
    import re
    cols = {t: {c for c, _ in SCHEMA[t]["cols"]} for t in TABLES}
    for a, b in RELATIONSHIPS:
        for ref in (a, b):
            t, c = ref.split(".")
            assert t in cols and c in cols[t], f"unknown column {ref}"
    measures = {m for v in MEASURES.values() for m, *_ in v}
    for t, v in MEASURES.items():
        for m, dax, *_ in v:
            for tt, c in re.findall(r"(\w+)\[([^\]]+)\]", dax):
                assert tt in cols and c in cols[tt], f"{m}: unknown column {tt}[{c}]"
            for ref in re.findall(r"(?<![\w\]])\[([^\]]+)\]", dax):
                assert ref in measures, f"{m}: unknown measure [{ref}]"


if __name__ == "__main__":
    check()
    build()
