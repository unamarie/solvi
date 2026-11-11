# Solvi in Fabric

One script builds the whole platform in your own Fabric tenant:
- 6 domain workspaces, each with a lakehouse and 3 notebooks
- 24 shortcuts between the domains
- one pipeline per domain, plus a nightly pipeline that runs everything
- a reporting workspace with the Direct Lake semantic model "Solvi" (20 tables, 38 measures)

## 0. Account and trial (once, about 30 minutes)

Fabric needs a work account. A Gmail address won't work.

1. Buy **Microsoft 365 Business Basic** for `unadata.dev`, and set up `una@unadata.dev` as your sign-in. You need a card.
2. Add the DNS records Microsoft asks for in Vercel, under Domains > unadata.dev > DNS.
3. Go to [app.fabric.microsoft.com](https://app.fabric.microsoft.com) and sign in as `una@unadata.dev`.
4. Select your account picture (top right), then **Start trial** and **Activate**. Keep the default region.

The trial lasts 60 days. It doesn't include the Fabric data agent, so that step needs a small paid capacity later (F2, paused when not in use).

## 1. Build it

From the repo root, in PowerShell:

```
pip install azure-identity requests nbformat
python generator/generate.py
python notebooks/build_notebooks.py
python fabric/solvi_fabric.py all
```

A browser window opens once. Sign in as `una@unadata.dev`. The whole run takes about 30 to 45 minutes, mostly waiting for notebooks.

You can also run one step at a time. Each step is safe to run again.

| Command | What it does |
|---|---|
| `setup` | Workspaces, lakehouses, CSV upload, notebooks |
| `run` | For each domain in order: shortcuts, then bronze, silver, gold. `run hseq` runs one domain. |
| `pipelines` | `pl_<domain>` in each workspace, and `pl_solvi_nightly` in Solvi Core |
| `model` | `lh_consume` with shortcuts to the gold tables, then the semantic model |

## 2. Check it

- Open **Solvi Hseq** > `lh_hseq`. The tables `fact_job_risk` and `silver_dq_log` should be there.
- Open **Solvi Reporting** > **Solvi** (semantic model). Make a quick table with `risk_level` and `Battery jobs`.
- Optional: in `pl_solvi_nightly`, add a schedule.

## If something fails

- **A notebook fails:** open it in Fabric and run it there to see the failing cell. Then run `run <domain>` again.
- **A notebook has no lakehouse:** open it, choose **Add lakehouse** and pick `lh_<domain>`.
- **The model fails:** the SQL endpoint may not have picked up the new shortcuts yet. Wait five minutes and run `model` again.
- **Something else:** send the error message to Claude.

## Next, by hand

1. Build the report in Power BI on the Solvi model. Suggested pages: battery risk, compliance, production, proposals.
2. Connect each workspace to this GitHub repo (Workspace settings > Git integration). Fabric then saves the model and the report as files here.
3. Take screenshots of the lineage view, the report and a failed quality gate for the README and the site.
