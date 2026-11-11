"""Aggregates the generated Solvi data into site/solvi/data.js for the interactive demo report.
Mirrors the gold-layer logic in notebooks/03_gold_model. Run after generator/generate.py."""
import json, os
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
import glob
def D(n, **kw):   # tables live in data/<domain>/<table>.csv
    return pd.read_csv(glob.glob(os.path.join(ROOT, "data", "*", f"{n}.csv"))[0], **kw)
END = pd.Timestamp("2026-10-31")

site, cust, prod = D("site"), D("customer"), D("product")
q = D("proposal", parse_dates=["created_date", "sent_date", "decided_date"])
ql, o, ol, act = D("proposal_line"), D("sales_order"), D("sales_order_line"), D("activity", parse_dates=["activity_date"])
inst = D("installation", parse_dates=["grid_connected_date"])
pdly = D("production_daily", parse_dates=["date"])
wx = D("weather_daily", parse_dates=["date"])

cust = cust.merge(site[["site_id", "municipality", "country", "station_id"]], on="site_id")
q = q.merge(cust[["customer_id", "segment", "country", "municipality"]], on="customer_id")
q["year"] = q.created_date.dt.year
q["ym"] = q.created_date.dt.strftime("%Y-%m")
KEY = ["year", "country", "segment"]

# ---------- proposal-line outcomes (same rules as fact_proposal_line)
olq = ol.dropna(subset=["proposal_line_no"]).drop(columns=["line_no"]).astype({"proposal_line_no": int})
olq = olq.rename(columns={"proposal_line_no": "line_no", "product_code": "ordered_product", "qty": "ordered_qty",
                          "line_total_nok": "ordered_value"})[["proposal_id", "line_no", "ordered_product", "ordered_qty", "ordered_value"]]
f = (ql.merge(q[["proposal_id", "status"] + KEY], on="proposal_id")
       .merge(o[["proposal_id", "order_status"]], on="proposal_id", how="left")
       .merge(olq, on=["proposal_id", "line_no"], how="left")
       .merge(prod[["product_code", "category"]], on="product_code"))
def outcome(r):
    if r.status == "Open": return "Open"
    if r.status != "Won": return "Proposal not accepted"
    if r.order_status == "Cancelled": return "Contract cancelled"
    if pd.isna(r.ordered_product): return "Component dropped"
    if r.ordered_product != r.product_code: return "Component swapped"
    if r.ordered_qty < r.qty: return "System downsized"
    if r.ordered_qty > r.qty: return "System expanded"
    return "Installed as proposed"
f["outcome"] = f.apply(outcome, axis=1)
f["ordered_value"] = f.ordered_value.fillna(0)
f["lost"] = 0.0
m = f.outcome.isin(["Proposal not accepted", "Component dropped", "System downsized", "Contract cancelled"])
f.loc[m, "lost"] = (f.loc[m, "line_total_nok"] - f.loc[m, "ordered_value"]).clip(lower=0)
f["won_q"] = f.status.eq("Won")

def r0(x): return int(round(float(x)))
qo = []
for k, g in f.groupby(KEY):
    qq = q[(q.year == k[0]) & (q.country == k[1]) & (q.segment == k[2])]
    lost = g.groupby("outcome").lost.sum()
    qo.append([int(k[0]), k[1], k[2], len(qq), int(qq.status.isin(["Won", "Lost", "Expired"]).sum()), int((qq.status == "Won").sum()),
               r0(g.line_total_nok.sum()), r0(g[g.won_q & g.order_status.ne("Cancelled")].line_total_nok.sum()),
               r0(g[g.won_q & g.order_status.ne("Cancelled")].ordered_value.sum()),
               r0(lost.get("Component dropped", 0)), r0(lost.get("System downsized", 0)), r0(lost.get("Contract cancelled", 0)),
               r0(lost.get("Proposal not accepted", 0))])

monthly = [[k[0], k[1], k[2], int((g.status == "Won").sum()), int(g.status.isin(["Lost", "Expired"]).sum()), int((g.status == "Open").sum())]
           for k, g in q.groupby(["ym", "country", "segment"])]

cat = f[f.outcome.isin(["Component dropped", "System downsized", "Contract cancelled"])]
cat_rows = [[int(k[0]), k[1], k[2], k[3], k[4], r0(g.lost.sum())] for k, g in cat.groupby(KEY + ["category", "outcome"]) if g.lost.sum() > 0]

