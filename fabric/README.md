# Solvi in Fabric

One script builds the whole platform in your own Fabric tenant. Names have no underscores: workspaces like **Solvi Core**, lakehouses like **Core**, notebooks like **Core 1 Bronze**, tables like `factjobrisk`.

It builds:
- 6 domain workspaces, each with a lakehouse and 3 notebooks
- 24 shortcuts between the domains
- one pipeline per domain, plus a nightly pipeline that runs everything
- a reporting workspace with the Direct Lake semantic model "Solvi" (20 tables, 38 measures)

## 0. Account and capacity (once)

Fabric needs a work account (a Gmail address won't work) and a Fabric capacity.

1. Microsoft 365 Business Basic for `unadata.dev`, with `una@unadata.dev` as your sign-in.
2. A capacity. The free 60 day trial only works on tenants that are at least 90 days old. Until then, use a small paid one:
   - In portal.azure.com, signed in as `una@unadata.dev`, create a pay-as-you-go subscription.
   - Add a budget alert under Cost Management.
   - Create **Microsoft Fabric** capacity **solvifabric**, size F2, region Norway East.
   - It costs a few kroner an hour while running and nothing while paused. Pause it with `py fabric/solvifabric.py pause`.

## 1. Build it

From the repo root, in PowerShell:

```
py -m pip install azure-identity requests nbformat
py generator/generate.py
py notebooks/buildnotebooks.py
py fabric/solvifabric.py all
```

The script prints a short code. Open microsoft.com/devicelogin, type the code and sign in as `una@unadata.dev`. It remembers the login after that. The whole run takes about 30 to 45 minutes, mostly waiting for notebooks.

You can also run one step at a time. Each step is safe to run again.

| Command | What it does |
|---|---|
| `setup` | Workspaces, lakehouses, CSV upload, notebooks |
| `run` | For each domain in order: shortcuts, then bronze, silver, gold. `run hseq` runs one domain. |
| `pipelines` | **Run Core**, **Run Sales** and so on in each workspace, and **Run all** in Solvi Core |
| `pause` | Pauses the **solvifabric** capacity in Azure, so it stops costing money |
| `resume` | Starts it again |
| `check` | Shows your capacities and which one each Solvi workspace uses |
| `model` | The **Reporting** lakehouse with shortcuts to the gold tables, then the semantic model |

## 2. Check it

- Open **Solvi HSEQ** > **HSEQ** (lakehouse). The tables `factjobrisk` and `silverdqlog` should be there.
- Open **Solvi Reporting** > **Solvi** (semantic model). Make a quick table with **Risk level** and **Battery jobs**.
- Optional: add a schedule to **Run all**.

## If something fails

- **A notebook fails:** open it in Fabric and run it there to see the failing cell. Then run `run <domain>` again.
- **A notebook has no lakehouse:** open it, choose **Add lakehouse** and pick the lakehouse with the same name as the workspace, like **Core**.
- **The model fails:** the SQL endpoint may not have picked up the new shortcuts yet. Wait five minutes and run `model` again.
- **Something else:** send the error message to Claude.

## Next, by hand

1. Build the report in Power BI on the Solvi model. Suggested pages: battery risk, compliance, production, proposals.
2. Connect each workspace to this GitHub repo (Workspace settings > Git integration). Fabric then saves the model and the report as files here.
3. Take screenshots of the lineage view, the report and a failed quality gate for the README and the site.
