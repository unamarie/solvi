"""
Solvi — fictional Nordic solar & battery installer.
Generates a realistic, fully synthetic dataset for a Fabric / Power BI portfolio project.

Run:  python generate.py  -> writes CSVs to ./data
All companies, customers, people and numbers are invented. Locations are real places used only as geography.
"""
import math, random, csv, os, datetime as dt
from collections import defaultdict

random.seed(2026)
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUT, exist_ok=True)

START, END = dt.date(2023, 1, 1), dt.date(2026, 10, 31)
DAYS = (END - START).days + 1

def d(x): return x.isoformat() if x else ""
def rand_date(a, b): return a + dt.timedelta(days=random.randint(0, max(0, (b - a).days)))
# Every table belongs to one domain. Each domain has its own owner, workspace and lakehouse;
# "core" holds shared master data that the other domains read through shortcuts.
DOMAIN = {
    "core":     ["site","weather_station","weather_daily","weather_forecast","product","customer"],
    "sales":    ["seller","proposal","proposal_line","activity","sales_order","sales_order_line","invoice",
                 "legacy_customer","legacy_product","legacy_order_line","customer_xref","product_xref"],
    "supply":   ["supplier","supplier_prequal","battery_delivery"],
    "delivery": ["crew","certification","job"],
    "assets":   ["installation","production_daily","service_visit","fault_log_truth"],
    "hseq":     ["compliance_requirement","compliance_item","inspection_deviation","risk_rule","hse_event","hse_action"],
}
TABLE_DOMAIN = {t: dom for dom, ts in DOMAIN.items() for t in ts}

def write(name, header, rows):
    folder = os.path.join(OUT, TABLE_DOMAIN[name]); os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    print(f"{name:<22} {len(rows):>9,} rows")

# ---------------------------------------------------------------- geography
# (site_id, municipality, region, country, lat, lon, weather_station, customer weight)
SITES = [
    ("S01","Oslo","Østlandet","Norway",59.91,10.75,"WS-OSL",14),
    ("S02","Bærum","Østlandet","Norway",59.89,10.52,"WS-OSL",8),
    ("S03","Fredrikstad","Østlandet","Norway",59.22,10.93,"WS-FRE",6),
    ("S04","Hamar","Innlandet","Norway",60.79,11.07,"WS-HAM",5),
    ("S05","Kristiansand","Sørlandet","Norway",58.15,8.00,"WS-KRS",7),
    ("S06","Stavanger","Vestlandet","Norway",58.97,5.73,"WS-SVG",7),
    ("S07","Bergen","Vestlandet","Norway",60.39,5.32,"WS-BGO",8),
    ("S08","Ålesund","Vestlandet","Norway",62.47,6.15,"WS-AES",4),
    ("S09","Trondheim","Trøndelag","Norway",63.43,10.40,"WS-TRD",7),
    ("S10","Tromsø","Nord-Norge","Norway",69.65,18.96,"WS-TOS",3),
    ("S11","Gothenburg","Västra Götaland","Sweden",57.71,11.97,"WS-GOT",7),
    ("S12","Malmö","Skåne","Sweden",55.60,13.00,"WS-MMX",6),
    ("S13","Aarhus","Midtjylland","Denmark",56.16,10.20,"WS-AAR",5),
]
STATIONS = sorted({s[6]: s for s in SITES}.values(), key=lambda s: s[6])

# ---------------------------------------------------------------- weather (daily)
def clear_sky_kwh_m2(lat, doy):
    """Approximate daily clear-sky irradiation on a south-facing ~35° panel (kWh/m²)."""
    decl = 23.44 * math.sin(math.radians(360 / 365 * (doy - 81)))
    noon_elev = 90 - lat + decl
    if noon_elev <= 0: return 0.0
    # day length
    x = -math.tan(math.radians(lat)) * math.tan(math.radians(decl))
    x = max(-1, min(1, x))
    daylen = 2 * math.degrees(math.acos(x)) / 15
    tilt_gain = 1 + 0.9 * max(0, (35 - noon_elev)) / 35   # tilted panels help most when sun is low
    return min(7.8, max(0.0, 0.80 * daylen * math.sin(math.radians(noon_elev)) * tilt_gain))

weather, wx, wtemp = [], {}, {}
for st in STATIONS:
    sid, lat = st[6], st[4]
    west = st[5] < 7          # west coast: cloudier
    cloud = 0.6
    snow = 0.0
    for i in range(DAYS):
        day = START + dt.timedelta(days=i); doy = day.timetuple().tm_yday
        cloud = 0.7 * cloud + 0.3 * random.random()
        sun_frac = max(0.08, min(1.0, 1.05 - cloud * (1.05 if west else 0.85)))
        irr = round(clear_sky_kwh_m2(lat, doy) * sun_frac, 3)
        temp = round(6 - (lat - 58) * 0.45 + 10 * math.sin(math.radians(360 / 365 * (doy - 110))) + random.gauss(0, 3), 1)
        precip = round(max(0, random.gauss(2.6 if west else 1.7, 3.5)) if cloud > 0.45 else 0, 1)
        if temp < 0 and precip > 0: snow += precip * 0.8
        elif temp > 1: snow = max(0, snow - (temp * 1.5 + irr))
        snow = round(snow, 1)
        weather.append([sid, d(day), irr, temp, precip, snow])
        wx[(sid, day)] = (irr, snow); wtemp[(sid, day)] = temp
write("weather_daily", ["station_id","date","irradiation_kwh_m2","temp_c","precip_mm","snow_depth_cm"], weather)
write("weather_station", ["station_id","name","latitude","longitude"],
      [[s[6], s[1], s[4], s[5]] for s in STATIONS])
write("site", ["site_id","municipality","region","country","latitude","longitude","station_id"],
      [list(s[:7]) for s in SITES])

