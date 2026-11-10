# PRD: Grocery Basket Recommender

A data mining lab project: Preprocessing, Association Rule Mining and Item Recommendation, with a companion website.

## 0. Instructions to the agent (read first)

You are building this whole project from scratch, autonomously. Work in the order of the milestones in section 12, and finish and verify each milestone before the next. Do not ask me questions. Where something is ambiguous, pick the simplest option that satisfies the acceptance criteria and write the assumption in `ASSUMPTIONS.md`.

**Priority rule:** The Jupyter/Colab notebook is the hero of this project. The website is a thin presentation layer that only displays what the notebook exports. Never put data mining logic in the website. If time is short, cut website polish, never notebook quality.

## 1. Overview

**Goal:** Take real grocery shopping data, clean it, mine frequent itemsets and association rules with Apriori and FP-Growth, and turn the rules into an item recommender ("customers who buy X also buy Y"). Export the results as JSON, then show them in a Next.js website.

**Context:** This is a solo university project for a Data Mining lab course (CSE 426). The lab topics used are data preprocessing, association rule mining (Apriori, FP-Growth, support/confidence/lift), and recommendation systems. The notebook must look like a clean, well-explained lab notebook, with markdown explanations for a student audience.

**Target users:** the course instructor and classmates evaluating the project, and anyone visiting the deployed demo.

## 2. Scope

**In scope**
- One Colab-compatible notebook: `notebooks/grocery_basket_recommender.ipynb`
- Four exported JSON files
- A Next.js site that consumes the JSON files
- README and assumptions file

**Out of scope**
- User accounts, databases, or any backend/API server
- Training ML models other than association rules (and one small optional item-similarity bonus)
- Real-time data or payments
- Python code running inside the website

## 3. Dataset

- **File:** `data/Groceries_dataset.csv` (Kaggle "Groceries Dataset")
- **Columns:** `Member_number`, `Date`, `itemDescription` (one row = one item bought by one member on one date; about 38k rows)
- **Date format:** assume day-first, for example `21-07-2015`. Parse with `dayfirst=True` and record the assumption.
- **Where it lives:** the user will place the real file at `data/Groceries_dataset.csv`.
- **If the file is missing:** run `scripts/make_synthetic_data.py`, which generates a realistic synthetic file with the same columns (about 38k rows, about 160 items, Zipf-like popularity, a few deliberately planted item pairs so that rules exist, and a few injected messy values such as extra spaces, mixed case, duplicate rows, and `?` placeholders). Save it as `data/Groceries_dataset.csv`. Print a loud warning in the notebook if synthetic data is in use. The pipeline must work identically on both files.
- **Notebook path handling:** in the first cells, try Google Drive first (`/content/drive/MyDrive/Data Mining/Groceries_dataset.csv`) only if running inside Colab, otherwise fall back to the local `data/` path. Use a `DATA_PATH` variable defined once.

## 4. Tech stack

**Notebook:** Python 3.10+, pandas, numpy, matplotlib, seaborn, mlxtend, json, time. Install cell: `!pip install -q mlxtend`. All imports (including `apriori`, `fpgrowth`, `association_rules`, `TransactionEncoder`) go in a single cell at the top so no `NameError` can occur later.

**Website:** Next.js (latest stable, App Router), TypeScript, Tailwind CSS, Recharts for charts. No other UI dependencies. The site must work as a fully static export (`output: 'export'`) so it deploys free on Vercel, Netlify, or GitHub Pages. All data is fetched client-side from `/data/*.json` in `public/`.

## 4b. Repository structure

```
grocery-basket-recommender/
├── README.md
├── ASSUMPTIONS.md
├── data/
│   └── Groceries_dataset.csv
├── scripts/
│   ├── make_synthetic_data.py
│   ├── build_notebook.py        # builds the .ipynb with nbformat
│   └── validate_exports.py      # checks JSON schemas, see section 8
├── notebooks/
│   └── grocery_basket_recommender.ipynb
├── export/                      # notebook output
│   ├── rules.json
│   ├── recommendations.json
│   ├── items.json
│   └── stats.json
└── web/                         # Next.js app
    └── public/data/             # copy of export/*.json
```

## 5. Notebook requirements (the hero)

Build the notebook with `nbformat` through `scripts/build_notebook.py`, then execute it end to end (`jupyter nbconvert --to notebook --execute --inplace`) so the saved file contains outputs and plots. It must run top to bottom in a fresh runtime with no errors.

**Style:** markdown heading before each section, a plain-English explanation after each important output, short comments in code, simple readable code. One small action per code cell. Keep consistent variable names: `df`, `basket_df`, `frequent_itemsets`, `rules`, `recommend`. Total notebook length about 40 to 50 cells. Avoid deprecated arguments and avoid `inplace=True` fillna patterns (assign the result back instead).

**Sections, in this order:**

**Part 0: Title and intro (markdown).** Project goal, dataset description, list of lab topics used.