reasons = [[int(k[0]), k[1], k[2], k[3], len(g)] for k, g in q[q.status == "Lost"].groupby(KEY + ["loss_reason"])]

# ---------- follow-up
done = act[act.status == "Completed"].groupby("proposal_id").activity_date.min().rename("first_fu")
plan = act[act.status == "Planned"].groupby("proposal_id").activity_date.min().rename("planned")
q = q.merge(done, on="proposal_id", how="left").merge(plan, on="proposal_id", how="left")
q["fu"] = q.first_fu.notna().map({True: "Completed", False: "None"})
q.loc[q.first_fu.isna() & q.planned.notna(), "fu"] = "Planned"
q["days_fu"] = (q.first_fu - q.sent_date).dt.days
q["bucket"] = pd.cut(q.days_fu, [-1, 3, 7, 14, 999], labels=["0–3 days", "4–7 days", "8–14 days", "15+ days"]).astype(str)
q.loc[q.first_fu.isna(), "bucket"] = "No follow-up"
dec = q[q.status.isin(["Won", "Lost", "Expired"])]
fu_rows = [[int(k[0]), k[1], k[2], k[3], len(g), int((g.status == "Won").sum())] for k, g in dec.groupby(KEY + ["bucket"])]

op = q[q.status == "Open"].copy()
op["age"] = (END - op.sent_date).dt.days
op = op[(op.fu != "Completed") & (op.age >= 3)].sort_values("proposal_total_nok", ascending=False)
open_list = [[r.proposal_id, r.segment, r.municipality, r.country, int(r.age), r0(r.proposal_total_nok), r.fu, int(r.year)]
             for r in op.itertuples()]

# ---------- production vs expected (same formula as fact_production_daily)
ORIENT = {"S": 1.0, "SE": 0.95, "SW": 0.95, "E/W": 0.84}
inst = inst.merge(site[["site_id", "municipality", "country", "station_id"]], on="site_id")
inst = inst.merge(cust[["customer_id", "segment"]], on="customer_id")
p = (pdly.merge(inst[["installation_id", "station_id", "kwp", "orientation", "grid_connected_date", "country", "municipality"]], on="installation_id")
         .merge(wx[["station_id", "date", "irradiation_kwh_m2", "snow_depth_cm"]], on=["station_id", "date"], how="left"))
age = (p.date - p.grid_connected_date).dt.days / 365
p["expected"] = p.kwp * p.irradiation_kwh_m2 * 0.82 * p.orientation.map(ORIENT) * (1 - 0.005 * age)
p["snow"] = p.snow_depth_cm > 2
p["ym"] = p.date.dt.strftime("%Y-%m")
p["exp_clear"] = p.expected.where(~p.snow, p.kwh)          # don't count snow days as missing output
prod_m = [[k[0], k[1], round(g.kwh.sum() / 1000, 1), round(g.exp_clear.sum() / 1000, 1), round(g.expected.sum() / 1000, 1)]
          for k, g in p.groupby(["ym", "country"])]

y25 = p[(p.date.dt.year == 2025) & (p.grid_connected_date < "2025-01-01")]
yl = y25.groupby(["installation_id", "municipality", "country", "kwp"]).kwh.sum().reset_index()
yl["y"] = yl.kwh / yl.kwp
yield_rows = [[k[0], k[1], int(round(g.y.median())), len(g)] for k, g in yl.groupby(["municipality", "country"])]

p = p.sort_values(["installation_id", "date"])
grp = p.groupby("installation_id")
p["k7"] = grp.kwh.transform(lambda s: s.rolling(7, min_periods=7).sum())
p["e7"] = grp.exp_clear.transform(lambda s: s.rolling(7, min_periods=7).sum())
p["ratio"] = (p.k7 / p.e7).where(p.e7 > 5)
p["flag"] = (p.ratio < 0.7) & ~p.snow
last30 = p[p.date > END - pd.Timedelta(days=60)]
under = (last30.groupby(["installation_id", "municipality", "country", "kwp"])
         .agg(days=("flag", "sum"), ratio=("ratio", "last")).reset_index())
under = under[under.days > 0].sort_values(["days", "ratio"], ascending=[False, True])
under_rows = [[r.installation_id, r.municipality, r.country, r.kwp, None if pd.isna(r.ratio) else round(r.ratio, 2), int(r.days)]
              for r in under.itertuples()]