# ---------------------------------------------------------------- products
PRODUCTS = [
    # code, name, category, unit, list_price_nok, abc
    ("PV-410","Panel 410 W mono","Panel","pcs",2150,"A"),
    ("PV-440","Panel 440 W bifacial","Panel","pcs",2650,"A"),
    ("PV-380B","Panel 380 W all-black","Panel","pcs",2450,"B"),
    ("INV-5","Hybrid inverter 5 kW","Inverter","pcs",16900,"A"),
    ("INV-8","Hybrid inverter 8 kW","Inverter","pcs",22900,"A"),
    ("INV-15","String inverter 15 kW","Inverter","pcs",31900,"B"),
    ("INV-30","String inverter 30 kW","Inverter","pcs",48900,"C"),
    ("BAT-5","Battery 5 kWh module","Battery","pcs",34900,"A"),
    ("BAT-10","Battery 10 kWh","Battery","pcs",62900,"A"),
    ("EVC-11","EV charger 11 kW","EV charging","pcs",11900,"B"),
    ("MNT-TIL","Roof mount, tile","Mounting","panel",420,"C"),
    ("MNT-STL","Roof mount, steel","Mounting","panel",360,"C"),
    ("MNT-GND","Ground mount frame","Mounting","panel",780,"C"),
    ("OPT-1","Power optimiser","Electrical","pcs",690,"C"),
    ("CBL-KIT","DC cable & connector kit","Electrical","kit",3900,"D"),
    ("MTR-1","Smart energy meter","Electrical","pcs",3400,"C"),
    ("SNW-G","Snow guard","Mounting","m",590,"D"),
    ("LAB-INST","Installation labour","Service","hour",950,"-"),
    ("LAB-ELEC","Electrician labour","Service","hour",1150,"-"),
    ("SCF-1","Scaffolding","Service","day",4500,"-"),
    ("SVC-ANN","Annual service visit","Service","visit",2900,"-"),
    ("APP-MON","Monitoring subscription, year","Subscription","year",990,"-"),
]
PROD = {p[0]: p for p in PRODUCTS}
write("product", ["product_code","product_name","category","unit","list_price_nok","abc_class"], [list(p) for p in PRODUCTS])

# ---------------------------------------------------------------- sellers
SELLERS = [("SE01","A. Lund","Østlandet"),("SE02","K. Moe","Østlandet"),("SE03","T. Rød","Vestlandet"),
           ("SE04","S. Nilsen","Vestlandet"),("SE05","E. Haug","Trøndelag"),("SE06","J. Berg","Sørlandet"),
           ("SE07","M. Ek","Sweden"),("SE08","L. Holm","Denmark"),("SE09","I. Dahl","Inbound / web")]
write("seller", ["seller_id","seller_name","sales_area"], [list(s) for s in SELLERS])
def seller_for(site):
    reg, ctry = site[2], site[3]
    if ctry == "Sweden": pool = ["SE07"]
    elif ctry == "Denmark": pool = ["SE08"]
    elif reg in ("Østlandet","Innlandet"): pool = ["SE01","SE02"]
    elif reg == "Vestlandet": pool = ["SE03","SE04"]
    elif reg in ("Trøndelag","Nord-Norge"): pool = ["SE05"]
    else: pool = ["SE06"]
    return random.choice(pool + ["SE09"])

# ---------------------------------------------------------------- customers
SEGMENTS = [("Residential",0.74),("Housing cooperative",0.07),("Farm",0.09),("Commercial",0.10)]
SRC = [("Website",0.38),("Referral",0.22),("Partner",0.14),("Campaign",0.16),("Event",0.10)]
def pick(pairs): return random.choices([p[0] for p in pairs], [p[1] for p in pairs])[0]
B1 = ["Lyng","Fjære","Bjørke","Solbakk","Hagle","Storm","Vidde","Mose","Kvist","Furu","Lerke","Skjær","Teig","Myr","Rabb"]
B2 = {"Housing cooperative":["Borettslag","Sameie"],"Farm":["Gård","Gårdsdrift"],"Commercial":["Eiendom","Logistikk","Handel","Verksted","Bygg"]}
customers, site_of = [], {}
for i in range(1, 3201):
    site = random.choices(SITES, [s[7] for s in SITES])[0]
    seg = pick(SEGMENTS)
    cid = f"C{100000+i}"
    name = f"Private customer {cid}" if seg == "Residential" else \
           f"{random.choice(B1)}{random.choice(['li','vik','dal','nes','haug','berg'])} {random.choice(B2[seg])} (demo)"
    created = rand_date(START - dt.timedelta(days=200), END - dt.timedelta(days=20))
    customers.append([cid, name, seg, site[0], pick(SRC), d(created)])
    site_of[cid] = (site, seg, created)
write("customer", ["customer_id","customer_name","segment","site_id","lead_source","created_date"], customers)

# ---------------------------------------------------------------- proposals, orders, invoices, installs
proposals, qlines, orders, olines, invoices, installs, activities = [], [], [], [], [], [], []
pending_battery = []
q_no, o_no, inv_no, act_no, inst_no = 30000, 70000, 900000, 500000, 1000
def season_weight(day):   # more proposals in spring
    return 0.55 + 0.75 * max(0, math.sin(math.radians((day.timetuple().tm_yday - 30) * 360 / 365)))
def price_index(day):     # panel prices fell through 2023-24
    m = (day.year - 2023) * 12 + day.month
    return max(0.78, 1.0 - 0.009 * m)

LOSS_REASONS = [("Price",0.34),("Chose competitor",0.22),("Postponed",0.18),("No roof approval",0.07),
                ("Financing",0.09),("No response",0.10)]

