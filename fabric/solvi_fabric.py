"""Builds Solvi in Microsoft Fabric from this repo, using your own login.

    pip install azure-identity requests
    python generator/generate.py
    python notebooks/build_notebooks.py
    python fabric/build_model.py
    python fabric/solvi_fabric.py all

Steps (each can be run on its own, and each is safe to run again):
    setup      workspaces, lakehouses, CSV upload, notebooks
    run        for each domain in order: create its shortcuts, then run bronze, silver and gold
    pipelines  one pipeline per domain, and "Solvi nightly" in Solvi Core that runs all 18 notebooks in order
    model      lh_consume with shortcuts to the gold tables, and the Direct Lake semantic model "Solvi"
    all        all of the above
"""
import base64
import json
import os
import re
import sys
import time

import requests
from azure.identity import InteractiveBrowserCredential

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.fabric.microsoft.com/v1"
ONELAKE = "https://onelake.dfs.fabric.microsoft.com"
PBI = "https://api.powerbi.com/v1.0/myorg"
ORDER = ["core", "sales", "supply", "delivery", "assets", "hseq"]
STEPS = [("01", "bronze"), ("02", "silver"), ("03", "gold")]
REPORTING = "Solvi Reporting"

cred = InteractiveBrowserCredential()     # opens your browser once; sign in with una@unadata.dev
_tokens = {}


def token(scope):
    t = _tokens.get(scope)
    if not t or t.expires_on - time.time() < 300:
        t = _tokens[scope] = cred.get_token(scope)
    return t.token


def call(method, url, body=None, scope="https://api.fabric.microsoft.com/.default", ok=(200, 201, 202), **kw):
    for attempt in range(6):
        r = requests.request(method, url, json=body, headers={"Authorization": f"Bearer {token(scope)}"}, timeout=120, **kw)
        if r.status_code == 429:                                   # throttled: wait as told
            time.sleep(int(r.headers.get("Retry-After", 20)))
            continue
        if r.status_code not in ok:
            raise RuntimeError(f"{method} {url} -> {r.status_code}: {r.text[:500]}")
        return r
    raise RuntimeError(f"{method} {url}: still throttled")


def wait(r):
    """Fabric answers 202 for slow work; follow the Location header until the operation is done."""
    if r.status_code != 202:
        return r.json() if r.content else {}
    loc = r.headers["Location"]
    while True:
        time.sleep(int(r.headers.get("Retry-After", 5)))
        r = call("GET", loc)
        body = r.json() if r.content else {}
        status = body.get("status")
        if status in ("Succeeded", "Completed"):
            res = call("GET", loc + "/result", ok=(200, 404))
            return res.json() if res.status_code == 200 and res.content else body
        if status in ("Failed", "Cancelled", "Deduped"):
            raise RuntimeError(f"Operation failed: {json.dumps(body)[:800]}")


def listing(url):
    out, tok = [], None
    while True:
        u = url if not tok else url + ("&" if "?" in url else "?") + "continuationToken=" + requests.utils.quote(tok)
        body = call("GET", u).json()
        out += body.get("value", [])
        tok = body.get("continuationToken")
        if not tok:
            return out


def b64(s):
    return base64.b64encode(s.encode("utf-8") if isinstance(s, str) else s).decode()


# ---- workspaces, lakehouses, items -------------------------------------------------------------------------------
def capacity_id():
    caps = [c for c in listing(f"{API}/capacities") if c.get("state") == "Active"]
    if not caps:
        sys.exit("No active Fabric capacity. Start the Fabric trial first (see fabric/README.md).")
    trial = [c for c in caps if c.get("sku", "").startswith("FT")]
    return (trial or caps)[0]["id"]


def workspace(name, cap=None):
    for w in listing(f"{API}/workspaces"):
        if w["displayName"] == name:
            return w["id"]
    body = {"displayName": name, "capacityId": cap or capacity_id()}
    print(f"  + workspace {name}")
    return call("POST", f"{API}/workspaces", body).json()["id"]


def item(ws, kind, name, definition=None, path=None):
    """Get or create an item. With a definition, an existing item is updated to match the repo."""
    path = path or {"Lakehouse": "lakehouses", "Notebook": "notebooks", "DataPipeline": "dataPipelines",
                    "SemanticModel": "semanticModels"}[kind]
    existing = next((i for i in listing(f"{API}/workspaces/{ws}/items?type={kind}") if i["displayName"] == name), None)
    if existing:
        if definition:
            wait(call("POST", f"{API}/workspaces/{ws}/{path}/{existing['id']}/updateDefinition?updateMetadata=true",
                      {"definition": definition}))
            print(f"  ~ {kind} {name}")
        return existing["id"]
    body = {"displayName": name}
    if definition:
        body["definition"] = definition
    print(f"  + {kind} {name}")
    res = wait(call("POST", f"{API}/workspaces/{ws}/{path}", body))
    if res.get("id"):
        return res["id"]
    return next(i["id"] for i in listing(f"{API}/workspaces/{ws}/items?type={kind}") if i["displayName"] == name)