p12 = p[p.date > END - pd.Timedelta(days=365)]
prod_kpi = {c: {"installs": int((inst.country == c).sum()), "kwp": round(inst[inst.country == c].kwp.sum(), 1),
                "mwh12": round(p12[p12.country == c].kwh.sum() / 1000, 1)} for c in sorted(inst.country.unique())}


# ---------- compliance (same rules as fact_compliance_item / fact_audit_readiness)
req = D("compliance_requirement"); ci = D("compliance_item", parse_dates=["due_date", "submitted_date"])
dv = D("inspection_deviation", parse_dates=["found_date", "closed_date"])
ikey = inst[["installation_id", "municipality", "country", "segment"]].assign(year=D("installation", parse_dates=["installed_date"]).installed_date.dt.year.values)
ci = ci.merge(req[["requirement_id", "requirement_name"]], on="requirement_id").merge(ikey, on="installation_id")
ci["status"] = "Not yet due"
ci.loc[ci.submitted_date.notna() & (ci.submitted_date <= ci.due_date), "status"] = "On time"
ci.loc[ci.submitted_date.notna() & (ci.submitted_date > ci.due_date), "status"] = "Late"
ci.loc[ci.submitted_date.isna() & (ci.due_date < END), "status"] = "Overdue"
ci["days_over"] = (END - ci.due_date).dt.days.where(ci.status == "Overdue")
ci["dq"] = ci.due_date.dt.year.astype(str) + "-Q" + ci.due_date.dt.quarter.astype(str)
comp_items = [[int(k[0]), k[1], k[2], k[3], k[4], k[5], len(g)] for k, g in ci[ci.due_date <= END].groupby(KEY + ["requirement_name", "dq", "status"])]
dv = dv.merge(ikey, on="installation_id")
dv["open"] = dv.closed_date.isna()
dv["days"] = ((dv.closed_date.fillna(END)) - dv.found_date).dt.days
dv["age"] = pd.cut(dv.days, [-1, 30, 90, 180, 99999], labels=["0–30 d", "31–90 d", "91–180 d", "180+ d"]).astype(str)
dev_rows = [[int(k[0]), k[1], k[2], k[3], bool(k[4]), k[5], len(g), int(g.days.sum())] for k, g in dv.groupby(KEY + ["severity", "open", "age"])]
ov = ci[ci.status == "Overdue"].groupby("installation_id").agg(n=("item_id", "count"), mx=("days_over", "max"),
                                                                  what=("requirement_name", lambda x: ", ".join(sorted(set(x)))))
oh = dv[dv.open & (dv.severity == "High")].groupby("installation_id").size().rename("high")
au = ikey.set_index("installation_id").join(ov).join(oh).fillna({"n": 0, "mx": 0, "high": 0, "what": ""})
au["ready"] = (au.n == 0) & (au.high == 0)
audit_tot = [[int(k[0]), k[1], k[2], len(g), int(g.ready.sum())] for k, g in au.reset_index().groupby(KEY)]
nr = au[~au.ready].reset_index().sort_values(["high", "mx"], ascending=False)
audit_list = [[r.installation_id, r.municipality, r.country, r.segment, int(r.year), int(r.n), int(r.mx), int(r.high), r.what] for r in nr.itertuples()]

# ---------- battery risk (same rules as hseq fact_job_risk)
job = D("job", parse_dates=["planned_date", "job_date"]); dl = D("battery_delivery"); crew_t = D("crew"); cert = D("certification", parse_dates=["valid_from","valid_to"])
rules = D("risk_rule"); sup = D("supplier"); pq = D("supplier_prequal", parse_dates=["valid_from","valid_to"]); ev = D("hse_event", parse_dates=["event_date"])
fcst = D("weather_forecast", parse_dates=["date"]); act = D("hse_action")
custsite = cust[["customer_id","municipality","country","station_id"]]
oc = o[["order_id","customer_id"]]
J = (job.merge(dl, on="delivery_id", suffixes=("", "_d")).merge(crew_t.rename(columns={"supplier_id":"subcontractor_id"}), on="crew_id")
        .merge(oc, on="order_id").merge(custsite, on="customer_id")
        .merge(fcst[["station_id","date","temp_min_c"]].rename(columns={"date":"job_date"}), on=["station_id","job_date"], how="left"))
