# Assumptions

This file records every judgement call made while building BasketWise, as required by the PRD.
It grows as the project is built.

## Data

1. **Dataset.** The project uses a fixed sample of the **Complete Journey** study (84.51° /
   Dunnhumby), distributed by the public `completejourney` R package. `scripts/fetch_completejourney.py`
   downloads the raw files and derives `data/Groceries_dataset.csv` with columns
   `Member_number`, `Date`, `itemDescription`: 500 households (seed 42), 289,425 receipt lines,
   25,433 raw baskets, 294 product categories, dated 2017-01-01 to 2018-01-01. The mined "item"
   is `product_category`, not an SKU; `product_type` was rejected because its 2,242 labels are
   unreadable transaction codes.
2. **Dataset substitution.** The originally supplied Kaggle *Groceries Dataset* (38,765 rows,
   167 items) was mined first and produced only one item-to-item rule with lift > 1 at the PRD
   support of 0.005 (maximum lift 1.12); at 0.001 the best lift was 1.65 and no item had five
   rules. The user asked for a dataset with a usable signal, so the Complete Journey sample was
   adopted. Neither raw data file is committed.
3. **Date format.** Dates are written **day-first** (`21-07-2015` = 21 July 2015) and are parsed
   with `dayfirst=True`.
4. **Missing file fallback.** If `data/Groceries_dataset.csv` is absent, the notebook runs
   `scripts/make_synthetic_data.py` to create a realistic synthetic replacement (seed 42).
   The generator writes `data/DATA_SOURCE.txt`; while that file exists, the notebook and
   `stats.json` report `data_source = "synthetic"` and the website shows a "Demo data" banner.
   Delete the marker after rebuilding the CSV with `scripts/fetch_completejourney.py`.
5. **Basket definition.** One basket = one `Member_number` + one `Date`. Repeated rows of the
   same item inside a basket are collapsed to a single item (a set), because buying the same
   item twice is not a new association.
6. **Duplicates.** Only exact duplicate rows are removed. Repeated item lines within a basket
   are not treated as errors at row level, they are collapsed during basket building.
7. **Hidden missing values.** `"?"`, `"missing"`, `"n/a"`, `"--"`, `""`, `"NULL"` are treated as
   missing. The derived CSV retains 392 rows with no product category so the cleaning stage has
   something to remove.
8. **Synthetic data.** Generated with a fixed seed (42), a Zipf-like item popularity curve, a
   handful of deliberately planted co-purchase pairs, and injected messy values, so the whole
   pipeline can be demonstrated without redistributing the real dataset.
9. **Licensing.** The Complete Journey data is provided by 84.51° / Dunnhumby for academic use.
   The repository cites the source and the `completejourney` package, and keeps the raw files and
   derived CSV out of git (`.gitignore`).

## Notebook

10. **Runs on local or Colab.** `DATA_PATH` is defined once. In Colab the notebook first tries
    `/content/drive/MyDrive/Data Mining/Groceries_dataset.csv`, then falls back to `data/`.
11. **Thresholds.** Default `min_support=0.01` and `min_confidence=0.1`, with automatic
    adjustment if the result set is empty or unreadably large. Category-level baskets are dense:
    `0.005` built a ~40 GB candidate array and exhausted memory, while `0.01` yielded ~40,000
    rules, so the safety net raised support through `0.015` to a final `0.0225`.
12. **Rules export.** `rules.json` keeps only rules with `lift > 1` and caps the file at 500
    rules, ranked by lift. To keep the ledger and the recommender consistent, the selection first
    reserves each recommendable item's five best item-to-item rules, then fills the remaining
    slots with the highest-lift rules and re-sorts the whole file by lift. A strict lift-only top
    500 left some common items with no recommendation, which left the site's basket mode with
    nothing to match. The count, the `lift > 1` floor and the descending-lift order are
    unchanged.
13. **Recommendation shape.** `recommend(item)` uses rules whose antecedent is exactly that one
    item and whose consequent is one product. That keeps the website's explanation ("x% of
    baskets with this item also had that item") literally true. Multi-item antecedents are left
    to basket mode, which requires the whole antecedent to be in the basket.
14. **Numbers.** Every exported float is rounded to 4 decimals; `frozenset`s become sorted lists;
    no `NaN` or `Infinity` is allowed.
15. **Notebook length.** 32 code cells and 29 markdown cells (61 total), a little above the PRD's
    "about 40 to 50". The extra cells are short section headings and explanations; every code
    cell still performs one small action, which was kept ahead of hitting an exact cell count.

## Website

16. **Next.js**, App Router, TypeScript, Tailwind CSS and Recharts only, exported fully static
    (`output: 'export'`). All data is fetched client-side from `/data/*.json`.
17. **Notebook link.** A single `NOTEBOOK_URL` constant defaults to the notebook in the GitHub
    repository.
18. **Link prefetching.** Internal links set `prefetch={false}`. In a static export Next requests
    RSC payloads at dot-named paths that plain static hosts (GitHub Pages, `python -m http.server`)
    answer with 404; disabling prefetch keeps navigation client-side and the console clean.