def lakehouse(ws, name):
    return item(ws, "Lakehouse", name)


_tables = {}


def tables_path(ws, lh):
    """Lakehouses with schemas keep tables under Tables/dbo; older ones directly under Tables."""
    if lh not in _tables:
        props = call("GET", f"{API}/workspaces/{ws}/lakehouses/{lh}").json().get("properties", {})
        _tables[lh] = "Tables/dbo" if props.get("defaultSchema") else "Tables"
    return _tables[lh]


def state():
    """IDs of every domain workspace and lakehouse, looked up by name."""
    cap = capacity_id()
    s = {}
    for d in ORDER:
        ws = workspace(f"Solvi {d.title()}", cap)
        s[d] = {"ws": ws, "lh": lakehouse(ws, f"lh_{d}")}
    return s


# ---- upload --------------------------------------------------------------------------------------------------------
def upload(ws, lh, rel_path, data: bytes):
    url = f"{ONELAKE}/{ws}/{lh}/{rel_path}"
    st = "https://storage.azure.com/.default"
    call("PUT", url + "?resource=file", scope=st, ok=(200, 201))
    pos, chunk = 0, 4 * 1024 * 1024
    while pos < len(data):
        part = data[pos:pos + chunk]
        r = requests.patch(f"{url}?action=append&position={pos}", data=part,
                           headers={"Authorization": f"Bearer {token(st)}"}, timeout=300)
        if r.status_code not in (200, 202):
            raise RuntimeError(f"upload {rel_path}: {r.status_code} {r.text[:300]}")
        pos += len(part)
    call("PATCH", f"{url}?action=flush&position={pos}", scope=st, ok=(200,))


# ---- notebooks -----------------------------------------------------------------------------------------------------
def fabric_source(ipynb_path, ws, lh, lh_name):
    """Converts a repo notebook to Fabric's .py source format, with its default lakehouse attached."""
    nb = json.load(open(ipynb_path, encoding="utf-8"))
    meta = {"kernel_info": {"name": "synapse_pyspark"},
            "dependencies": {"lakehouse": {"default_lakehouse": lh, "default_lakehouse_name": lh_name,
                                           "default_lakehouse_workspace_id": ws}}}
    meta_lines = lambda m: "\n".join("# META " + l for l in json.dumps(m, indent=2).splitlines())
    out = ["# Fabric notebook source", "", "# METADATA ********************", "", meta_lines(meta), ""]
    for c in nb["cells"]:
        src = "".join(c["source"])
        if c["cell_type"] == "markdown":
            out += ["# MARKDOWN ********************", "", "\n".join("# " + l if l else "#" for l in src.splitlines()), ""]
        else:
            out += ["# CELL ********************", "", src, "", "# METADATA ********************", "",
                    meta_lines({"language": "python", "language_group": "synapse_pyspark"}), ""]
    return "\n".join(out) + "\n"


def notebook_name(d, step, layer):
    return f"{step}_{d}_{layer}"


def setup():
    s = state()
    for d in ORDER:
        ws, lh = s[d]["ws"], s[d]["lh"]
        folder = os.path.join(ROOT, "data", d)
        files = sorted(f for f in os.listdir(folder) if f.endswith(".csv"))
        print(f"{d}: uploading {len(files)} files")
        for f in files:
            upload(ws, lh, f"Files/landing/{d}/{f}", open(os.path.join(folder, f), "rb").read())
        for step, layer in STEPS:
            name = notebook_name(d, step, layer)
            src = fabric_source(os.path.join(ROOT, "notebooks", d, f"{name}.ipynb"), ws, lh, f"lh_{d}")
            item(ws, "Notebook", name, {"format": "fabricGitSource",
                                        "parts": [{"path": "notebook-content.py", "payload": b64(src), "payloadType": "InlineBase64"}]})
    return s


# ---- shortcuts and runs --------------------------------------------------------------------------------------------
def shortcut_rows():
    rows = []
    for line in open(os.path.join(ROOT, "notebooks", "SHORTCUTS.md"), encoding="utf-8"):
        m = re.match(r"\|\s*lh_(\w+)\s*\|\s*(\w+)\s*\|\s*lh_(\w+)\s*/\s*(\w+)\s*\|", line)
        if m:
            rows.append(m.groups())        # (consumer domain, shortcut name, source domain, table)
    return rows


def shortcut(ws, lh, name, src_ws, src_lh, table):
    call("POST", f"{API}/workspaces/{ws}/items/{lh}/shortcuts?shortcutConflictPolicy=CreateOrOverwrite",
         {"path": tables_path(ws, lh), "name": name,
          "target": {"oneLake": {"workspaceId": src_ws, "itemId": src_lh, "path": f"{tables_path(src_ws, src_lh)}/{table}"}}})