J = J.sort_values(["job_date","job_id"]); J["crew_prior"] = J.groupby("crew_id").cumcount()
def certified(r): return ((cert.crew_id == r.crew_id) & (cert.valid_from <= r.job_date) & (cert.valid_to >= r.job_date)).any()
def prequal_ok(r):
    if pd.isna(r.subcontractor_id): return True
    return ((pq.supplier_id == r.subcontractor_id) & (pq.valid_from <= r.job_date) & (pq.valid_to >= r.job_date)).any()
J["certified"] = J.apply(certified, axis=1); J["prequal_ok"] = J.apply(prequal_ok, axis=1)
done = J.status == "Done"; indoor = J.location != "Outdoor cabinet"
F_ = {
  "DAMAGE_UNCHECKED": ((J.packaging_damage == 1) | (J.shock_indicator_tripped == 1)) & (J.inspected_at_receipt == 0),
  "PKG_DAMAGE": J.packaging_damage == 1, "SHOCK": J.shock_indicator_tripped == 1, "NOT_INSPECTED": J.inspected_at_receipt == 0,
  "TEMP_EXCURSION": J.temp_excursion == 1, "LONG_STORAGE": J.storage_days > 60, "PREQUAL_EXPIRED": ~J.prequal_ok,
  "UNCERTIFIED": ~J.certified, "NEW_CREW": J.crew_prior < 3,
  "COLD_BATTERY": done & (J.battery_temp_c < 5) & (J.acclimatised == 0), "FROST_FORECAST": ~done & (J.temp_min_c < 0),
  "NO_VENT_CHECK": done & indoor & (J.ventilation_check_done == 0), "GARAGE": J.location == "Garage",
  "NO_SJA": done & (J.sja_done == 0), "LATE": done & ((J.job_date - J.planned_date).dt.days > 14),
}
W_ = rules.set_index("factor_code").weight.to_dict(); STOP = set(rules[rules.stops_work == 1].factor_code)
J["factors"] = [[k for k, m in F_.items() if bool(m.iloc[i]) is True] for i in range(len(J))]
J["score"] = J.factors.apply(lambda f: sum(W_[x] for x in f))
J["level"] = [("Red" if (set(f) & STOP or sc >= 6) else "Yellow" if sc >= 3 else "Green") for f, sc in zip(J.factors, J.score)]
evc = ev.groupby(["job_id","event_type"]).size().unstack(fill_value=0)
J = J.merge(evc, left_on="job_id", right_index=True, how="left").fillna({"Near miss":0, "Incident":0, "Good catch":0})
acted = set(act[act.completed == 1].job_id)
sname = sup.set_index("supplier_id").supplier_name.to_dict()
Dn = J[J.status == "Done"]
risk_jobs = [[r.job_date.strftime("%Y-%m-%d"), r.country, r.level, int(r.score), r.factors, r.crew_type, r.supplier_id, r.subcontractor_id if isinstance(r.subcontractor_id, str) else "",
              int(r["Near miss"]), int(r["Incident"]), int(r["Good catch"]), int(r.job_id in acted)] for _, r in Dn.iterrows()]
Pn = J[J.status == "Planned"].sort_values(["job_date"])
planned = [[r.job_id, r.job_date.strftime("%Y-%m-%d"), r.municipality, r.country, r.crew_name, r.crew_type, r.location, r.level, int(r.score), r.factors,
            None if pd.isna(r.temp_min_c) else float(r.temp_min_c)] for _, r in Pn.iterrows()]
inc = ev[ev.event_type == "Incident"].iloc[0]; ij = J[J.job_id == inc.job_id].iloc[0]
incident = {"date": inc.event_date.strftime("%Y-%m-%d"), "job_date": ij.job_date.strftime("%Y-%m-%d"), "text": inc.description,
            "factors": ij.factors, "level": ij.level, "crew": ij.crew_type, "supplier": sname[ij.supplier_id], "location": ij.location}
events_list = [[r.event_date.strftime("%Y-%m-%d"), r.event_type, r.severity] for r in ev.sort_values("event_date").itertuples()]
risk = {"rule_date": "2026-04-01", "rules": {r.factor_code: [r.factor, r.category, int(r.weight), int(r.stops_work)] for r in rules.itertuples()},
        "suppliers": sname, "jobs": risk_jobs, "planned": planned, "incident": incident, "events": events_list}