for cid, (site, seg, created) in site_of.items():
    n_proposals = 1 if random.random() < 0.82 else 2
    for _ in range(n_proposals):
        # proposal date, seasonally weighted
        for _try in range(10):
            qd = rand_date(max(START, created), END - dt.timedelta(days=3))
            if random.random() < season_weight(qd) / 1.3: break
        q_no += 1; qid = f"PR-{q_no}"
        seller = seller_for(site)
        # system size
        if seg == "Residential": kwp = random.choice([6,8,8,10,10,12,14,16])
        elif seg == "Farm": kwp = random.choice([20,30,40,60,80])
        elif seg == "Housing cooperative": kwp = random.choice([30,50,80,120])
        else: kwp = random.choice([25,40,60,100,150])
        panel = random.choices(["PV-410","PV-440","PV-380B"], [5,3,2])[0]
        n_pan = max(6, round(kwp * 1000 / int(PROD[panel][1].split()[1])))
        battery = random.random() < (0.42 if seg == "Residential" else 0.18) * (1 + 0.15 * (qd.year - 2023))
        evc = seg == "Residential" and random.random() < 0.28
        lines = [(panel, n_pan)]
        if kwp <= 10: lines.append(("INV-5" if kwp <= 6 else "INV-8", 1))
        else:
            n30, rest = divmod(kwp, 30)
            if n30: lines.append(("INV-30", n30))
            if rest: lines.append(("INV-15", 1) if rest > 8 else ("INV-8", 1))
        if battery: lines.append(("BAT-10", 1) if random.random() < 0.6 else ("BAT-5", random.choice([1,2])))
        if evc: lines.append(("EVC-11", 1))
        mount = "MNT-GND" if seg == "Farm" and random.random() < 0.5 else random.choice(["MNT-TIL","MNT-STL"])
        lines += [(mount, n_pan), ("CBL-KIT", 1 + kwp // 30), ("MTR-1", 1)]
        if random.random() < 0.35: lines.append(("OPT-1", n_pan))
        if site[4] > 62 or random.random() < 0.15: lines.append(("SNW-G", max(4, n_pan // 2)))
        lines += [("LAB-INST", round(6 + kwp * 1.1)), ("LAB-ELEC", round(4 + kwp * 0.35))]
        if seg != "Farm" and random.random() < 0.55: lines.append(("SCF-1", 1 + kwp // 40))
        if random.random() < 0.6: lines.append(("APP-MON", 1))
        disc = random.choice([0,0,0,0.03,0.05,0.08,0.10]) + (0.04 if seg == "Commercial" else 0)
        q_total = 0; cur_q = []
        for ln, (code, qty) in enumerate(lines, 1):
            p = PROD[code][4] * (price_index(qd) if PROD[code][2] in ("Panel","Inverter","Battery") else 1)
            unit = round(p * (1 - disc), 2)
            q_total += unit * qty
            row = [qid, ln, code, qty, unit, round(unit * qty, 2)]; qlines.append(row); cur_q.append(row)

        sent = qd + dt.timedelta(days=random.choice([0,0,1,1,2,3,5,8]))
        valid_until = sent + dt.timedelta(days=30)

        # ---- follow-up activities (drives the follow-up analysis)
        followed = random.random() < (0.58 if seller != "SE09" else 0.35)
        fu_day = sent + dt.timedelta(days=random.choice([2,3,3,4,7,7,8,10,14]))
        if followed and fu_day <= END:
            act_no += 1
            activities.append([f"AC-{act_no}", qid, seller, d(fu_day), random.choices(["Phone call","Email","Site visit"],[6,3,1])[0], "Completed"])
        elif fu_day <= END and random.random() < 0.3:
            act_no += 1
            activities.append([f"AC-{act_no}", qid, seller, d(fu_day), "Phone call", "Planned"])

        # ---- outcome
        p_win = 0.30 + (0.11 if followed else 0) + (0.07 if pick(SRC) == "Referral" else 0) \
                - (0.06 if disc == 0 and kwp > 30 else 0) + (0.05 if battery else 0)
        decided_by = sent + dt.timedelta(days=random.randint(5, 55))
        if decided_by > END:
            status = "Open"; decided = None; reason = ""
        elif random.random() < p_win:
            status = "Won"; decided = decided_by; reason = ""
        else:
            status = "Lost" if random.random() < 0.8 else "Expired"
            decided = decided_by if status == "Lost" else valid_until
            reason = pick(LOSS_REASONS) if status == "Lost" else "No response"
        proposals.append([qid, cid, seller, d(qd), d(sent), d(valid_until), status, d(decided), reason, kwp, round(q_total, 2)])
        if status != "Won": continue

        # ---- order (with realistic deviations from the proposal)
        o_no += 1; oid = f"SO-{o_no}"
        od = decided
        o_total = 0; ol = 0
        cur_o = []
        for qln in cur_q:
            _, ln, code, qty, unit, _ = qln
            r = random.random()
            if PROD[code][2] in ("Battery","EV charging") and r < 0.12: continue           # removed from order
            if code == "OPT-1" and r < 0.30: continue
            if PROD[code][2] == "Panel" and r < 0.10: qty = max(6, qty - random.randint(2, 6))  # roof smaller than expected
            if code == "PV-440" and r > 0.93: code = "PV-410"                                # variant swap (supply)
            if code.startswith("LAB") and r < 0.35: qty = round(qty * random.uniform(0.9, 1.35))
            ol += 1; o_total += unit * qty
            row = [oid, ol, qid, ln, code, qty, unit, round(unit * qty, 2)]; olines.append(row); cur_o.append(row)
        if random.random() < 0.06:   # added on order, not proposed
            ol += 1; code = random.choice(["SNW-G","SCF-1","CBL-KIT"])
            row = [oid, ol, qid, "", code, 1, PROD[code][4], PROD[code][4]]; olines.append(row); cur_o.append(row); o_total += PROD[code][4]
        cancelled = random.random() < 0.035
        orders.append([oid, qid, cid, d(od), "Cancelled" if cancelled else "Delivered", round(o_total, 2)])
        if cancelled: continue

        # ---- installation
        lead = random.randint(14, 45) + (25 if od.month in (11,12,1,2) and site[4] > 60 else 0)
        inst_d = od + dt.timedelta(days=lead)
        if inst_d > END:
            # contract signed, installation not done yet: battery jobs here become the planned jobs in the risk model
            bkwh = sum((10 if c == "BAT-10" else 5 * q) for (_, _, _, _, c, q, _, _) in cur_o if c.startswith("BAT"))
            if bkwh: pending_battery.append((oid, cid, site[0], bkwh, inst_d))
            continue
        grid_d = inst_d + dt.timedelta(days=random.randint(1, 21))
        inst_no += 1; iid = f"IN-{inst_no}"
        bat_kwh = sum((10 if c == "BAT-10" else 5 * q) for (_, _, _, _, c, q, _, _) in cur_o if c.startswith("BAT"))
        pan_qty = sum(q for (_, _, _, _, c, q, _, _) in cur_o if c.startswith("PV"))
        pan_code = next(c for (_, _, _, _, c, _, _, _) in cur_o if c.startswith("PV"))
        kwp_inst = round(pan_qty * int(PROD[pan_code][1].split()[1]) / 1000, 2)
        azimuth = random.choice(["S","S","S","SE","SW","E/W"])
        installs.append([iid, oid, cid, site[0], d(inst_d), d(grid_d), kwp_inst, bat_kwh, azimuth, random.randint(15, 45)])
        # invoices: 30% deposit at order, rest after install
        inv_no += 1; invoices.append([f"IV-{inv_no}", oid, d(od), round(o_total * 0.3, 2), "Deposit"])
        inv_no += 1; invoices.append([f"IV-{inv_no}", oid, d(inst_d + dt.timedelta(days=3)), round(o_total * 0.7, 2), "Final"])

write("proposal", ["proposal_id","customer_id","seller_id","created_date","sent_date","valid_until","status","decided_date","loss_reason","proposed_kwp","proposal_total_nok"], proposals)
write("proposal_line", ["proposal_id","line_no","product_code","qty","unit_price_nok","line_total_nok"], qlines)
write("sales_order", ["order_id","proposal_id","customer_id","order_date","order_status","order_total_nok"], orders)
write("sales_order_line", ["order_id","line_no","proposal_id","proposal_line_no","product_code","qty","unit_price_nok","line_total_nok"], olines)
write("invoice", ["invoice_id","order_id","invoice_date","amount_nok","invoice_type"], invoices)
write("activity", ["activity_id","proposal_id","seller_id","activity_date","activity_type","status"], activities)
write("installation", ["installation_id","order_id","customer_id","site_id","installed_date","grid_connected_date","kwp","battery_kwh","orientation","tilt_deg"], installs)

# ---------------------------------------------------------------- production telemetry + faults + service
ORIENT = {"S":1.0,"SE":0.95,"SW":0.95,"E/W":0.84}
site_station = {s[0]: s[6] for s in SITES}
production, service, faults = [], [], []
svc_no = 0
for iid, oid, cid, sid, inst_d, grid_d, kwp, bat, orient, tilt in installs:
    start = dt.date.fromisoformat(grid_d); st = site_station[sid]
    pr = random.uniform(0.78, 0.86) * ORIENT[orient]          # performance ratio
    # injected problems: inverter faults, string failures, soiling/shading
    fault_windows = []
    if random.random() < 0.10:
        fs = rand_date(start + dt.timedelta(days=30), END)
        fault_windows.append((fs, fs + dt.timedelta(days=random.randint(3, 40)), 0.0, "Inverter fault"))
    if random.random() < 0.07:
        fs = rand_date(start + dt.timedelta(days=60), END)
        fault_windows.append((fs, fs + dt.timedelta(days=random.randint(20, 160)), random.uniform(0.55, 0.8), "String failure"))
    shading = random.uniform(0.82, 0.93) if random.random() < 0.06 else 1.0
    for fw in fault_windows:
        faults.append([iid, d(fw[0]), d(min(fw[1], END)), fw[3]])
    day = start
    while day <= END:
        irr, snow = wx[(st, day)]
        age_y = (day - start).days / 365
        snow_f = 0.05 if snow > 8 else (0.5 if snow > 2 else 1.0)
        f = 1.0
        for a, b, mult, _ in fault_windows:
            if a <= day <= b: f = min(f, mult)
        actual = kwp * irr * pr * shading * snow_f * f * (1 - 0.005 * age_y) * random.uniform(0.97, 1.03)
        production.append([iid, d(day), round(actual, 2)])
        day += dt.timedelta(days=1)
    # service visits: annual + fault-driven
    for y in range(1, 4):
        v = start + dt.timedelta(days=365 * y + random.randint(-20, 40))
        if v <= END and random.random() < 0.55:
            svc_no += 1; service.append([f"SV-{svc_no}", iid, d(v), "Annual service", round(random.uniform(1.5, 3), 1), 2900])
    for a, b, mult, kind in fault_windows:
        v = b + dt.timedelta(days=random.randint(0, 3))
        if v <= END:
            svc_no += 1; service.append([f"SV-{svc_no}", iid, d(v), kind + " repair", round(random.uniform(2, 6), 1), round(random.uniform(3500, 14000))])

write("production_daily", ["installation_id","date","kwh"], production)
write("service_visit", ["visit_id","installation_id","visit_date","visit_type","hours","cost_nok"], service)
write("fault_log_truth", ["installation_id","fault_start","fault_end","fault_type"], faults)

# ---------------------------------------------------------------- compliance (installation paperwork + inspections)
# Generic requirement names; a real installer would map these to the regulations that apply to them.
REQS = [("R01","Declaration of conformity","All installations",7,0),
        ("R02","Grid operator notification","All installations",14,0),
        ("R03","As-built documentation","All installations",30,0),
        ("R04","Warranty registration","All installations",30,0),
        ("R05","Battery installation record","Installations with battery",14,0),
        ("R06","Annual inspection","Commercial, farm and housing cooperative",365,1)]
write("compliance_requirement", ["requirement_id","requirement_name","applies_to","due_days","recurring"], [list(r) for r in REQS])
seg_of = {c[0]: c[2] for c in customers}
DEV_CATS = [("Labelling",30),("Cable routing",22),("Earthing",12),("Roof penetration",14),("Documentation",22)]
items, devs = [], []
it_no = dv_no = 0
def deviation(iid, found, source):
    global dv_no
    dv_no += 1
    sev = random.choices(["High","Medium","Low"], [15,40,45])[0]
    close = found + dt.timedelta(days={"High":random.randint(1,20),"Medium":random.randint(5,60),"Low":random.randint(10,150)}[sev])
    closed = None if (close > END or random.random() < 0.06) else close
    devs.append([f"DV-{dv_no}", iid, d(found), source, random.choices([c[0] for c in DEV_CATS],[c[1] for c in DEV_CATS])[0], sev, d(closed)])
for iid, oid, cid, sid, inst_d, grid_d, kwp, bat, orient, tilt in installs:
    idate, gdate = dt.date.fromisoformat(inst_d), dt.date.fromisoformat(grid_d)
    discipline = 0.78 if idate < dt.date(2025, 3, 1) else 0.94      # digital handover checklist introduced March 2025
    dues = []
    for rid, _, _, days, rec in REQS:
        if rid == "R05" and bat == 0: continue
        if rid == "R06":
            if seg_of[cid] == "Residential": continue
            k = 1
            while gdate + dt.timedelta(days=365 * k) <= END + dt.timedelta(days=90):
                dues.append((rid, gdate + dt.timedelta(days=365 * k), 30)); k += 1
        else:
            dues.append((rid, idate + dt.timedelta(days=days), days))
    for rid, due, window in dues:
        it_no += 1
        start = due - dt.timedelta(days=window)
        if due > END:
            sub = rand_date(start, END) if random.random() < 0.45 and start <= END else None
        elif random.random() < discipline:
            sub = rand_date(start, due)
        elif random.random() < 0.72:
            sub = due + dt.timedelta(days=random.randint(1, 75))
        else:
            sub = None
        if sub and sub > END: sub = None
        items.append([f"CI-{it_no}", iid, rid, d(due), d(sub)])
        if rid == "R06" and sub:
            for _ in range(random.choice([0,0,0,1,1,2,3])): deviation(iid, sub, "Annual inspection")
    if random.random() < (0.12 if idate < dt.date(2025, 3, 1) else 0.06):
        deviation(iid, idate + dt.timedelta(days=random.randint(1, 10)), "Handover check")
write("compliance_item", ["item_id","installation_id","requirement_id","due_date","submitted_date"], items)
write("inspection_deviation", ["deviation_id","installation_id","found_date","source","category","severity","closed_date"], devs)

# ---------------------------------------------------------------- legacy ERP (2013–2022), frozen archive
# Solvi switched ERP on 1 Jan 2023. Old numbers differ from new ones; crosswalk tables map what can be mapped.
LEG_START, LEG_END = dt.date(2013, 1, 1), dt.date(2022, 12, 31)
LEG_PRODUCTS = [  # old item no, description, category, maps to current product (None = discontinued)
    ("100250","SOLARPANEL 250W POLY","Panel",None), ("100300","SOLARPANEL 300W MONO","Panel",None),
    ("100365","SOLARPANEL 365W MONO","Panel","PV-410"), ("200030","VEKSELRETTER 3KW","Inverter",None),
    ("200050","VEKSELRETTER 5KW HYBRID","Inverter","INV-5"), ("200150","VEKSELRETTER 15KW","Inverter","INV-15"),
    ("300048","BATTERI 4.8KWH","Battery",None), ("300100","BATTERI 10KWH","Battery","BAT-10"),
    ("400010","TAKFESTE TEGL","Mounting","MNT-TIL"), ("400020","TAKFESTE STÅL","Mounting","MNT-STL"),
    ("500001","KABELSETT DC","Electrical","CBL-KIT"), ("500010","ENERGIMÅLER","Electrical","MTR-1"),
    ("900001","MONTØR TIME","Service","LAB-INST"), ("900002","ELEKTRIKER TIME","Service","LAB-ELEC"),
    ("900010","SERVICEBESØK","Service","SVC-ANN"), ("910000","DIVERSE","Other",None),
]
LP = {p[0]: p for p in LEG_PRODUCTS}
write("legacy_product", ["old_item_no","description","category"], [[p[0], p[1], p[2]] for p in LEG_PRODUCTS])
write("product_xref", ["old_item_no","product_code"], [[p[0], p[3]] for p in LEG_PRODUCTS if p[3]])

leg_cust, cust_xref, leg_lines = [], [], []
old_no, lo_no = 40000, 100000
def leg_customer_history(oldid, seg, lat):
    global lo_no
    first = rand_date(LEG_START, LEG_END - dt.timedelta(days=200))
    kwp = random.choice([4,5,6,8]) if seg == "Residential" else random.choice([15,20,30,50])
    panel = "100250" if first.year < 2016 else ("100300" if first.year < 2019 else "100365")
    lo_no += 1; ono = f"{lo_no}"
    n_pan = max(6, round(kwp * 1000 / int(LP[panel][1].split()[1][:-1])))
    unit = {"100250":1900,"100300":2300,"100365":2400}[panel] * (1.25 if first.year < 2016 else 1.0)
    rows = [(panel, n_pan, unit), ("200050" if kwp <= 6 and first.year >= 2017 else ("200030" if kwp <= 6 else "200150"), 1, 18000),
            ("400010" if random.random() < .6 else "400020", n_pan, 450), ("500001", 1, 4200), ("500010", 1, 3600),
            ("900001", round(6 + kwp * 1.2), 820), ("900002", round(4 + kwp * .4), 980)]
    if first.year >= 2018 and random.random() < .25: rows.append(("300048" if first.year < 2020 else "300100", 1, 52000 if first.year < 2020 else 68000))
    for ln, (item, q, u) in enumerate(rows, 1):
        leg_lines.append([ono, ln, oldid, d(first), item, q, round(u * q, 2)])
    # follow-up business: service visits and small add-ons
    y = first.year + 1
    while y <= 2022:
        if random.random() < 0.45:
            dd = dt.date(y, random.randint(3, 10), random.randint(1, 28)); lo_no += 1
            items = [("900010", 1, 2400)] + ([("910000", 1, random.randint(300, 2500))] if random.random() < .4 else [])
            if random.random() < .08 and y >= 2019: items.append(("300100", 1, 66000))
            for ln, (item, q, u) in enumerate(items, 1):
                leg_lines.append([f"{lo_no}", ln, oldid, d(dd), item, q, round(u * q, 2)])
        y += 1
# existing customers who were also customers in the old system
for c in customers:
    cid, name, seg, sid = c[0], c[1], c[2], c[3]
    if random.random() < 0.30:
        old_no += 1; oldid = f"K-{old_no}"
        site = next(s for s in SITES if s[0] == sid)
        leg_cust.append([oldid, name.upper().replace(" (DEMO)", ""), site[1]])
        if random.random() < 0.96: cust_xref.append([oldid, cid])      # a few could not be matched
        leg_customer_history(oldid, seg, site[4])
# old customers who never moved to the new system
for _ in range(260):
    old_no += 1; oldid = f"K-{old_no}"; site = random.choices(SITES, [s[7] for s in SITES])[0]
    seg = random.choices(["Residential","Farm","Commercial"], [80, 10, 10])[0]
    leg_cust.append([oldid, f"PRIVATKUNDE {oldid}" if seg == "Residential" else f"{random.choice(B1).upper()}{random.choice(['LI','VIK','DAL'])} AS (DEMO)", site[1]])
    leg_customer_history(oldid, seg, site[4])
write("legacy_customer", ["old_customer_no","name","municipality"], leg_cust)
write("customer_xref", ["old_customer_no","customer_id"], cust_xref)
write("legacy_order_line", ["legacy_order_no","line_no","old_customer_no","order_date","old_item_no","qty","amount_nok"], leg_lines)

# ---------------------------------------------------------------- battery chain: supply, delivery and HSEQ risk
# Story: on 11 March 2026 a battery with transport damage, not inspected at goods receipt, was installed cold in a
# garage by a subcontractor crew. Three days later it overheated. Management asked for action. Quality answered that
# "days since last incident" warns nobody, and introduced risk factors across the chain with required actions
# from 1 April 2026 (RULE_DATE). Everything below is fictional.
random.seed(4242)
RULE_DATE = dt.date(2026, 4, 1)
INCIDENT_JOB_DATE = dt.date(2026, 3, 11)

SUPPLIERS = [  # id, name, type, country, battery damage rate
    ("SUP-B1", "Battery supplier A (demo)", "Battery", "Germany", .03),
    ("SUP-B2", "Battery supplier B (demo)", "Battery", "Sweden", .05),
    ("SUP-B3", "Battery supplier C (demo)", "Battery", "Poland", .12),
    ("SUP-S1", "Subcontractor Nord (demo)", "Installation subcontractor", "Norway", 0),
    ("SUP-S2", "Subcontractor Vest (demo)", "Installation subcontractor", "Norway", 0),
    ("SUP-S3", "Subcontractor Sør (demo)", "Installation subcontractor", "Norway", 0),
    ("SUP-S4", "Subcontractor Øresund (demo)", "Installation subcontractor", "Sweden", 0),
]
# safety prequalification windows for subcontractors; S2 let theirs lapse for a while
PREQUAL = {"SUP-S1": [(dt.date(2022,1,1), dt.date(2027,6,30))],
           "SUP-S2": [(dt.date(2022,1,1), dt.date(2025,8,31)), (dt.date(2026,4,20), dt.date(2028,4,19))],
           "SUP-S3": [(dt.date(2022,1,1), dt.date(2027,1,31))],
           "SUP-S4": [(dt.date(2022,6,1), dt.date(2026,12,31))]}
write("supplier", ["supplier_id","supplier_name","supplier_type","country"], [list(x[:4]) for x in SUPPLIERS])
write("supplier_prequal", ["supplier_id","valid_from","valid_to"], [[k, d(a_), d(b_)] for k, w in PREQUAL.items() for a_, b_ in w])

CREWS = [("CR-01","Own crew Oslo","Own",None), ("CR-02","Own crew Bergen","Own",None), ("CR-03","Own crew Trondheim","Own",None),
         ("CR-04","Own crew Stavanger","Own",None), ("CR-05","Own crew Gothenburg","Own",None),
         ("CR-11","Nord crew 1","Subcontractor","SUP-S1"), ("CR-12","Nord crew 2","Subcontractor","SUP-S1"),
         ("CR-21","Vest crew 1","Subcontractor","SUP-S2"), ("CR-22","Vest crew 2","Subcontractor","SUP-S2"),
         ("CR-31","Sør crew 1","Subcontractor","SUP-S3"), ("CR-41","Øresund crew 1","Subcontractor","SUP-S4")]
write("crew", ["crew_id","crew_name","crew_type","supplier_id"], [list(c) for c in CREWS])
REGION_CREWS = {"Østlandet":["CR-01","CR-11","CR-12"], "Innlandet":["CR-01","CR-12"], "Sørlandet":["CR-04","CR-31"],
                "Vestlandet":["CR-02","CR-04","CR-21","CR-22"], "Trøndelag":["CR-03","CR-11"], "Nord-Norge":["CR-03","CR-12"],
                "Västra Götaland":["CR-05","CR-41"], "Skåne":["CR-05","CR-41"], "Midtjylland":["CR-41"]}

# battery certifications: two-year validity, some crews renew late (gaps = uncertified periods)
certs, cert_windows = [], {}
for cid_, _, ctype, _ in CREWS:
    start = dt.date(2022, random.randint(3, 12), 1); wins = []
    while start <= dt.date(2026, 12, 31):
        end = start + dt.timedelta(days=730)
        wins.append((start, end)); certs.append([cid_, "Battery installation", d(start), d(end)])
        gap = random.choice([0,0,0,10]) if ctype == "Own" else random.choice([0,0,30,60,120])
        start = end + dt.timedelta(days=gap + 1)
    cert_windows[cid_] = wins
write("certification", ["crew_id","certification","valid_from","valid_to"], certs)
def valid(wins, day): return any(a <= day <= b for a, b in wins)

risk_rules = [  # code, factor, category, weight, stops work on its own
    ("DAMAGE_UNCHECKED","Damage signs on delivery, battery not inspected","Supply",4,1),
    ("PKG_DAMAGE","Packaging damaged on delivery","Supply",2,0),
    ("SHOCK","Shock indicator tripped in transport","Supply",2,0),
    ("NOT_INSPECTED","Not inspected at goods receipt","Supply",1,0),
    ("TEMP_EXCURSION","Temperature outside limits in transport or storage","Supply",2,0),
    ("LONG_STORAGE","Stored more than 60 days before installation","Supply",1,0),
    ("PREQUAL_EXPIRED","Subcontractor safety prequalification expired","Chain",2,0),
    ("UNCERTIFIED","Crew without valid battery certification","People",3,1),
    ("NEW_CREW","Crew's first battery jobs (fewer than 3)","People",1,0),
    ("COLD_BATTERY","Battery below 5 °C and not acclimatised before start-up","Handling",3,1),
    ("FROST_FORECAST","Frost forecast on a planned job: plan acclimatisation","Handling",2,0),
    ("NO_VENT_CHECK","Indoor location without ventilation check","Site",3,1),
    ("GARAGE","Installed in a garage with combustibles nearby","Site",1,0),
    ("NO_SJA","No safe job analysis before start","Planning",2,0),
    ("LATE","Job more than 14 days behind plan","Planning",1,0),
]
write("risk_rule", ["factor_code","factor","category","weight","stops_work"], [list(r) for r in risk_rules])
W_ = {r[0]: r[3] for r in risk_rules}; STOP = {r[0] for r in risk_rules if r[4]}

site_by_id = {s_[0]: s_ for s_ in SITES}; seg_by_cust = {c[0]: c[2] for c in customers}
station_of = {s_[0]: s_[6] for s_ in SITES}
deliveries, jobs, events, actions = [], [], [], []
crew_jobs = {}
incident_done = False
dl_no = jb_no = ev_no = ac_no = 0
def make_job(order_id, inst_id, cust, site_id, job_day, status):
    global dl_no, jb_no, ev_no, ac_no
    site = site_by_id[site_id]; st = station_of[site_id]; after = job_day >= RULE_DATE
    crew = random.choice(REGION_CREWS[site[2]]); crew_rec = next(c for c in CREWS if c[0] == crew)
    sup = random.choices(["SUP-B1","SUP-B2","SUP-B3"], [5,3,2])[0]; dmg_rate = next(x[4] for x in SUPPLIERS if x[0] == sup)
    storage = random.choice([1,2,3,5,7,10,14,21,30,45,75,95])
    delivered = job_day - dt.timedelta(days=storage)
    pkg = random.random() < dmg_rate
    shock = (pkg and random.random() < .5) or random.random() < .02
    inspected = random.random() < (.93 if after else .55)
    winter = delivered.month in (11,12,1,2,3)
    excursion = random.random() < (.10 if winter else .02)
    seg = seg_by_cust[cust]
    loc = random.choices(["Garage","Utility room","Technical room","Outdoor cabinet"], [35,25,15,25] if seg == "Residential" else [5,10,55,30])[0]
    indoor = loc != "Outdoor cabinet"
    planned = job_day - dt.timedelta(days=random.choice([0,0,0,0,3,7,10,20,30]))
    ambient = wtemp.get((st, job_day), 5.0)
    if status == "Done":
        vent = (not indoor) or random.random() < (.95 if after else .70)
        sja = random.random() < (.97 if after else .74)
        bat_temp = round(ambient + (random.uniform(-2, 4) if storage <= 2 else random.uniform(6, 12)), 1)   # fresh off the van vs stored indoors
        acclim = bat_temp >= 5 or random.random() < (.95 if after else .45)
        commissioned = random.random() < (.98 if after else .90)
    else:
        vent, sja, bat_temp, acclim, commissioned = None, None, None, None, None
    # the March incident, exactly as described in the story
    global incident_done
    if status == "Done" and job_day == INCIDENT_JOB_DATE and not incident_done:
        incident_done = True; is_incident = True
    else:
        is_incident = False
    if is_incident:
        crew, crew_rec, sup, pkg, shock, inspected, loc, indoor, vent, sja = "CR-21", next(c for c in CREWS if c[0] == "CR-21"), "SUP-B3", True, True, False, "Garage", True, True, False
        bat_temp, acclim, storage = -3.5, False, 1
        delivered = job_day - dt.timedelta(days=storage)
    dl_no += 1; did = f"DL-{dl_no}"
    deliveries.append([did, order_id, sup, f"B{sup[-1]}-{delivered.strftime('%y%m')}-{random.randint(10,99)}", d(delivered), int(pkg), int(shock), int(inspected), int(excursion), storage])
    jb_no += 1; jid = f"JB-{jb_no}"
    jobs.append([jid, order_id, inst_id or "", did, crew, d(planned), d(job_day), status, loc,
                 "" if vent is None else int(vent), "" if sja is None else int(sja), "" if bat_temp is None else bat_temp,
                 "" if acclim is None else int(acclim), "" if commissioned is None else int(commissioned)])
    # factors as the gold layer will compute them (used here only to drive realistic outcomes)
    n_prev = crew_jobs.get(crew, 0); crew_jobs[crew] = n_prev + 1
    f = set()
    if (pkg or shock) and not inspected: f.add("DAMAGE_UNCHECKED")
    if pkg: f.add("PKG_DAMAGE")
    if shock: f.add("SHOCK")
    if not inspected: f.add("NOT_INSPECTED")
    if excursion: f.add("TEMP_EXCURSION")
    if storage > 60: f.add("LONG_STORAGE")
    if crew_rec[3] and not valid(PREQUAL[crew_rec[3]], job_day): f.add("PREQUAL_EXPIRED")
    if not valid(cert_windows[crew], job_day): f.add("UNCERTIFIED")
    if n_prev < 3: f.add("NEW_CREW")
    if loc == "Garage": f.add("GARAGE")
    if status == "Done":
        if bat_temp < 5 and not acclim: f.add("COLD_BATTERY")
        if indoor and not vent: f.add("NO_VENT_CHECK")
        if not sja: f.add("NO_SJA")
        if (job_day - planned).days > 14: f.add("LATE")
    if status != "Done": return
    score = sum(W_[x] for x in f); red = bool(f & STOP) or score >= 6; yellow = not red and score >= 3
    # after the rule: red and yellow jobs get an action before start, which removes most of the risk
    mitigated = False
    if after and (red or yellow):
        ac_no += 1; done_ = random.random() < .95; mitigated = done_
        act = ("Stop until fixed: " + ", ".join(sorted(x.lower().replace("_", " ") for x in (f & STOP))) if red and f & STOP
               else "Supervisor check and toolbox talk before start")
        actions.append([f"AC-{ac_no}", jid, d(job_day - dt.timedelta(days=random.randint(0, 2))), "Red" if red else "Yellow", act, int(done_)])
    if pkg and inspected:
        ev_no += 1
        events.append([f"EV-{ev_no}", jid, d(delivered), "Good catch", "Low", "Damaged battery stopped at goods receipt and returned to supplier", "Warehouse"])
    if is_incident:
        ev_no += 1
        events.append([f"EV-{ev_no}", jid, d(job_day + dt.timedelta(days=3)), "Incident", "High",
                       "Battery overheated three days after installation in a garage. Fire service called, no injuries, garage wall damaged.", "Customer"])
        return
    eff = (score * .25 + (1 if red else 0)) if mitigated else score
    p = .008 + .014 * eff + (.06 if (red and not mitigated) else 0)
    if random.random() < p:
        ev_no += 1
        kind = random.choices(["BMS over-temperature warning in the first week", "Swollen cell found at first service",
                               "Hot DC connector found at commissioning", "Error code at start-up after cold charging",
                               "Battery mounted closer to combustibles than allowed"], [30,15,25,20,10])[0]
        sev = "Medium" if ("Swollen" in kind or "Hot" in kind) else "Low"
        events.append([f"EV-{ev_no}", jid, d(job_day + dt.timedelta(days=random.randint(0, 20))), "Near miss", sev, kind,
                       random.choice(["Own crew","Monitoring","Subcontractor","Customer"])])

inst_by_order = {i[1]: i for i in installs}
# the incident happened on the battery installation closest to 11 March 2026
INCIDENT_JOB_DATE = min((dt.date.fromisoformat(i[4]) for i in installs if i[7] > 0 and i[3] in [s_[0] for s_ in SITES if s_[3] == "Norway"]),
                        key=lambda x: abs((x - dt.date(2026, 3, 11)).days))
for i in sorted(installs, key=lambda r: r[4]):
    if i[7] > 0: make_job(i[1], i[0], i[2], i[3], dt.date.fromisoformat(i[4]), "Done")
# make sure the March incident job exists (pick the battery install closest to the date and move it)
for oid_, cid_, sid_, bk, inst_d_ in pending_battery:
    plan_day = END + dt.timedelta(days=random.randint(2, 16))
    make_job(oid_, None, cid_, sid_, plan_day, "Planned")
write("battery_delivery", ["delivery_id","order_id","supplier_id","batch_no","delivered_date","packaging_damage","shock_indicator_tripped",
                           "inspected_at_receipt","temp_excursion","storage_days"], deliveries)
write("job", ["job_id","order_id","installation_id","delivery_id","crew_id","planned_date","job_date","status","location",
              "ventilation_check_done","sja_done","battery_temp_c","acclimatised","commissioning_complete"], jobs)
write("hse_event", ["event_id","job_id","event_date","event_type","severity","description","reported_by"], events)
write("hse_action", ["action_id","job_id","action_date","risk_level","action","completed"], actions)

# weather forecast for the planned jobs (next two weeks)
fc = []
for st in STATIONS:
    lat = st[4]
    for k in range(1, 21):
        day = END + dt.timedelta(days=k)
        tmin = round(-1 - (lat - 58) * .5 + random.gauss(0, 3), 1)
        fc.append([st[6], d(END), d(day), tmin, round(tmin + random.uniform(3, 7), 1), round(abs(random.gauss(6, 3)), 1), round(max(0, random.gauss(2, 3)), 1)])
write("weather_forecast", ["station_id","issued_date","date","temp_min_c","temp_max_c","wind_ms","precip_mm"], fc)

print("done ->", OUT)