def run_notebook(ws, nb_id, label):
    r = call("POST", f"{API}/workspaces/{ws}/items/{nb_id}/jobs/instances?jobType=RunNotebook")
    loc, t0 = r.headers["Location"], time.time()
    while True:
        time.sleep(15)
        job = call("GET", loc).json()
        st = job.get("status")
        if st == "Completed":
            print(f"  ok   {label} ({time.time() - t0:.0f} s)")
            return
        if st in ("Failed", "Cancelled", "Deduped"):
            raise RuntimeError(f"{label} {st}: {json.dumps(job.get('failureReason'))[:800]}\n"
                               "Open the notebook in Fabric to see the failing cell.")


def run(only=None):
    s = state()
    rows = shortcut_rows()
    for d in ORDER:
        if only and d != only:
            continue
        print(f"{d}:")
        for consumer, name, src, table in rows:
            if consumer == d:
                shortcut(s[d]["ws"], s[d]["lh"], name, s[src]["ws"], s[src]["lh"], table)
        nbs = {i["displayName"]: i["id"] for i in listing(f"{API}/workspaces/{s[d]['ws']}/items?type=Notebook")}
        for step, layer in STEPS:
            name = notebook_name(d, step, layer)
            run_notebook(s[d]["ws"], nbs[name], name)


# ---- pipelines -----------------------------------------------------------------------------------------------------
def activity(name, ws, nb_id, after=None):
    return {"name": name, "type": "TridentNotebook", "state": "Active",
            "dependsOn": [{"activity": after, "dependencyConditions": ["Succeeded"]}] if after else [],
            "policy": {"timeout": "0.02:00:00", "retry": 0, "retryIntervalInSeconds": 30, "secureOutput": False, "secureInput": False},
            "typeProperties": {"notebookId": nb_id, "workspaceId": ws}}


def pipeline_def(activities, description):
    content = {"properties": {"description": description, "activities": activities}}
    return {"parts": [{"path": "pipeline-content.json", "payload": b64(json.dumps(content)), "payloadType": "InlineBase64"}]}


def pipelines():
    s = state()
    chain, prev = [], None
    for d in ORDER:
        ws = s[d]["ws"]
        nbs = {i["displayName"]: i["id"] for i in listing(f"{API}/workspaces/{ws}/items?type=Notebook")}
        acts, p = [], None
        for step, layer in STEPS:
            name = notebook_name(d, step, layer)
            acts.append(activity(name, ws, nbs[name], p))
            chain.append(activity(name, ws, nbs[name], prev))
            p = prev = name
        item(ws, "DataPipeline", f"pl_{d}", pipeline_def(acts, f"Solvi {d}: bronze, silver (quality gate), gold"))
    item(s["core"]["ws"], "DataPipeline", "pl_solvi_nightly",
         pipeline_def(chain, "All six domains in order. A failed quality gate stops everything after it."))
    print("Add a schedule to pl_solvi_nightly in Fabric if you want it to run every night.")


# ---- reporting lakehouse and semantic model ------------------------------------------------------------------------
def model():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import build_model
    build_model.check()
    build_model.build()
    s = state()
    ws = workspace(REPORTING)
    lh = lakehouse(ws, "lh_consume")
    for t in build_model.TABLES:
        src = build_model.SCHEMA[t]["domain"]
        shortcut(ws, lh, t, s[src]["ws"], s[src]["lh"], t)
    print(f"  {len(build_model.TABLES)} shortcuts in lh_consume")

    # the SQL endpoint takes a moment to appear and to pick up new shortcuts
    for _ in range(40):
        props = call("GET", f"{API}/workspaces/{ws}/lakehouses/{lh}").json()["properties"].get("sqlEndpointProperties", {})
        if props.get("provisioningStatus") == "Success" and props.get("connectionString"):
            break
        time.sleep(15)
    else:
        sys.exit("The SQL endpoint for lh_consume is not ready yet. Run `model` again in a few minutes.")
    time.sleep(60)

    parts = []
    base = os.path.join(build_model.OUT)
    for dirpath, _, files in os.walk(base):
        for f in files:
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, base).replace("\\", "/")
            text = open(full, encoding="utf-8").read()
            text = text.replace("{{SQL_SERVER}}", props["connectionString"]).replace("{{SQL_ENDPOINT_ID}}", props["id"])
            parts.append({"path": rel, "payload": b64(text), "payloadType": "InlineBase64"})
    sm = item(ws, "SemanticModel", "Solvi", {"format": "TMDL", "parts": parts})
    pbi = "https://analysis.windows.net/powerbi/api/.default"
    call("POST", f"{PBI}/groups/{ws}/datasets/{sm}/refreshes", {"type": "full"}, scope=pbi, ok=(200, 202))
    print("Semantic model 'Solvi' deployed and refresh started. Open Solvi Reporting in Fabric to build the report.")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "setup":
        setup()
    elif cmd == "run":
        run(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "pipelines":
        pipelines()
    elif cmd == "model":
        model()
    elif cmd == "all":
        setup(); run(); pipelines(); model()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