**Part 1: Load and explore.** Load CSV, then `shape`, `head()`, `info()`, `describe()`, `nunique()`. Top 15 items via `value_counts()`. A markdown note after each output saying what to notice.

**Part 2: Data preprocessing.**
- Missing values: counts and percentages, with a bar chart if any exist.
- Hidden missing values: re-read with an `na_values` list (`"?"`, `"missing"`, `"n/a"`, `"--"`, `""`, `"NULL"`), and show counts before and after.
- Duplicates: same member buying the same item on the same date can be legitimate in basket data. Show the number of exact duplicate rows, explain the decision (remove exact duplicates, and collapse repeats of the same item inside one basket later using a set), and show before/after row counts.
- Clean `itemDescription`: strip whitespace, lowercase, fix inconsistent spellings if any are found.
- Convert `Date` to datetime with `dayfirst=True`, add `Year` and `Month` columns.
- Before/after summary table (rows, unique items, unique members).
- Final markdown cell listing every cleaning step.

**Part 3: Exploratory plots.** Top 15 items bar chart, purchases per month chart, basket size histogram. Each has a title, axis labels, and a one-line insight in markdown.

**Part 4: Build baskets.** A transaction is one `Member_number` + `Date`. Use `groupby` into lists of unique items. Show the transaction count and 3 example baskets. One-hot encode with `TransactionEncoder` into a boolean DataFrame `basket_df`, and show its shape and head.

**Part 5: Frequent itemsets and rules.**
- `apriori(basket_df, min_support=0.005, use_colnames=True)` with timing.
- `fpgrowth(...)` with the same support and timing.
- Comparison table: number of itemsets, runtime, whether results are identical.
- Add an itemset `length` column and show counts by size.
- Rules: `num_itemsets = len(frequent_itemsets)` then `association_rules(frequent_itemsets, metric="confidence", min_threshold=0.1, num_itemsets=num_itemsets)`. The `num_itemsets` argument is required by the current mlxtend version.
- Sort by `['lift','confidence','support']` descending. Show the top 20 rules.
- Markdown explaining support, confidence, and lift in simple words, with one real example from the results.
- A parameter tuning table: several `min_support` values against the number of itemsets and rules. If the defaults give zero rules or an unreadable number, the notebook must adjust the thresholds automatically and explain why.

**Part 6: Rule visualizations.** Support vs confidence scatter colored by lift, top 10 rules by lift as a bar chart (labels like `A -> B`), and a heatmap or bar chart of the strongest single-item to single-item rules.

