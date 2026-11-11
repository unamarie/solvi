"""Writes the Solvi semantic model as TMDL, in Direct Lake mode on the lh_consume lakehouse.

Run from the repo root:  python fabric/buildmodel.py
Output: fabric/Solvi.SemanticModel/ (deployed by solvifabric.py, which fills in the SQL endpoint)
Column lists come from fabric/goldschema.json, written from a local run of the gold notebooks.
"""
import json
import re
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "Solvi.SemanticModel")
SCHEMA = json.load(open(os.path.join(HERE, "goldschema.json"), encoding="utf-8"))

TABLES = [
    "dimdate", "dimcustomer", "dimsite", "dimproduct", "diminstallation", "dimcrew", "dimsupplier", "dimseller",
    "dimcompliancerequirement",
    "factjobrisk", "factjobriskfactor", "facthseevent", "facthseaction",
    "factproductiondaily", "factservicevisit",
    "factcomplianceitem", "factinspectiondeviation", "factauditreadiness",
    "factproposal", "factproposalline",
]

# many side -> one side. Kept as a clean star: no two paths between the same tables.
RELATIONSHIPS = [
    ("dimcustomer.site_id", "dimsite.site_id"),
    ("diminstallation.site_id", "dimsite.site_id"),
    ("factjobrisk.job_date", "dimdate.date"),
    ("factjobrisk.customer_id", "dimcustomer.customer_id"),
    ("factjobrisk.crew_id", "dimcrew.crew_id"),
    ("factjobrisk.supplier_id", "dimsupplier.supplier_id"),
    ("factjobriskfactor.job_id", "factjobrisk.job_id"),
    ("facthseevent.job_id", "factjobrisk.job_id"),
    ("facthseaction.job_id", "factjobrisk.job_id"),
    ("factproductiondaily.date", "dimdate.date"),
    ("factproductiondaily.installation_id", "diminstallation.installation_id"),
    ("factservicevisit.visit_date", "dimdate.date"),
    ("factservicevisit.installation_id", "diminstallation.installation_id"),
    ("factcomplianceitem.due_date", "dimdate.date"),
    ("factcomplianceitem.installation_id", "diminstallation.installation_id"),
    ("factcomplianceitem.requirement_id", "dimcompliancerequirement.requirement_id"),
    ("factinspectiondeviation.found_date", "dimdate.date"),
    ("factinspectiondeviation.installation_id", "diminstallation.installation_id"),
    ("factauditreadiness.installation_id", "diminstallation.installation_id"),
    ("factproposal.created_date", "dimdate.date"),
    ("factproposal.customer_id", "dimcustomer.customer_id"),
    ("factproposal.seller_id", "dimseller.seller_id"),
    ("factproposalline.proposal_id", "factproposal.proposal_id"),
    ("factproposalline.product_code", "dimproduct.product_code"),
]

# what report users see: no underscores, plain words
DISPLAY = {
    "dimdate": "Date", "dimcustomer": "Customer", "dimsite": "Site", "dimproduct": "Product", "diminstallation": "Installation",
    "dimcrew": "Crew", "dimsupplier": "Supplier", "dimseller": "Seller", "dimcompliancerequirement": "Compliance requirement",
    "factjobrisk": "Battery job", "factjobriskfactor": "Risk factor", "facthseevent": "HSE event", "facthseaction": "HSE action",
    "factproductiondaily": "Production", "factservicevisit": "Service visit", "factcomplianceitem": "Compliance item",
    "factinspectiondeviation": "Deviation", "factauditreadiness": "Audit readiness", "factproposal": "Proposal",
    "factproposalline": "Proposal line",
}
WORDS = {"id": "ID", "kwh": "kWh", "kwp": "kWp", "nok": "NOK", "hse": "HSE", "sja": "SJA", "iso": "ISO", "abc": "ABC"}


def col_name(c):
    """job_date -> Job date, customer_id -> Customer ID, expected_kwh -> Expected kWh"""
    words = [WORDS.get(w, w) for w in c.split("_")]
    words[0] = words[0] if words[0] in WORDS.values() else words[0].capitalize()
    return " ".join(words)


def q(n):
    return f"'{n}'"


def dax(expr):
    """Measures are written with lakehouse names; this turns them into the names report users see."""
    expr = re.sub(r"\b(\w+)\[([^\]]+)\]", lambda m: f"{q(DISPLAY[m[1]])}[{col_name(m[2])}]" if m[1] in DISPLAY else m[0], expr)
    return re.sub(r"(?<!')\b(dim\w+|fact\w+)\b(?!')", lambda m: q(DISPLAY[m[1]]) if m[1] in DISPLAY else m[0], expr)