print("risk jobs", len(risk_jobs), "planned", len(planned), "red planned", sum(1 for p_ in planned if p_[7] == "Red"))

out = {"generated": "2026-10-31", "years": sorted(q.year.unique().tolist()), "countries": sorted(q.country.unique().tolist()),
       "segments": sorted(q.segment.unique().tolist()),
       "qo": qo, "monthly": monthly, "cat": cat_rows, "reasons": reasons, "fu": fu_rows, "open": open_list,
       "prod_m": prod_m, "yield": yield_rows, "under": under_rows, "prod_kpi": prod_kpi,
       "risk": risk, "comp_items": comp_items, "dev": dev_rows, "audit_tot": audit_tot, "audit_list": audit_list}
os.makedirs(os.path.join(ROOT, "site", "solvi"), exist_ok=True)
with open(os.path.join(ROOT, "site", "solvi", "data.js"), "w") as fh:
    fh.write("window.SOLVI = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n")
print("wrote site/solvi/data.js", os.path.getsize(os.path.join(ROOT, "site", "solvi", "data.js")) // 1024, "KB")
print("open list", len(open_list), "under", len(under_rows))

# ---------- customer history archive (same rules as fact_sales_history) -> site/solvi/archive.js
lc = D("legacy_customer"); lpd = D("legacy_product"); lol = D("legacy_order_line", parse_dates=["order_date"])
cx = D("customer_xref"); px = D("product_xref")
leg = lol.merge(lpd, on="old_item_no", how="left").merge(cx, on="old_customer_no", how="left")
leg = leg.rename(columns={"legacy_order_no": "order_no", "amount_nok": "amount"}).assign(source="L")
curo = o[o.order_status != "Cancelled"][["order_id", "customer_id", "order_date"]]
cur = (ol.merge(curo, on="order_id").merge(prod[["product_code", "product_name"]], on="product_code")
         .rename(columns={"order_id": "order_no", "product_name": "description", "line_total_nok": "amount"}))
cur["order_date"] = pd.to_datetime(cur.order_date); cur = cur.assign(source="C", old_customer_no=None)
allh = pd.concat([leg[["source", "order_no", "order_date", "customer_id", "old_customer_no", "description", "amount"]],
                  cur[["source", "order_no", "order_date", "customer_id", "old_customer_no", "description", "amount"]]])
allh["key"] = allh.customer_id.fillna(allh.old_customer_no)
oldno = cx.set_index("customer_id").old_customer_no.to_dict()
cinfo = cust.set_index("customer_id")
linfo = lc.set_index("old_customer_no")
orders = (allh.sort_values("amount", ascending=False)
          .groupby(["key", "source", "order_no", "order_date"]).agg(top=("description", "first"), lines=("description", "size"), amount=("amount", "sum"))
          .reset_index().sort_values(["key", "order_date"]))
arch = []
for key, g in orders.groupby("key"):
    if key in cinfo.index:
        ci_ = cinfo.loc[key]; name, muni, seg, old = ci_.customer_name, ci_.municipality, ci_.segment, oldno.get(key, "")
    else:
        li = linfo.loc[key]; name, muni, seg, old = li["name"].title().replace("(Demo)", "(demo)"), li.municipality, "", key
    arch.append([key, old, name, muni, seg, key in cinfo.index,
                 [[r.order_date.strftime("%Y-%m-%d"), r.source, str(r.order_no), str(r.top).title() if r.source == "L" else r.top, int(r.lines), int(round(r.amount))]
                  for r in g.itertuples()]])
archive = {"lines_legacy": int(len(lol)), "lines_current": int(len(cur)),
           "pct_cust_mapped": round(float(leg.customer_id.notna().mean() * 100), 1),
           "pct_item_mapped": round(float(lol.old_item_no.isin(px.old_item_no).mean() * 100), 1),
           "customers": arch}
with open(os.path.join(ROOT, "site", "solvi", "archive.js"), "w") as fh:
    fh.write("window.SOLVI_ARCHIVE = " + json.dumps(archive, ensure_ascii=False, separators=(",", ":")) + ";\n")
print("wrote site/solvi/archive.js", os.path.getsize(os.path.join(ROOT, "site", "solvi", "archive.js")) // 1024, "KB,", len(arch), "customers")
