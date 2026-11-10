# Assumptions

This file records every judgement call made while building BasketWise, as required by the PRD.
It grows as the project is built.

## Data

1. **Dataset.** The project uses the Kaggle *Groceries Dataset* with columns
   `Member_number`, `Date`, `itemDescription` (~38k rows, one item per row).
2. **Date format.** Dates are assumed to be **day-first** (`21-07-2015` = 21 July 2015) and are
   parsed with `dayfirst=True`.
3. **Missing file fallback.** If `data/Groceries_dataset.csv` is absent, the notebook runs
   `scripts/make_synthetic_data.py` to create a realistic synthetic replacement (seed 42).
   Synthetic use is flagged loudly in the notebook and in `stats.json` (`data_source`), and the
   website shows a "Demo data" banner.
4. **Basket definition.** One basket = one `Member_number` + one `Date`. Repeated rows of the
   same item inside a basket are collapsed to a single item (a set), because buying the same
   item twice is not a new association.
5. **Duplicates.** Only exact duplicate rows are removed. Repeated item lines within a basket
   are not treated as errors at row level, they are collapsed during basket building.
6. **Hidden missing values.** `"?"`, `"missing"`, `"n/a"`, `"--"`, `""`, `"NULL"` are treated as
   missing.
7. **Synthetic data.** Generated with a fixed seed (42), a Zipf-like item popularity curve, a
   handful of deliberately planted co-purchase pairs, and injected messy values, so the whole
   pipeline can be demonstrated without redistributing the real dataset.

## Notebook

8. **Runs on local or Colab.** `DATA_PATH` is defined once. In Colab the notebook first tries
   `/content/drive/MyDrive/Data Mining/Groceries_dataset.csv`, then falls back to `data/`.
9. **Thresholds.** Default `min_support=0.005` and `min_confidence=0.1`, with automatic
   adjustment if the result set is empty or unreadably large.
10. **Rules export.** `rules.json` keeps only rules with `lift > 1`, top 500 by lift.
11. **Numbers.** Every exported float is rounded to 4 decimals; `frozenset`s become sorted lists;
    no `NaN` or `Infinity` is allowed.

## Website (planned)

12. **Next.js**, App Router, TypeScript, Tailwind CSS and Recharts only, exported fully static
    (`output: 'export'`). All data is fetched client-side from `/data/*.json`.
13. **Notebook link.** A single `NOTEBOOK_URL` constant defaults to the notebook in the GitHub
    repository.