PCT, NUM, DEC, KWH, NOK, DATE = "0.0%", "#,0", "#,0.0", "#,0 \"kWh\"", "#,0 \"kr\"", "yyyy-mm-dd"
# table: [(name, DAX, format, folder)]
MEASURES = {
    "factjobrisk": [
        ("As of date", 'DATE ( 2026, 10, 31 )', DATE, "Settings"),
        ("Battery jobs", 'CALCULATE ( COUNTROWS ( factjobrisk ), factjobrisk[status] = "Done" )', NUM, "Risk"),
        ("Red jobs", 'CALCULATE ( [Battery jobs], factjobrisk[risk_level] = "Red" )', NUM, "Risk"),
        ("Yellow jobs", 'CALCULATE ( [Battery jobs], factjobrisk[risk_level] = "Yellow" )', NUM, "Risk"),
        ("Red job share", 'DIVIDE ( [Red jobs], [Battery jobs] )', PCT, "Risk"),
        ("Planned jobs", 'CALCULATE ( COUNTROWS ( factjobrisk ), factjobrisk[status] = "Planned" )', NUM, "Risk"),
        ("Planned red jobs", 'CALCULATE ( [Planned jobs], factjobrisk[risk_level] = "Red" )', NUM, "Risk"),
        ("Average risk score", 'AVERAGE ( factjobrisk[risk_score] )', DEC, "Risk"),
    ],
    "factjobriskfactor": [
        ("Risk factors found", 'COUNTROWS ( factjobriskfactor )', NUM, "Risk"),
        ("Stop factors found", 'CALCULATE ( COUNTROWS ( factjobriskfactor ), factjobriskfactor[stops_work] = 1 )', NUM, "Risk"),
    ],
    "facthseevent": [
        ("Incidents", 'CALCULATE ( COUNTROWS ( facthseevent ), facthseevent[event_type] = "Incident" )', NUM, "HSE"),
        ("Near misses", 'CALCULATE ( COUNTROWS ( facthseevent ), facthseevent[event_type] = "Near miss" )', NUM, "HSE"),
        ("Good catches", 'CALCULATE ( COUNTROWS ( facthseevent ), facthseevent[event_type] = "Good catch" )', NUM, "HSE"),
        ("Events per 100 jobs", 'DIVIDE ( [Incidents] + [Near misses], [Battery jobs] ) * 100', DEC, "HSE"),
        ("Days since last incident",
         'VAR lastIncident = CALCULATE ( MAX ( facthseevent[event_date] ), facthseevent[event_type] = "Incident", REMOVEFILTERS () ) '
         'RETURN IF ( NOT ISBLANK ( lastIncident ), DATEDIFF ( lastIncident, [As of date], DAY ) )', NUM, "HSE"),
    ],
    "facthseaction": [
        ("Required actions", 'COUNTROWS ( facthseaction )', NUM, "HSE"),
        ("Actions completed share", 'DIVIDE ( CALCULATE ( COUNTROWS ( facthseaction ), facthseaction[completed] = 1 ), [Required actions] )', PCT, "HSE"),
    ],
    "factproductiondaily": [
        ("Production kWh", 'SUM ( factproductiondaily[kwh] )', KWH, "Production"),
        ("Expected kWh", 'SUM ( factproductiondaily[expected_kwh] )', KWH, "Production"),
        ("Performance ratio", 'DIVIDE ( [Production kWh], [Expected kWh] )', PCT, "Production"),
        ("Underperforming installations",
         'CALCULATE ( DISTINCTCOUNT ( factproductiondaily[installation_id] ), factproductiondaily[underperforming] = TRUE () )', NUM, "Production"),
    ],
    "factservicevisit": [
        ("Service visits", 'COUNTROWS ( factservicevisit )', NUM, "Service"),
        ("Service cost", 'SUM ( factservicevisit[cost_nok] )', NOK, "Service"),
    ],
    "factcomplianceitem": [
        ("Compliance items", 'COUNTROWS ( factcomplianceitem )', NUM, "Compliance"),
        ("Overdue items", 'CALCULATE ( COUNTROWS ( factcomplianceitem ), factcomplianceitem[status] = "Overdue" )', NUM, "Compliance"),
        ("On-time share",
         'DIVIDE ( CALCULATE ( COUNTROWS ( factcomplianceitem ), factcomplianceitem[status] = "On time" ), '
         'CALCULATE ( COUNTROWS ( factcomplianceitem ), factcomplianceitem[status] IN { "On time", "Late" } ) )', PCT, "Compliance"),
    ],
    "factinspectiondeviation": [
        ("Open deviations", 'CALCULATE ( COUNTROWS ( factinspectiondeviation ), factinspectiondeviation[is_open] = TRUE () )', NUM, "Compliance"),
        ("Open high deviations",
         'CALCULATE ( [Open deviations], factinspectiondeviation[severity] = "High" )', NUM, "Compliance"),
        ("Average days open", 'AVERAGE ( factinspectiondeviation[days_open] )', DEC, "Compliance"),
    ],
    "factauditreadiness": [
        ("Audit-ready share",
         'DIVIDE ( CALCULATE ( COUNTROWS ( factauditreadiness ), factauditreadiness[audit_ready] = TRUE () ), COUNTROWS ( factauditreadiness ) )', PCT, "Compliance"),
    ],
    "factproposal": [
        ("Proposals", 'COUNTROWS ( factproposal )', NUM, "Sales"),
        ("Won proposals", 'CALCULATE ( COUNTROWS ( factproposal ), factproposal[status] = "Won" )', NUM, "Sales"),
        ("Win rate",
         'DIVIDE ( [Won proposals], CALCULATE ( COUNTROWS ( factproposal ), factproposal[status] IN { "Won", "Lost", "Expired" } ) )', PCT, "Sales"),
        ("Proposal value", 'SUM ( factproposal[proposal_total_nok] )', NOK, "Sales"),
        ("Median days to first follow-up", 'MEDIAN ( factproposal[days_to_first_followup] )', DEC, "Sales"),
    ],
    "factproposalline": [
        ("Proposed line value", 'SUM ( factproposalline[line_total_nok] )', NOK, "Sales"),
        ("Ordered value", 'SUM ( factproposalline[ordered_value_nok] )', NOK, "Sales"),
        ("Change from proposal", 'SUM ( factproposalline[changed_value_nok] )', NOK, "Sales"),
    ],
}

