# BasketWise

**Smart grocery recommendations from shopping data.**

BasketWise is a solo CSE 426 (Data Mining and Warehouse Lab) project. It takes raw grocery
transaction records, cleans them, mines frequent itemsets and association rules with Apriori
and FP-Growth, and turns the rules into an item recommender. A small Next.js site presents the
exported results.

> The Jupyter/Colab notebook is the core deliverable. The website only displays what the
> notebook exports. No data mining logic lives in the web app.

## Results at a glance

| Measure | Value |
| --- | --- |
| Baskets after cleaning | 7,831 |
| Distinct items | 158 |
| Members | 2,482 |
| Frequent itemsets (support 0.0112) | 612 |
| Rules exported | 500 |
| Items with recommendations | 43 |
| Strongest rule by lift | `spices → chicken`, confidence 73.8%, lift 23.11 |
| Apriori / FP-Growth runtime | 0.13 s / 6.51 s, identical itemsets |

The run uses the synthetic demo dataset (`data/DATA_SOURCE.txt` present). Replacing it with the
Kaggle CSV and re-running the notebook changes these numbers; nothing in the site is hard-coded.

## Project layout

```
BasketWise/
├── README.md
├── ASSUMPTIONS.md
├── prd.md
├── data/                  # Groceries_dataset.csv (real or synthetic) + DATA_SOURCE.txt
├── scripts/
│   ├── make_synthetic_data.py
│   ├── build_notebook.py
│   └── validate_exports.py
├── notebooks/             # grocery_basket_recommender.ipynb (executed, with outputs)
├── export/                # rules, recommendations, items, stats (JSON)
└── web/                   # Next.js static site
```

## Roadmap

- [x] Repository scaffold
- [x] Synthetic data generator
- [x] Notebook: preprocessing and baskets (Parts 0-4)
- [x] Notebook: Apriori / FP-Growth / recommender (Parts 5-7)
- [x] Notebook: exports and conclusion (Parts 8-9) + export validation
- [x] Next.js website: home, recommender, rules, insights, methodology
- [x] Deployment notes and screenshot placeholders

## Quick start: data mining

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. (Optional) create the synthetic demo dataset if data/Groceries_dataset.csv is missing
python scripts/make_synthetic_data.py

# 3. Build and run the notebook
python scripts/build_notebook.py
python -m nbconvert --to notebook --execute --inplace notebooks/grocery_basket_recommender.ipynb

# 4. Validate the exported JSON
python scripts/validate_exports.py
```

The executed notebook is committed with outputs and plots, so you can read it without running
anything. Open it in Jupyter, VS Code, or upload it to Google Colab.

### Real vs synthetic data

If `data/Groceries_dataset.csv` is missing, `scripts/make_synthetic_data.py` creates a realistic
demo file (seed 42) plus `data/DATA_SOURCE.txt`. That marker tells the notebook and the website to
label the run as **synthetic/demo**. To use the real Kaggle file, replace
`data/Groceries_dataset.csv`, delete `data/DATA_SOURCE.txt`, and re-run the notebook.

## Quick start: website

Requires Node.js 20 or newer.

```bash
cd web
npm install
npm run dev
```

Open <http://localhost:3000>. The production build is a fully static export:

```bash
cd web
npm run build     # writes web/out/
npx serve out     # or any static file server
```

The site fetches its four JSON files from `/data/*.json` at runtime. They live in
`web/public/data/` and are copies of `export/*.json`. There is no server code, no database and no
required environment variable.

### Updating the data

1. Re-run the notebook as shown above.
2. Run `python scripts/validate_exports.py` and confirm it passes.
3. Copy the new exports into the site:

   ```bash
   # macOS / Linux
   cp export/*.json web/public/data/

   # Windows PowerShell
   Copy-Item export\*.json web\public\data\ -Force
   ```

4. Reload the site. The homepage counts, rule ledger, charts and recommendations all follow the
   files automatically.

### Deploying

**Vercel (recommended).** Import the repository, set the project root to `web`, and keep the
default build command `npm run build`. Vercel detects the static export; no environment variables
are needed. Add a `vercel.json` only if you add redirects later.

**GitHub Pages.** Push the repository, then publish `web/out`:

```bash
cd web
npm run build
npx gh-pages -d out
```

This works when the site is served from a domain root, for example a user site
(`username.github.io`) or a custom domain. A project site served from
`username.github.io/BasketWise/` needs `basePath: "/BasketWise"` in `next.config.ts` **and** the
data URLs in `src/lib/useJson.ts` calls prefixed with the same base path, because the browser
requests `/data/*.json` by absolute path. The simplest free deployment is Vercel.

**Netlify.** Build command `npm run build`, publish directory `web/out`.

## What the site reads

| File | Used by | Contents |
| --- | --- | --- |
| `stats.json` | home, insights, methodology | counts, top items, monthly series, basket sizes, Apriori/FP-Growth timing, parameters, data-source flag |
| `rules.json` | rules, recommender basket mode | 500 rules (antecedents, consequents, support, confidence, lift), sorted by lift |
| `recommendations.json` | recommender item mode | each item mapped to its five best single-item follow-ups |
| `items.json` | recommender search | the 43 items that have recommendations, ordered by purchase count |

`scripts/validate_exports.py` checks the four files against their contracts (keys, types, value
ranges, ordering, and that `items.json` and `recommendations.json` describe the same item set)
before the site ever sees them.

## Pages

- `/` — hero, headline counts, the six-step pipeline and a printed recommendation slip.
- `/recommend/` — searchable item combobox, plus a basket mode that matches rules whose whole
  antecedent is present in the basket.
- `/rules/` — sortable, filterable ledger of all 500 rules with confidence and lift sliders and
  20-row pagination.
- `/insights/` — four Recharts figures: top items, monthly purchases, basket sizes and the
  algorithm comparison.
- `/notebook/` — the method in short sections: cleaning, basket construction, thresholds, a worked
  rule, the algorithm comparison, the exports and the data-source switch.

A "Demo data" banner appears on every page while `stats.json` reports `data_source: "synthetic"`.

## Screenshots

Replace the placeholders below with captures from the deployed site or a local production build.

| Page | Light | Dark |
| --- | --- | --- |
| Home | `docs screenshots/home-light.png` | `docs screenshots/home-dark.png` |
| Recommender | `docs screenshots/recommend-light.png` | `docs screenshots/recommend-dark.png` |
| Rules | `docs screenshots/rules-light.png` | `docs screenshots/rules-dark.png` |
| Insights | `docs screenshots/insights-light.png` | `docs screenshots/insights-dark.png` |
| Methodology | `docs screenshots/notebook-light.png` | `docs screenshots/notebook-dark.png` |

## Assumptions and AI use

Every data, threshold and export decision is recorded in [`ASSUMPTIONS.md`](ASSUMPTIONS.md),
including the raised support threshold, the curated rule export and the recommendation shape.

AI assistance (OpenCode) was used to draft the notebook prose, build scripts and the website.
Every number shown in the site is read from the exports, not written by hand; the notebook is the
source of truth and its committed outputs are the evidence. The demo dataset is synthetic and is
labelled as such in the UI. No paid services, API keys or secrets are involved.

## Notes

- Python dependencies are pinned in `requirements.txt`; Node dependencies in `web/package.json`.
- `web/` has its own `.gitignore` for `node_modules`, `.next` and `out`.
- The design tokens use a green grocery accent in light and dark mode; the site is responsive at
  375 px and up.
- Full requirements are in [`prd.md`](prd.md).