**Part 7: Recommendation system.**
- `recommend(item, top_n=5)` returns a DataFrame with `recommended_item`, `confidence`, `lift`, `support`. It uses rules where the item is in the antecedents, ranks by lift then confidence, and returns an empty result with a friendly message if no rules exist.
- `recommend_for_basket(items, top_n=5)` uses rules whose antecedents are fully contained in the basket and excludes items already in it.
- Demo both on at least 5 popular items and 3 example baskets.
- **Bonus (short):** item-to-item similarity from a customer-item matrix using `1 / (1 + euclidean distance)` (the same similarity from the lab's collaborative filtering notebook) or cosine similarity. Compare its top 5 with the rule-based top 5 for 2 items, with a markdown comparison.

**Part 8: Export.** See section 6. Print each file's size and a preview. Create `export.zip`.

**Part 9: Conclusion (markdown).** What was cleaned, how many itemsets and rules were found, 3 interesting rules in plain language, Apriori vs FP-Growth observations, limitations (no ratings, no time awareness, small data), future work.

## 6. Data contracts (JSON exports)

All floats rounded to 4 decimals. No `NaN`, no `Infinity`. Convert `frozenset` to sorted lists. UTF-8 encoding.

**`rules.json`**: only rules with lift > 1, top 500 by lift.
```json
[
  {"antecedents": ["whole milk"], "consequents": ["yogurt"],
   "support": 0.0123, "confidence": 0.2345, "lift": 1.2345}
]
```

**`recommendations.json`**: every item that has rules maps to its top 5 recommendations.
```json
{ "whole milk": [ {"item": "yogurt", "confidence": 0.2345, "lift": 1.2345, "support": 0.0123} ] }
```

**`items.json`**: items present in `recommendations.json`, sorted by count descending.
```json
[ {"item": "whole milk", "count": 2502} ]
```

**`stats.json`**
```json
{
  "total_transactions": 0, "total_items": 0, "total_members": 0,
  "date_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
  "top_items": [{"item": "", "count": 0}],
  "monthly_counts": [{"month": "YYYY-MM", "count": 0}],
  "basket_size_distribution": [{"size": 1, "count": 0}],
  "algorithm_comparison": {
    "apriori": {"itemsets": 0, "runtime_sec": 0.0},
    "fpgrowth": {"itemsets": 0, "runtime_sec": 0.0},
    "identical_results": true
  },
  "parameters": {"min_support": 0.005, "min_confidence": 0.1},
  "data_source": "real | synthetic"
}
```

`scripts/validate_exports.py` must check all four files against these shapes and exit nonzero on any mismatch.

## 7. Website requirements

**Design:** clean, modern, responsive (mobile first), light and dark mode, a grocery/fresh feel (green accent), readable fonts, accessible contrast. Header with the project name and navigation, simple footer.

**Pages (App Router):**

1. **Home (`/`)**: hero section with the project title and one-line pitch; a stat cards row (transactions, unique items, members, rules found) from `stats.json`; a pipeline diagram section (Raw data → Cleaning → Baskets → Apriori/FP-Growth → Rules → Recommender) built with simple styled components; buttons to the recommender and to the notebook.
2. **Recommender (`/recommend`)**: a searchable dropdown (combobox) of items from `items.json`. Selecting one shows the top 5 recommendations as cards with confidence and lift, plus a one-line plain-language explanation such as "73% of baskets with X also had Y". Add a "basket mode" where the user picks several items and gets combined recommendations, computed in the browser by matching rules whose antecedents are fully contained in the chosen items. Handle no-result cases with a friendly message. Include an empty state and a loading state.
3. **Rules explorer (`/rules`)**: a sortable, filterable table from `rules.json` (columns: antecedents, consequents, support, confidence, lift). Add a text filter and sliders or inputs for minimum confidence and minimum lift. Client-side pagination (20 per page).
4. **Insights (`/insights`)**: charts from `stats.json` with Recharts: top items bar chart, monthly purchases line chart, basket size distribution, and Apriori vs FP-Growth comparison (itemsets and runtime), each with a one-sentence caption.
5. **Notebook and methodology (`/notebook`)**: explains each step of the pipeline in short sections (preprocessing, baskets, support/confidence/lift definitions with a worked example, Apriori vs FP-Growth), and a button linking to the notebook (use a configurable `NOTEBOOK_URL` constant, default to the file in the repo). If `stats.json` says `data_source` is `synthetic`, show a visible banner on every page: "Demo data".

**Technical rules:** fetch data client-side from `/data/*.json`, wrapped in a small typed data-loading hook with loading and error states. Define TypeScript types matching the contracts in section 6. Keep components small and reusable. No server code, no environment variables required. `next build` must succeed with zero type errors and zero lint errors, and the site must work as a static export.

## 8. Acceptance criteria

**Notebook**
- Executes top to bottom with no errors on both real and synthetic data.
- Saved file contains outputs and plots.
- Apriori and FP-Growth results are identical for the same support and are timed.
- At least 20 rules found with lift > 1 (on synthetic data too).
- `recommend()` returns correct, sorted results for 5 sample items, and the empty case is handled.
- All four JSON files are produced and `validate_exports.py` passes.

**Website**
- Production build succeeds (`npm run build`) with no errors.
- All five pages render using only the JSON files.
- Recommender returns results within 100 ms of selection.
- Works at 375px wide and on desktop, in light and dark mode.
- No console errors in the browser.

**Repo**
- README with: project summary, setup steps for the notebook, how to run the website (`npm install`, `npm run dev`), how to deploy (Vercel and GitHub Pages), how to update the data (re-run notebook, copy `export/*.json` into `web/public/data/`), and a screenshot placeholder section.
- `ASSUMPTIONS.md` listing every assumption made.

## 9. Non-functional requirements

- Beginner-readable code and explanations everywhere.
- Fixed random seeds where randomness is used (synthetic data uses `seed=42`).
- No secrets, API keys, or paid services.
- Only free tooling and dependencies.
- Keep website data under 2 MB total.

## 10. Risks and decisions

- **Zero or too many rules:** handled by the automatic threshold tuning in Part 5.
- **mlxtend API changes:** use `num_itemsets` in `association_rules`, and pin `mlxtend` in the notebook's install cell only if a version problem appears.
- **Dataset missing:** synthetic fallback, clearly flagged in the notebook and on the site.
- **Date parsing:** day-first assumption, documented.

## 11. Definition of done

The notebook runs cleanly and tells a clear story, the exports validate, the website builds and displays all the exported data, and the README lets a stranger run everything in under 10 minutes.

## 12. Milestones (do in order, verify each)

1. Scaffold the repo, write `make_synthetic_data.py`, and generate the data if the real file is missing.
2. Write `build_notebook.py` and generate the notebook (Parts 0 to 4), execute it, fix errors.
3. Add Parts 5 to 7, execute it, check the rules and recommender outputs.
4. Add Parts 8 and 9, produce `export/*.json`, write and run `validate_exports.py`.
5. Scaffold the Next.js app, define types and the data hook, copy the JSON files into `web/public/data/`.
6. Build the pages in this order: Home, Recommender, Rules, Insights, Notebook.
7. Polish: responsive layout, dark mode, empty and error states, README, ASSUMPTIONS.
8. Final check: re-run the notebook from scratch, re-validate the exports, run `npm run build`, and fix anything that fails. Write a short summary of what was built and what to do next.