TYPE = {"string": "string", "date": "dateTime", "int": "int64", "bigint": "int64", "double": "double", "boolean": "boolean"}


def tmdl_type(spark_type):
    return "decimal" if spark_type.startswith("decimal") else TYPE[spark_type]


def tag(*parts):
    """Stable lineage tags, so a rebuild does not look like a new model to Fabric."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "solvi/" + "/".join(parts)))


def name(n):
    return f"'{n}'" if not n.isalnum() else n


def table(t):
    lines = [f"table {name(DISPLAY[t])}", f"\tlineageTag: {tag(t)}"]
    if t == "dimdate":
        lines.append("\tdataCategory: Time")
    lines.append("")
    for m, expr, fmt, folder in MEASURES.get(t, []):
        lines += [f"\tmeasure {name(m)} = {dax(expr)}", f'\t\tformatString: {fmt}', f"\t\tdisplayFolder: {folder}",
                  f"\t\tlineageTag: {tag(t, 'm', m)}", ""]
    for col, st in SCHEMA[t]["cols"]:
        dt = tmdl_type(st)
        lines += [f"\tcolumn {name(col_name(col))}", f"\t\tdataType: {dt}"]
        if dt == "dateTime":
            lines.append("\t\tformatString: yyyy-mm-dd")
        if t == "dimdate" and col == "date":
            lines.append("\t\tisKey")
        lines += [f"\t\tlineageTag: {tag(t, col)}", "\t\tsummarizeBy: none", f"\t\tsourceColumn: {col}", ""]
    lines += [f"\tpartition {name(DISPLAY[t])} = entity", "\t\tmode: directLake", "\t\tsource", f"\t\t\tentityName: {t}",
              "\t\t\tschemaName: dbo", "\t\t\texpressionSource: DatabaseQuery", ""]
    return "\n".join(lines)


def ref(table_col):
    t, c = table_col.split(".")
    return f"{name(DISPLAY[t])}.{name(col_name(c))}"


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
      + "".join(f"ref table {name(DISPLAY[t])}\n" for t in TABLES))
    w("definition/expressions.tmdl",
      "expression DatabaseQuery =\n\t\tlet\n\t\t    database = Sql.Database(\"{{SQL_SERVER}}\", \"{{SQL_ENDPOINT_ID}}\")\n"
      f"\t\tin\n\t\t    database\n\tlineageTag: {tag('DatabaseQuery')}\n")
    w("definition/relationships.tmdl", "\n".join(
        f"relationship {tag('rel', a, b)}\n\tfromColumn: {ref(a)}\n\ttoColumn: {ref(b)}\n" for a, b in RELATIONSHIPS))
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
