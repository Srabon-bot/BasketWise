# BasketWise — dataset migration log

**Status:** complete. The project now mines the Complete Journey sample and the
site, exports and documentation all use the new numbers.

## What changed

The originally supplied Kaggle *Groceries Dataset* produced only one
item-to-item rule with lift > 1 at the PRD support (0.005). At 0.001 the best
lift was 1.65 and no item had five rules, so the project switched to a real
grocery dataset with a usable signal.

**Dataset:** a fixed 500-household sample (seed 42) of the **Complete Journey**
study (84.51° / Dunnhumby), distributed by the `completejourney` R package.
`scripts/fetch_completejourney.py` downloads the raw files once and derives
`data/Groceries_dataset.csv`. Raw data and the CSV are git-ignored and not
redistributed.

| Property | Value |
| --- | --- |
| Rows written | 289,425 |
| Baskets after cleaning | 25,431 |
| Households / members | 500 |
| Product categories (items) | 294 |
| Date range | 2017-01-01 to 2018-01-01 |
| Missing categories removed in cleaning | 392 |
| Final support / confidence | 0.0225 / 0.1 |
| Frequent itemsets | 763 |
| Rules (exported, capped) | 500 of 2,451 |
| Items with recommendations | 67 |
| Strongest rule | `cheeses → deli meats` (63.5%, lift 8.78) |

Mining notes: category-level baskets are dense. `0.005` exhausted memory
(~40 GB candidate array); `0.01` gave 39,858 rules, so the notebook's safety
net raised support through `0.015` to `0.0225`. Apriori and FP-Growth returned
identical itemsets; Apriori was faster (2.04 s vs 24.57 s).

## Site updates

- `web/public/data/*.json` refreshed from `export/*.json`.
- Default examples now use `cheeses` / `deli meats` and
  `dry noodles/pasta + beef → pasta sauce` instead of the old synthetic items.
- Insights copy covers one year (2017–2018), 294 categories, and slices the
  basket-size chart to 20 categories (data still exports the full tail).
- Rules page derives the lift slider maximum from the loaded rules (9, not 24).
- Notebook page reflects the new thresholds, dynamic confidence wording and the
  Complete Journey source.
- Footer and demo banner reference Complete Journey (84.51°).
- Docs updated: `README.md`, `web/README.md`, `ASSUMPTIONS.md`.

## Verification

- `python scripts/validate_exports.py` passes (500 rules, 67 items, source real).
- `npm run lint` and `npm run build` pass.
- Headless Chrome checks: all five routes, four `/data/*.json` files, light and
  dark, 1280 px and 375 px, no horizontal overflow, no console errors.
- Recommender: `cheeses → deli meats`; basket mode:
  `dry noodles/pasta + beef → pasta sauce`.
- Rules: 500 rules, 20 per page, filter and pagination work.
- Insights: four charts render; demo banner absent.

## Commands

```powershell
python scripts/fetch_completejourney.py
python scripts/build_notebook.py
python -m nbconvert --to notebook --execute --inplace notebooks/grocery_basket_recommender.ipynb
python scripts/validate_exports.py
Copy-Item export\*.json web\public\data\ -Force
cd web; npm run lint; npm run build
```

## Fallback

`python scripts/make_synthetic_data.py` restores the seeded synthetic CSV and
`data/DATA_SOURCE.txt`; re-run the notebook to return to the labelled demo run.
