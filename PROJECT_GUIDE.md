# BasketWise — Complete Project Guide

This document explains the whole project from beginning to end: what the data is, how it
flows through the pipeline, every data-mining technique and function that matters, and how
the notebook, exports and website fit together.

It is written for someone who has the repository open and wants to understand **why** each
step exists, not just **what** command to run.

---

## 1. What BasketWise does

BasketWise is a market-basket analysis project:

1. Take grocery receipts (who bought what, on which date).
2. Clean them.
3. Group the items into shopping baskets.
4. Mine **frequent itemsets** and **association rules** with **Apriori** and **FP-Growth**.
5. Turn the strongest rules into an item recommender.
6. Export the results as four JSON files.
7. Show those files in a static Next.js website.

The Jupyter notebook is the source of truth. The website is a thin presentation layer: it
does **no mining**, it only reads the exported JSON.

### One-sentence version

> “Customers who bought `cheeses` also bought `deli meats` 63.5% of the time, which is
> 8.78× more often than chance.”

That sentence is an association rule, and producing it reliably is the whole project.

---

## 2. The big picture

```
 Raw Complete Journey files
 (transactions.rds + products.rda)
            │
            │  scripts/fetch_completejourney.py
            │  • join product categories
            │  • keep 500 households (seed 42)
            │  • write 3 columns
            ▼
 data/Groceries_dataset.csv
 (Member_number, Date, itemDescription)
            │
            │  notebooks/grocery_basket_recommender.ipynb
            │
            ├─ 1. Load and explore
            ├─ 2. Clean
            ├─ 3. Exploratory plots
            ├─ 4. Build baskets
            ├─ 5. One-hot encode
            ├─ 6. Apriori + FP-Growth
            ├─ 7. Generate and evaluate rules
            ├─ 8. Build recommender functions
            ├─ 9. Export JSON
            ▼
 export/rules.json
 export/recommendations.json
 export/items.json
 export/stats.json
            │
            │  scripts/validate_exports.py
            │  (keys, types, ranges, ordering, lift > 1)
            ▼
 web/public/data/*.json
            │
            │  Next.js static site (no mining code)
            ▼
 Browser: home, recommender, rules, insights, notebook
```

### The three loops

The project is not a straight line; it has three feedback loops.

**Loop A — data loop**

```
new data → fetch/derive CSV → re-run notebook → validate → copy exports → rebuild site
```

**Loop B — mining loop**

```
choose min_support → mine itemsets → generate rules → count rules
        ↑                                              │
        └────────── too few / too many / OOM ←─────────┘
```

**Loop C — development loop**

```
edit code → execute notebook → validate exports → browser test → commit
```

The next sections walk through each loop in detail.

---

## 3. The dataset

### 3.1 Source

The project uses the **Complete Journey** study from **84.51° / Dunnhumby**, distributed by
the public `completejourney` R package. It contains household-level grocery transactions from
a real retailer.

Two raw files are downloaded by `scripts/fetch_completejourney.py`:

| File | What it contains |
| --- | --- |
| `transactions.rds` | one row per item line on a receipt (1,469,307 rows in the package sample) |
| `products.rda` | product metadata: `product_id`, `department`, `product_category`, `product_type`, … |

The raw files are cached in `data/raw/` and are **not committed** to git.

### 3.2 Why this dataset instead of the original Kaggle file

The supplied Kaggle *Groceries Dataset* was mined first. At the PRD support of `0.005` it
produced only **one** item-to-item rule with lift > 1 (max lift 1.12); at `0.001` the best
lift was 1.65 and no item had five rules. That is too little signal for a recommender, so the
project switched to Complete Journey, which has real grocery structure.

### 3.3 What the derived CSV looks like

`scripts/fetch_completejourney.py` writes exactly three columns:

| Column | Meaning |
| --- | --- |
| `Member_number` | household ID (integer) |
| `Date` | shopping date, written day-first (`13-01-2017`) |
| `itemDescription` | product **category**, lower-case (e.g. `cheeses`) |

One row is one purchased category by one household on one date. If a household bought the
same category twice on the same receipt, the row appears more than once; the notebook
collapses that later.

The script keeps a fixed random sample of **500 households** (seed 42). This keeps the CSV
and the one-hot matrix small enough to mine on a laptop while preserving real shopping
patterns.

### 3.4 Dataset facts used in this run

| Property | Value |
| --- | --- |
| Raw transaction lines in package sample | 1,469,307 |
| Households sampled | 500 |
| Rows written to CSV | 289,425 |
| Raw baskets (member + date) | 25,433 |
| Rows with no product category | 392 |
| Product categories (items) | 294 |
| Date range | 2017-01-01 to 2018-01-01 |
| Baskets after cleaning | 25,431 |

### 3.5 Why product categories, not SKUs

`product_type` has 2,242 labels with names like `Sft Drnk 2 Liter Btl Carb Incl`. That is
unreadable and extremely sparse. `product_category` has about 300 readable labels
(`cheeses`, `deli meats`, `pasta sauce`), which produces interpretable rules and a matrix
small enough for Apriori.

The trade-off: rules say “cheeses → deli meats”, not “this exact cheddar → this exact ham”.
That is recorded as a limitation.

### 3.6 Licensing and reproducibility

The data is provided for academic use. The repository:

- cites 84.51° / Dunnhumby and the `completejourney` package,
- keeps `data/Groceries_dataset.csv`, `data/raw/` and `export.zip` out of git,
- lets anyone rebuild the CSV with one script.

---

## 4. The workflow, stage by stage

| Stage | Input | Main work | Output |
| --- | --- | --- | --- |
| 0. Setup | repo | install Python/Node packages | working environment |
| 1. Derive data | raw `.rds`/`.rda` | join, sample, rename, write | `data/Groceries_dataset.csv` |
| 2. Load and explore | CSV | read, inspect shape/types/cardinality | understanding + EDA |
| 3. Clean | raw dataframe | missing, duplicates, text, dates | clean dataframe |
| 4. Explore | clean dataframe | top items, monthly counts, basket sizes | three charts |
| 5. Build baskets | rows | group by member + date, dedupe items | list of baskets |
| 6. Encode | baskets | one-hot boolean matrix | `basket_df` |
| 7. Mine itemsets | matrix | Apriori and FP-Growth | frequent itemsets |
| 8. Generate rules | itemsets | split itemsets into rules | rule table + metrics |
| 9. Tune | matrix | support sweep + safety net | final threshold |
| 10. Recommend | rules | item mode + basket mode | recommendation tables |
| 11. Export | results | JSON contracts | four JSON files |
| 12. Validate | JSON | schema and range checks | pass/fail |
| 13. Publish | JSON | copy to `web/public/data` | site data |
| 14. Build site | data + code | static export | `web/out/` |
| 15. Verify | built site | routes, data, mobile, console | signed-off site |

The rest of this guide explains each stage.

---

## 5. Step-by-step explanation

### Step 1 — Setup

Python dependencies are in `requirements.txt`:

```bash
pip install -r requirements.txt
```

Key packages:

| Package | Why it is needed |
| --- | --- |
| `pandas` | tabular data, grouping, cleaning |
| `numpy` | numeric arrays and cosine similarity |
| `mlxtend` | `TransactionEncoder`, `apriori`, `fpgrowth`, `association_rules` |
| `matplotlib`, `seaborn` | plots in the notebook |
| `pyreadr` | read the R `.rds` / `.rda` files |
| `nbformat`, `nbconvert`, `ipykernel` | build and execute the notebook |

The website needs Node.js 20.9+ and its packages are in `web/package.json`.

### Step 2 — Derive the CSV (`scripts/fetch_completejourney.py`)

The script does six things:

1. **Download or reuse raw files** — `download(name, url)` caches into `data/raw/`.
2. **Read R data frames** — `read_r(path)` uses `pyreadr.read_r()` and returns the only
   data frame in the file.
3. **Join product metadata** — merge `transactions` with
   `products[["product_id", "product_category"]]` on `product_id`.
4. **Keep real purchases** — drop lines with `quantity <= 0` (returns/refunds).
5. **Sample households** — `np.random.RandomState(42).choice(...)` chooses 500 households.
6. **Rename and write** — `Member_number`, `Date` (`%d-%m-%Y`), `itemDescription`
   (`product_category`, stripped and lower-cased).

Run it once:

```bash
python scripts/fetch_completejourney.py
```

The raw files and the derived CSV are ignored by git.

### Step 3 — Load and explore

The notebook reads the CSV with `pd.read_csv()` and records the raw size before touching
anything:

```python
df_raw = pd.read_csv(DATA_PATH)
before_rows = len(df_raw)
before_items = df_raw["itemDescription"].nunique()
before_members = df_raw["Member_number"].nunique()
```

It then inspects:

- `df_raw.info()` — column types, non-null counts.
- `df_raw.describe()` — numeric summary (not very meaningful for IDs).
- `df_raw.nunique()` — cardinality per column.
- `value_counts().head(15)` — most common raw item strings.

This is **descriptive analytics**: understand the data before modelling it.

### Step 4 — Clean

Cleaning is the most important stage. The notebook handles five issues:

| Problem | Detection | Fix |
| --- | --- | --- |
| Hidden missing values | re-read with `na_values=["?", "missing", "n/a", "--", "", "NULL"]` | treat them as `NaN` |
| Rows with no usable member/date/item | `dropna(subset=[...])` | drop the row |
| Exact duplicate rows | `df.duplicated()` / `drop_duplicates()` | keep one copy |
| Inconsistent item text | `str.strip().str.lower().str.replace(r"\s+", " ", regex=True)` | normalise |
| Dates stored as text | `pd.to_datetime(..., dayfirst=True, errors="coerce")` | real datetime |

#### Why duplicates are removed

The derived CSV has one row per **line item**, so buying two units of the same category on
the same date creates two identical rows. Association rules only care about **presence**
(“was this category in the basket?”), not quantity. Removing exact duplicates collapses
those repeated units without deleting genuine purchases on different dates.

This run:

- 289,425 rows in the raw CSV,
- 392 rows dropped for a missing category,
- 79,104 exact duplicates removed,
- 209,929 cleaned rows remain,
- 25,431 baskets.

#### Date features

After parsing, the notebook adds:

```python
df["Year"] = df["Date"].dt.year
df["Month"] = df["Date"].dt.to_period("M").astype(str)
```

These are used only for the monthly chart and descriptive statistics; the mining itself is
time-agnostic.

### Step 5 — Exploratory plots

Three quick charts before modelling:

1. **Top 15 items** — `value_counts().head(15).sort_values()` + horizontal bar chart.
2. **Purchases per month** — `groupby("Month").size()` + line chart.
3. **Basket size distribution** — number of distinct items per basket + histogram.

The charts answer practical questions: which categories dominate, is shopping seasonal, and
how large is a typical basket? In this run the average basket has **8.25 distinct
categories**, but the median is **5** because a long tail of large trips pulls the mean up.

### Step 6 — Build baskets

Association rule mining needs **transactions**, not one-row-per-item records.

```python
basket_series = (
    df.groupby(["Member_number", "Date"])["itemDescription"]
      .apply(lambda items: sorted(set(items)))
)
```

- `groupby(["Member_number", "Date"])` defines a basket.
- `set(items)` collapses repeated categories.
- `sorted(...)` makes the output stable and readable.

Result: **25,431 baskets**, each a list of unique category names.

A basket is sometimes called a **transaction** in data-mining literature.

### Step 7 — One-hot encode

Apriori and FP-Growth expect a boolean matrix: one row per basket, one column per item.

```python
te = TransactionEncoder()
te_array = te.fit(basket_series.tolist()).transform(basket_series.tolist())
basket_df = pd.DataFrame(te_array, columns=te.columns_)
```

Shape: **25,431 rows × 294 columns**. `True` means “this category was in that basket”.

This is **data transformation**: converting transaction lists into a machine-readable
matrix.

### Step 8 — Frequent itemsets with Apriori

```python
frequent_itemsets = apriori(
    basket_df,
    min_support=MIN_SUPPORT,
    use_colnames=True,
)
```

A **frequent itemset** is a set of items that appears in at least `min_support` fraction of
all baskets.

Apriori works in rounds:

1. Count single items; keep those above support.
2. Join frequent items to make candidate pairs.
3. Prune candidates whose subsets are not frequent.
4. Count survivors; repeat for 3-itemsets, 4-itemsets, …

The **Apriori principle**: if an itemset is frequent, every subset of it must also be
frequent; if a subset is infrequent, every superset can be discarded. This is what makes
the search tractable.

At the starting threshold `0.01`, this dataset produced **6,302 itemsets** in about **35 s**.

### Step 9 — Frequent itemsets with FP-Growth

```python
frequent_itemsets_fp = fpgrowth(
    basket_df,
    min_support=MIN_SUPPORT,
    use_colnames=True,
)
```

FP-Growth takes a different route:

1. Build an **FP-tree** (a compressed prefix tree of the baskets).
2. Keep a header table of item frequencies.
3. For each item, extract its **conditional pattern base**.
4. Recursively mine that smaller database.

It avoids candidate generation, which is its theoretical advantage on large, dense data.

In this run both algorithms returned **identical itemsets**, which is a strong correctness
check. Apriori was much faster (about **2 s** vs **27 s** at the final threshold) because the
Python implementation of FP-Growth pays tree-building overhead on this moderate-size
dataset. The project reports that measured result honestly instead of forcing the textbook
story.

### Step 10 — Generate association rules

```python
rules = association_rules(
    frequent_itemsets,
    metric="confidence",
    min_threshold=MIN_CONFIDENCE,
    num_itemsets=len(frequent_itemsets),
)
```

`association_rules` takes every frequent itemset and splits it into every valid
antecedent → consequent pair. For example, `{cheeses, deli meats}` becomes:

- `cheeses → deli meats`
- `deli meats → cheeses`

Each split is filtered by the metrics below and sorted by lift.

### Step 11 — Tune the support threshold

The starting threshold is `0.01`, but that produced **39,858 rules**, which is too many to
explore. The notebook therefore includes a **safety net**:

```python
chosen_support = MIN_SUPPORT
for _ in range(6):
    trial_itemsets = apriori(basket_df, min_support=chosen_support, use_colnames=True)
    trial_rules = association_rules(...)
    if len(trial_rules) == 0 and chosen_support > 0.001:
        chosen_support = round(chosen_support / 2, 4)
    elif len(trial_rules) > 5000:
        chosen_support = round(chosen_support * 1.5, 4)
    else:
        break
```

The logic is:

- If there are **no rules**, lower support.
- If there are **more than 5,000 rules**, raise support.
- Otherwise keep the threshold.

This run went:

```
0.01 → 0.015 → 0.0225
```

At `0.015` there were 9,745 rules; at `0.0225` there were 2,451, so the loop stopped.
The tuning table in the notebook also shows what happens at `0.02`, `0.03` and `0.05`.

**Why not just use 0.005?** Category-level baskets are dense. At `0.005`, Apriori tried to
allocate a candidate array of roughly **40 GB** and the process ran out of memory. The
notebook documents this and starts at `0.01`.

### Step 12 — Read the metrics

For a rule `X → Y`:

| Metric | Formula | Plain meaning |
| --- | --- | --- |
| Support | `count(X ∪ Y) / N` | how common the combination is |
| Confidence | `count(X ∪ Y) / count(X)` | how often Y is there when X is there |
| Lift | `confidence / support(Y)` | how much better than guessing Y from its popularity |

**Support** answers “is this pattern frequent enough to trust?”
**Confidence** answers “how reliable is the if-then guess?”
**Lift** answers “is this actually a relationship, or just a popular consequent?”

Lift values:

- `lift > 1` — X and Y appear together **more** than chance; positive association.
- `lift = 1` — independent; no relationship.
- `lift < 1` — **less** than chance; a substitute or anti-correlation.

The project exports only `lift > 1` rules to `rules.json`, because negative associations are
not useful as “also buy this” recommendations.

#### Worked example: `cheeses → deli meats`

- Support = 739 / 25,431 = **0.0291** (2.91% of baskets contain both).
- Confidence = 739 / 1,164 = **0.6349** (63.49% of cheese baskets also have deli meats).
- Deli-meat support = 1,839 / 25,431 = **0.0723**.
- Lift = 0.6349 / 0.0723 = **8.78**.

Interpretation: deli meats are popular on their own, but they are still **8.78× more likely**
when cheeses are in the basket. That is a real association, not just popularity.

### Step 13 — Recommend items

Two project functions turn rules into recommendations.

#### Item mode

```python
def recommend(item, top_n=5):
    ...
```

- Keeps rules whose antecedent is exactly `{item}`.
- Keeps single-item consequents, so one card = one product.
- Ranks by **lift**, then **confidence**.
- Removes duplicates and returns the top `top_n`.

Example:

```
cheeses → deli meats          lift 8.78, confidence 63.5%
cheeses → baked bread/...     lift 2.36, confidence 62.9%
cheeses → fluid milk products lift 2.02, confidence 60.4%
```

#### Basket mode

```python
def recommend_for_basket(items, top_n=5):
    ...
```

- Keeps rules whose **entire antecedent** is contained in the chosen basket.
- Drops consequents that are already in the basket.
- Ranks by lift, then confidence.

Example:

```
basket = ["dry noodles/pasta", "beef"]
→ pasta sauce          lift 8.75, confidence 44.7%
→ vegetables - shelf stable lift 3.97
→ pork                 lift 3.41
```

This is a lookup over exported rules, not new mining. The website repeats the same logic in
`recommendForBasket()` so basket mode works in the browser without Python.

#### Empty case

If no rule matches, both functions return an empty DataFrame with a helpful message rather
than crashing. The website shows a friendly empty state with a “Try cheeses” button.

### Step 14 — Bonus: cosine similarity

The notebook also computes an **item–item cosine similarity** from the basket matrix:

```python
item_matrix = basket_df.astype(int).T
row_norms = np.sqrt((item_matrix ** 2).sum(axis=1))
similarity = item_matrix.dot(item_matrix.T).div(row_norms, axis=0).div(row_norms, axis=1)
```

This answers a different question:

- **Association rules:** “what is bought *with* this item?” (complementary).
- **Cosine similarity:** “what has a similar audience?” (substitutes or peers).

The notebook compares the two side by side to show that they are not the same task. The
website does not use cosine similarity; it is an explanatory bonus.

### Step 15 — Export four JSON files

| File | Contents | Contract |
| --- | --- | --- |
| `rules.json` | strongest positive rules, capped at 500 | sorted by lift descending; only `lift > 1`; floats rounded to 4 decimals |
| `recommendations.json` | each item → top 5 single-item follow-ups | at most 5 per item; ranked by lift then confidence |
| `items.json` | items that have recommendations | sorted by purchase count descending |
| `stats.json` | headline numbers, charts, parameters, source flag | exact keys checked by the validator |

Important details:

- `frozenset` values become **sorted lists** so the JSON is stable.
- `as_list(itemset)` does that conversion.
- `r4(value)` rounds every metric to 4 decimals.
- `rules.json` reserves each recommendable item’s **five best item-to-item rules** before
  filling the rest with the highest-lift rules. This keeps the rule ledger and the
  recommender consistent.
- `stats.json` includes the **actual chosen support** (`0.0225`), not the starting value.

The notebook also writes `export.zip` for easy download. `export.zip` is git-ignored.

### Step 16 — Validate the exports

`scripts/validate_exports.py` is a **data contract test**. It checks:

- all four files exist and parse as JSON;
- `rules.json`: correct keys, sorted lists, round-to-4 floats, `0 ≤ support ≤ 1`,
  `0 ≤ confidence ≤ 1`, `lift > 1`, sorted by lift descending, at most 500 rules;
- `recommendations.json`: at most 5 per item, no self-recommendation, no duplicates,
  positive lift, ranked correctly;
- `items.json`: exactly `{item, count}`, non-negative counts, sorted descending, and the
  same item set as `recommendations.json`;
- `stats.json`: all required keys, valid date range, non-negative counts, valid parameters,
  `data_source` is `real` or `synthetic`.

Run it:

```bash
python scripts/validate_exports.py
```

If it fails, the site should not be updated. This is the **quality gate** between mining and
publishing.

### Step 17 — Publish to the website

```bash
python scripts/validate_exports.py
cp export/*.json web/public/data/          # macOS / Linux
```

```powershell
Copy-Item export\*.json web\public\data\ -Force   # Windows
```

The website reads these files at runtime from `/data/*.json`. It has no server, no database
and no mining code.

### Step 18 — Build and verify the site

```bash
cd web
npm run lint
npm run build
npx serve out
```

Checks:

- five routes: `/`, `/recommend/`, `/rules/`, `/insights/`, `/notebook/`;
- four JSON requests return 200;
- no “Demo data” banner when `stats.json` says `source: real`;
- recommender: `cheeses` shows deli meats;
- basket mode: `dry noodles/pasta + beef` shows pasta sauce;
- rules page: 500 rules, 20 per page, filters work;
- insights: four charts;
- 375 px and desktop, light and dark, console clean.

---

## 6. Data-mining techniques used

| # | Technique | What it means here | Where |
| --- | --- | --- | --- |
| 1 | **Data cleaning** | Fix missing values, duplicates, text and dates | notebook Part 2 |
| 2 | **Data integration** | Join transactions with product metadata | `fetch_completejourney.py` |
| 3 | **Data reduction / sampling** | 500 households; category-level items; deduplicate rows | fetch script + cleaning |
| 4 | **Data transformation** | Basket construction; one-hot encoding; date features | notebook Parts 2 and 4 |
| 5 | **Descriptive analytics / EDA** | Top items, monthly volume, basket-size distribution | notebook Part 3 |
| 6 | **Frequent itemset mining** | Find sets of categories that co-occur often | notebook Part 5 |
| 7 | **Apriori algorithm** | Candidate generation + downward-closure pruning | notebook Part 5 |
| 8 | **FP-Growth algorithm** | FP-tree + conditional pattern bases, no candidates | notebook Part 5 |
| 9 | **Association rule generation** | Split itemsets into antecedent/consequent rules | notebook Part 5 |
| 10 | **Interestingness evaluation** | Support, confidence, lift | notebook Parts 5–6 |
| 11 | **Parameter tuning / constraint mining** | Support sweep and safety net | notebook Part 5 |
| 12 | **Pattern visualisation** | Support–confidence scatter, top-lift bars | notebook Part 6 |
| 13 | **Recommendation (rule-based)** | Top-N item and basket recommendations | notebook Part 7 |
| 14 | **Similarity analysis** | Cosine similarity on item–basket vectors | notebook Part 7 bonus |
| 15 | **Cross-algorithm validation** | Compare Apriori and FP-Growth itemsets | notebook Part 5 |
| 16 | **Schema/contract validation** | Check exported JSON before publishing | `validate_exports.py` |
| 17 | **Static data presentation** | JSON → Next.js → Recharts | `web/` |

### Techniques explained in plain language

**Data cleaning.** Real data has missing values, duplicate rows, inconsistent spelling and
text dates. Cleaning makes the same real-world event look the same every time.

**Data integration.** Transactions know `product_id`; the product table knows the category.
Merging them gives each purchased line a readable item name.

**Data reduction and sampling.** Mining 1.47 million lines is unnecessary for a lab project.
A fixed 500-household sample is smaller but still statistically useful. Category-level
items reduce 2,242 product types to 294 readable groups.

**Data transformation.** Algorithms cannot read “a basket is a list of strings”. The basket
is converted into a boolean row: `True` for “in the basket”, `False` for “not in the basket”.

**Frequent itemset mining.** The goal is to find item combinations that appear often enough
to be interesting. “Often enough” is controlled by `min_support`.

**Apriori.** A level-wise algorithm. It uses the fact that a frequent itemset cannot contain
an infrequent subset, so it prunes aggressively. It is easy to explain but can use a lot of
memory on dense data.

**FP-Growth.** A divide-and-conquer algorithm. It stores the database in a compressed tree
and mines conditional databases. It avoids candidate generation, but tree construction has
its own cost.

**Association rules.** An itemset is not yet a rule. `{cheeses, deli meats}` becomes
`cheeses → deli meats` and `deli meats → cheeses`, and each direction can have a different
confidence.

**Interestingness metrics.** Support filters rare noise, confidence measures reliability,
and lift removes the effect of a very popular consequent. Using confidence alone would
recommend the most popular item to everyone.

**Parameter tuning.** Lower support = more rules but more noise and more memory. Higher
support = fewer, safer rules. The safety net keeps the rule set readable (≤ 5,000 before the
final export cap).

**Recommendation.** A recommender is the practical application of the rules: given what is
already in the basket, rank the remaining items by the strength of the matching rules.

**Similarity.** Cosine similarity compares the *profiles* of two items across all baskets.
It can surface substitutes (two similar breads) where association rules surface complements
(bread and butter).

**Validation.** A model is only useful if its output can be consumed reliably. The JSON
contract catches shape errors before the website sees them.

### What this project does **not** do

- No classification, regression or clustering as the main task.
- No deep learning.
- No time-aware rules (month is used only for a chart).
- No quantity weighting (a category is present or absent).
- No causal inference (“bought together” ≠ “causes”).

---

## 7. Function reference

This is the practical “what does this call do?” list. It is grouped by library.

### 7.1 Python standard library

| Function | What it does | Used in |
| --- | --- | --- |
| `Path.cwd()` | current working directory | notebook path resolution |
| `Path.exists()` | does a file exist? | dataset and fallback checks |
| `Path.parent` | parent folder | project-root detection |
| `Path / "name"` | join paths safely | all file paths |
| `Path.mkdir(exist_ok=True)` | create `export/` if missing | export cell |
| `Path.read_text()` / `write_text()` | read/write UTF-8 text | exports |
| `Path.stat().st_size` | file size in bytes | export preview |
| `json.dumps()` | Python object → JSON text | exports |
| `json.load()` | JSON file → Python object | validator, site data checks |
| `time.perf_counter()` | high-resolution timer | Apriori/FP-Growth timing |
| `zipfile.ZipFile(..., "w", ZIP_DEFLATED)` | create `export.zip` | export cell |
| `subprocess.run()` | call the synthetic fallback script | notebook fallback |
| `sys.modules` | detect Google Colab | path resolution |
| `urllib.request.urlretrieve()` | download raw files | fetch script |
| `sorted()`, `set()`, `len()`, `round()` | sorting, deduplication, counts | everywhere |

### 7.2 pandas

| Function | What it does | Example |
| --- | --- | --- |
| `pd.read_csv(path, na_values=...)` | load CSV; optionally treat tokens as missing | `pd.read_csv(DATA_PATH, na_values=HIDDEN_MISSING)` |
| `df.head(n)` | first n rows | inspection |
| `df.info()` | column types and non-null counts | inspection |
| `df.describe()` | numeric summary | inspection |
| `df.nunique()` | distinct values per column | cardinality |
| `df.isna().sum()` | missing count per column | missing audit |
| `df.dropna(subset=[...])` | remove rows missing key fields | cleaning |
| `df.duplicated()` | mark exact duplicate rows | duplicate audit |
| `df.drop_duplicates()` | remove exact duplicates | cleaning |
| `df.copy()` | avoid chained-assignment surprises | cleaning |
| `Series.str.strip()` | remove leading/trailing spaces | text normalisation |
| `Series.str.lower()` | lower-case item names | text normalisation |
| `Series.str.replace(pattern, repl, regex=True)` | collapse whitespace | text normalisation |
| `Series.replace(dict)` | spelling map | `uht milk` fix |
| `pd.to_datetime(series, dayfirst=True, errors="coerce")` | parse day-first dates | date cleaning |
| `Series.dt.year` | extract year | `Year` feature |
| `Series.dt.to_period("M")` | month bucket | monthly chart |
| `Series.dt.strftime("%d-%m-%Y")` | format dates for CSV | fetch script |
| `df.groupby([...])` | group rows by member/date/month | baskets, charts |
| `GroupBy.size()` | row count per group | monthly totals |
| `GroupBy.apply(func)` | custom aggregation per group | basket lists |
| `Series.value_counts()` | frequency table | top items |
| `Series.sort_values()` | sort ascending/descending | charts, rules |
| `Series.sort_index()` | sort by index | monthly series |
| `DataFrame.sort_values([...], ascending=...)` | multi-key sort | rules ranking |
| `DataFrame.reset_index(drop=True)` | clean row numbers | rules table |
| `DataFrame.to_frame(name)` | Series → one-column frame | display |
| `DataFrame.merge(other, on=..., how="left")` | join transactions + products | fetch script |
| `DataFrame.sample(n, random_state=...)` | random sample | example baskets |
| `DataFrame.itertuples()` | iterate rows efficiently | export builder |
| `DataFrame.round(n)` | round numeric columns | statistics |
| `pd.concat([...], axis=1)` | side-by-side comparison | rule vs similarity |
| `pd.set_option(...)` | display width/columns | notebook setup |
| `DataFrame.plot(kind=...)` | quick pandas chart | EDA |

### 7.3 NumPy

| Function | What it does | Used in |
| --- | --- | --- |
| `np.random.seed(42)` | reproducible random numbers | notebook setup |
| `np.random.RandomState(42).choice(...)` | fixed household sample | fetch script |
| `np.sqrt(...)` | vector norms for cosine similarity | bonus section |
| `matrix.T` | transpose item–basket matrix | cosine similarity |
| `matrix.dot(other)` | matrix multiplication (co-occurrence counts) | cosine similarity |
| `Series.div(...)` | element-wise division for normalisation | cosine similarity |
| `** 2` and `.sum(axis=1)` | squared norms | cosine similarity |

### 7.4 mlxtend

| Function | Signature (simplified) | What it does |
| --- | --- | --- |
| `TransactionEncoder()` | — | creates an encoder object |
| `.fit(transactions)` | list of lists | learns the item vocabulary |
| `.transform(transactions)` | list of lists | returns a boolean array |
| `.columns_` | attribute | item names in column order |
| `apriori(df, min_support=..., use_colnames=True)` | boolean DataFrame | returns frequent itemsets with a `support` column |
| `fpgrowth(df, min_support=..., use_colnames=True)` | boolean DataFrame | same output, FP-tree algorithm |
| `association_rules(itemsets, metric="confidence", min_threshold=..., num_itemsets=...)` | itemsets DataFrame | returns rules with `support`, `confidence`, `lift`, plus counts |

`num_itemsets` is required by newer mlxtend versions to compute metrics efficiently.

### 7.5 matplotlib / seaborn

| Call | What it does |
| --- | --- |
| `sns.set_theme(style="whitegrid", palette="Greens_r")` | consistent plot style |
| `plt.rcParams["figure.figsize"] = (10, 5)` | default figure size |
| `plt.figure(figsize=...)` | start a new figure |
| `Series.plot(kind="barh")` | horizontal bar chart |
| `Series.plot(kind="line", marker="o")` | monthly line chart |
| `plt.hist(values, bins=...)` | basket-size histogram |
| `plt.scatter(x, y, c=..., cmap=...)` | support vs confidence, coloured by lift |
| `plt.colorbar(scatter, label="Lift")` | lift legend |
| `plt.barh(labels, values)` | top-rules chart |
| `plt.title()`, `xlabel()`, `ylabel()` | labels |
| `plt.xticks(rotation=45)` | readable month labels |
| `plt.tight_layout()` | prevent clipping |
| `plt.show()` | render the figure |

### 7.6 Project functions

| Function | File | What it does |
| --- | --- | --- |
| `download(name, url)` | `fetch_completejourney.py` | download a raw file once, cache it |
| `read_r(path)` | `fetch_completejourney.py` | read the single data frame from an R file |
| `main()` | `fetch_completejourney.py` | run the whole derivation |
| `make_weights(n_items)` | `make_synthetic_data.py` | build a Zipf-like popularity curve for demos |
| `choose_basket_items(rng, ...)` | `make_synthetic_data.py` | draw a realistic synthetic basket |
| `inject_mess(df, rng)` | `make_synthetic_data.py` | add hidden missing values and noisy names |
| `main()` | `make_synthetic_data.py` | write the synthetic CSV and marker |
| `recommend(item, top_n=5)` | notebook | item-to-item recommendations from exact antecedents |
| `recommend_for_basket(items, top_n=5)` | notebook | recommendations whose whole antecedent fits the basket |
| `similarity_recommend(item, top_n=5)` | notebook | cosine-similarity item ranking |
| `as_list(itemset)` | notebook | frozenset → sorted JSON list |
| `r4(value)` | notebook | round a metric to 4 decimals |
| `md(text)` / `code(text)` | `build_notebook.py` | append markdown/code cells to the notebook |
| `fail(message)` | `validate_exports.py` | print a failure and exit non-zero |
| `load(path)` | `validate_exports.py` | read JSON with a clear error |
| `is_number(value)` / `is_probability(value)` | `validate_exports.py` | type/range guards |
| `check_float_rounding(value, label)` | `validate_exports.py` | enforce 4 decimals |
| `validate_rules(payload)` | `validate_exports.py` | rules contract |
| `validate_recommendations(payload)` | `validate_exports.py` | recommendations contract |
| `validate_items(payload, recommendations)` | `validate_exports.py` | items contract + cross-check |
| `validate_stats(payload)` | `validate_exports.py` | stats contract |
| `main()` | `validate_exports.py` | run all validators |

### 7.7 Website functions

| Function | File | What it does |
| --- | --- | --- |
| `useJson<T>(url)` | `web/src/lib/useJson.ts` | fetch a JSON file with loading/error/retry |
| `formatInteger(value)` | `web/src/lib/data.ts` | thousands separators |
| `formatPercent(value)` | `web/src/lib/data.ts` | `0.6349 → "63.5%"` |
| `formatLift(value)` | `web/src/lib/data.ts` | two decimal places |
| `formatSeconds(value)` | `web/src/lib/data.ts` | `2.0377 → "2.04 s"` |
| `ruleSide(items)` | `web/src/lib/data.ts` | `["a","b"] → "a + b"` |
| `ruleSentence(rule)` | `web/src/lib/data.ts` | natural-language rule |
| `recommendForBasket(rules, basket, topN)` | `web/src/lib/data.ts` | browser-side basket matching |

`recommendForBasket` is a **lookup**, not mining: it filters the 500 exported rules whose
antecedents are already in the basket, removes items the shopper has, and ranks by lift then
confidence.

---

## 8. Metrics and formulas

Let:

- `N` = number of baskets,
- `X` = antecedent itemset,
- `Y` = consequent itemset,
- `count(·)` = number of baskets containing the set.

```
support(X → Y)    = count(X ∪ Y) / N
confidence(X → Y) = count(X ∪ Y) / count(X)
lift(X → Y)       = confidence(X → Y) / support(Y)
                  = [count(X ∪ Y) / N] / [count(X)/N * count(Y)/N]
```

Important:

- **Support is symmetric:** `support(X → Y) = support(Y → X)`.
- **Confidence is not symmetric:** `cheeses → deli meats` and `deli meats → cheeses` have
  different confidence.
- **Lift is symmetric** for the pair, because it compares the joint frequency with the
  product of the marginals.

### Thresholds used

| Parameter | Value | Why |
| --- | --- | --- |
| `min_support` | `0.0225` final (started at `0.01`) | 2.25% of 25,431 ≈ 572 baskets minimum |
| `min_confidence` | `0.1` | a rule must be right at least 10% of the time |
| export rule floor | `lift > 1` | only positive associations |
| export cap | 500 rules | readable ledger and small JSON |

A minimum support of `0.0225` means an itemset must appear in at least
`0.0225 × 25,431 ≈ 572` baskets. That is why the surviving rules are supported by hundreds
of real baskets, not a handful.

---

## 9. Apriori vs FP-Growth

### Apriori in one paragraph

Apriori builds candidates level by level. It counts 1-itemsets, keeps the frequent ones,
joins them into 2-itemsets, prunes any pair with an infrequent subset, counts the survivors,
and repeats. Its correctness comes from the **downward-closure property**: every subset of a
frequent itemset is frequent. Its weakness is that it may generate many candidates and scan
the database repeatedly.

### FP-Growth in one paragraph

FP-Growth compresses the baskets into an FP-tree. Each node stores an item and a count; a
header table links nodes with the same item. To mine an item, it builds that item’s
conditional pattern base (the prefixes of baskets containing it) and recurses on a smaller
tree. It never generates candidates, so it often wins on large, dense databases.

### What happened here

| Threshold | Apriori itemsets | FP-Growth itemsets | Same? | Apriori time | FP-Growth time |
| --- | --- | --- | --- | --- | --- |
| `0.01` | 6,302 | 6,302 | yes | ~24.7 s | ~252.9 s |
| `0.0225` (final) | 763 | 763 | yes | ~2.0 s | ~27.1 s |

The identical itemsets are a correctness check. The surprising part is the runtime: Apriori
is much faster on this dataset. That is an honest empirical result, not a bug. FP-Growth’s
Python implementation spends time building and traversing trees, and 294 columns × 25k
baskets is not large enough for its asymptotic advantage to pay off.

### Final itemset sizes at `0.0225`

| Itemset length | Count |
| --- | --- |
| 1 item | 109 |
| 2 items | 380 |
| 3 items | 237 |
| 4 items | 36 |
| 5 items | 1 |
| **Total** | **763** |

---

## 10. Results snapshot

### Data

| Measure | Value |
| --- | --- |
| CSV rows | 289,425 |
| Rows after missing-category removal | 289,033 |
| Exact duplicates removed | 79,104 |
| Clean rows | 209,929 |
| Baskets | 25,431 |
| Members | 500 |
| Categories | 294 |
| Average basket size | 8.25 categories |

### Mining

| Measure | Value |
| --- | --- |
| Final support | 0.0225 (2.25%) |
| Final confidence | 0.1 (10%) |
| Frequent itemsets | 763 |
| Rules generated | 2,451 |
| Positive rules (`lift > 1`) | 2,449 |
| Item-to-item positive rules | 710 |
| Items with at least one recommendation | 67 |
| Exported rules | 500 |
| Exported recommendation items | 67 |

### Strongest rules

| Rule | Support | Confidence | Lift |
| --- | --- | --- | --- |
| `cheeses → deli meats` | 2.91% | 63.49% | 8.78 |
| `pasta sauce → dry noodles/pasta` | 2.69% | 52.73% | 8.75 |
| `baked bread/buns/rolls + beef → vegetables - shelf stable + fluid milk products` | 2.35% | 40% | 4.68 |

### Runtime

| Algorithm | Itemsets | Runtime |
| --- | --- | --- |
| Apriori | 763 | 2.04 s |
| FP-Growth | 763 | 24.57 s |

---

## 11. The four JSON files

### `rules.json`

```json
[
  {
    "antecedents": ["cheeses"],
    "consequents": ["deli meats"],
    "support": 0.0291,
    "confidence": 0.6349,
    "lift": 8.7796
  }
]
```

- Only `lift > 1`.
- Sorted by lift descending.
- At most 500 rules.
- Lists are sorted alphabetically.

### `recommendations.json`

```json
{
  "cheeses": [
    {
      "item": "deli meats",
      "confidence": 0.6349,
      "lift": 8.7796,
      "support": 0.0291
    }
  ]
}
```

- Every item with at least one single-item rule.
- At most 5 entries per item.
- Ranked by lift, then confidence.
- The site uses this for item mode.

### `items.json`

```json
[
  { "item": "soft drinks", "count": 7753 },
  { "item": "fluid milk products", "count": 7622 }
]
```

- Only items that appear in `recommendations.json`.
- Sorted by purchase count descending.
- The site uses this for the searchable combobox.

### `stats.json`

```json
{
  "total_transactions": 25431,
  "total_items": 294,
  "total_members": 500,
  "date_range": { "start": "2017-01-01", "end": "2018-01-01" },
  "top_items": [{ "item": "soft drinks", "count": 7753 }],
  "monthly_counts": [{ "month": "2017-01", "count": 18401 }],
  "basket_size_distribution": [{ "size": 1, "count": 3923 }],
  "algorithm_comparison": {
    "apriori": { "itemsets": 763, "runtime_sec": 2.0377 },
    "fpgrowth": { "itemsets": 763, "runtime_sec": 24.5744 },
    "identical_results": true
  },
  "parameters": { "min_support": 0.0225, "min_confidence": 0.1 },
  "data_source": "real"
}
```

`data_source` is `"real"` when `data/DATA_SOURCE.txt` is absent. If the synthetic fallback
runs, the marker exists and the value becomes `"synthetic"`.

### Recommendations edge case

`recommend()` ranks all single-item rules, so for an item with fewer than five positive
follow-ups a below-chance entry can appear. In this run, `coupon/misc items` has two entries
with lift below 1. The website shows the lift value, so the reader can see it. A future
improvement is to filter `lift > 1` inside `recommend()` as well as in the rule export.

---

## 12. Website architecture

### Routes

| Route | Purpose |
| --- | --- |
| `/` | hero, dataset counts, pipeline diagram, printed recommendation slip |
| `/recommend/` | item combobox + basket mode |
| `/rules/` | sortable, filterable, paginated rule ledger |
| `/insights/` | four Recharts figures |
| `/notebook/` | short written methodology |

### Data flow

```
web/public/data/*.json
        │
        │  useJson<T>(url) → fetch → loading / error / retry
        ▼
React client components
        │
        ├─ HomeClient: stats + first recommendation + pipeline
        ├─ RecommendClient: items + recommendations + rules
        ├─ RulesClient: filter, sort, paginate
        ├─ InsightsClient: Recharts
        └─ NotebookClient: stats + rules + prose
```

### Important design rules

- **No mining in the browser.** `recommendForBasket()` only filters exported rules.
- **Every number comes from JSON.** The site never hard-codes 25,431 or 8.78.
- **No silent blank states.** `useJson` exposes loading and error states, and the UI shows
  them.
- **Static export.** `next.config.ts` uses `output: "export"` and `trailingSlash: true`, so
  `web/out/` can be hosted on Vercel, Netlify, GitHub Pages or any static server.

### Demo banner

`DataBanner` checks `stats.data_source`. When it is `"synthetic"`, the banner appears on every
page. With the real Complete Journey run it is absent.

### Recharts figures

1. Top 15 items (horizontal bars).
2. Purchases per month (line).
3. Basket-size distribution (bars, chart sliced to sizes ≤ 20 while the JSON keeps the full
   tail to 73).
4. Apriori vs FP-Growth runtime (bars).

---

## 13. Repository map

```
BasketWise/
├── README.md                     # overview, results, quick start
├── ASSUMPTIONS.md                # every judgement call
├── PROJECT_GUIDE.md              # this document
├── prd.md                        # original assignment spec
├── requirements.txt              # Python dependencies
├── data/
│   ├── Groceries_dataset.csv     # derived 3-column dataset (git-ignored)
│   └── raw/                      # downloaded .rds/.rda (git-ignored)
├── scripts/
│   ├── fetch_completejourney.py  # raw data → CSV
│   ├── build_notebook.py         # generates the notebook source
│   ├── make_synthetic_data.py    # fallback demo data
│   └── validate_exports.py       # JSON contract tests
├── notebooks/
│   └── grocery_basket_recommender.ipynb   # executed notebook with outputs
├── export/                       # four JSON exports (+ export.zip, ignored)
├── web/
│   ├── public/data/              # copies of the four JSON files
│   ├── src/app/                  # routes and client components
│   ├── src/lib/                  # types, fetch hook, formatting, basket lookup
│   └── README.md                 # site-specific notes
└── docs/
    └── DEPLOY_VERCEL.md          # deployment walkthrough
```

---

## 14. How to run everything from scratch

```bash
# 1. Python environment
pip install -r requirements.txt

# 2. Build the dataset (downloads raw files once)
python scripts/fetch_completejourney.py

# 3. Generate and execute the notebook
python scripts/build_notebook.py
python -m nbconvert --to notebook --execute --inplace notebooks/grocery_basket_recommender.ipynb

# 4. Validate the four exports
python scripts/validate_exports.py

# 5. Publish the data to the site
cp export/*.json web/public/data/        # Windows: Copy-Item export\*.json web\public\data\ -Force

# 6. Build and serve the site
cd web
npm install
npm run lint
npm run build
npx serve out
```

If `data/Groceries_dataset.csv` is missing and you cannot download the real data, the notebook
automatically runs `scripts/make_synthetic_data.py`. That creates a labelled demo dataset and
the site shows a “Demo data” banner. To return to the real run:

```bash
python scripts/fetch_completejourney.py
rm data/DATA_SOURCE.txt        # Windows: Remove-Item data\DATA_SOURCE.txt
python scripts/build_notebook.py
python -m nbconvert --to notebook --execute --inplace notebooks/grocery_basket_recommender.ipynb
```

---

## 15. Common questions and troubleshooting

**Why is the support threshold 0.0225 and not 0.005?**
Category-level baskets are dense. `0.005` exhausted memory (~40 GB candidate array), and
`0.01` produced 39,858 rules. The safety net raised support until the rule set was readable.

**Why does Apriori beat FP-Growth here?**
FP-Growth’s theoretical advantage appears on larger, denser databases. At 294 categories and
about 25k baskets, its Python tree overhead costs more than the candidate generation it
saves. Both return identical itemsets, so the comparison is fair.

**Why do rules use categories like “cheeses” instead of product names?**
SKU-level data is too sparse and the labels are unreadable. Categories keep the matrix small
and the rules explainable. This is recorded in `ASSUMPTIONS.md`.

**Why are there duplicate rows in the CSV?**
The CSV has one row per line item. Buying two units of the same category on one receipt
creates two identical rows. The notebook removes exact duplicates because association rules
care about presence, not quantity.

**Why is the site not showing new data?**
Copy the four files into `web/public/data/` and reload. The site fetches JSON at runtime; it
does not read `export/` directly.

**Why does the site say “Demo data”?**
`stats.json` has `"data_source": "synthetic"`, which means `data/DATA_SOURCE.txt` exists.
Delete the marker and re-run with the real CSV to remove the banner.

**The notebook ran out of memory.**
Lower the data size (household sample) or raise the starting support. Do not start at `0.005`
on category-level Complete Journey data.

**A JSON file fails validation.**
Read the validator message. Common causes: a float with more than 4 decimals, an unsorted
list, a rule with `lift <= 1` in `rules.json`, or an item in `items.json` that is missing from
`recommendations.json`.

---

## 16. Glossary

| Term | Meaning |
| --- | --- |
| **Transaction / basket** | the set of items one member bought on one date |
| **Item** | a product category in this project |
| **Itemset** | any set of one or more items |
| **k-itemset** | an itemset with `k` items |
| **Frequent itemset** | an itemset whose support ≥ `min_support` |
| **Support** | fraction of baskets containing the itemset |
| **Support count** | number of baskets containing the itemset |
| **Antecedent** | the “if” side of a rule (`X` in `X → Y`) |
| **Consequent** | the “then” side of a rule (`Y` in `X → Y`) |
| **Confidence** | `P(Y | X)`, how often Y appears when X appears |
| **Lift** | how much more often X and Y co-occur than independence predicts |
| **Apriori principle** | every subset of a frequent itemset is frequent |
| **Candidate generation** | proposing itemsets before counting them |
| **Pruning** | discarding candidates that cannot be frequent |
| **FP-tree** | compressed prefix tree used by FP-Growth |
| **Conditional pattern base** | the sub-database used to mine one item in FP-Growth |
| **One-hot encoding** | boolean matrix with one column per item |
| **Top-N recommendation** | the N highest-ranked items for a user/basket |
| **Cosine similarity** | cosine of the angle between two item vectors |
| **Data contract** | the required shape and rules for a JSON file |
| **Static export** | pre-built HTML/JS/CSS with no server-side runtime |

---

## 17. Limitations and future work

**Limitations**

- **Sampled data:** 500 of 2,469 households. Patterns may not generalize to all shoppers.
- **Category granularity:** rules describe product groups, not individual SKUs.
- **No quantities:** buying one unit or ten counts the same.
- **No time awareness:** a rule learned across 2017 may not hold this week.
- **No ratings or outcomes:** we know what was bought, not whether the shopper liked it.
- **Correlation, not causation:** “bought together” does not mean one product causes the
  other.
- **Recommendation edge case:** two entries for `coupon/misc items` have lift below 1 because
  the item has fewer than five positive follow-ups.

**Future work**

- Time-aware rules (monthly or seasonal models).
- Quantity-weighted support.
- SKU-level rules on a larger sample.
- Hold-out evaluation of the recommender (precision@k, recall@k).
- A lift floor inside `recommend()` so every card is a positive association.
- A larger sample or a database-backed miner for scale.

---

## 18. One-page summary

```
DATA
  Complete Journey (84.51°/Dunnhumby)
  → 500 households, seed 42
  → 289,425 rows, 294 categories, 2017

CLEAN
  missing categories → drop
  exact duplicates → collapse
  text → trim/lower/collapse whitespace
  dates → day-first datetime

BASKETS
  group by member + date
  set of categories
  → 25,431 baskets

ENCODE
  TransactionEncoder
  → 25,431 × 294 boolean matrix

MINE
  Apriori + FP-Growth, same itemsets
  support 0.0225, confidence 0.1
  → 763 itemsets
  → 2,451 rules (2,449 positive)

RANK
  support, confidence, lift
  top rule: cheeses → deli meats
  63.5% confidence, 8.78 lift

RECOMMEND
  item mode: exact antecedent
  basket mode: antecedent ⊆ basket
  rank by lift then confidence

EXPORT
  rules.json (500)
  recommendations.json (67 items)
  items.json (67)
  stats.json (counts, charts, parameters)

VALIDATE
  schema, ranges, ordering, lift > 1, cross-file item set

PUBLISH
  copy to web/public/data
  Next.js static export
  five pages, four charts, light/dark, 375px+
```

That is the complete cycle. Change the data or a threshold, re-run the notebook, validate,
copy the exports, rebuild the site, and the whole system follows.

---

## 19. Site walkthrough and the 10-minute presentation script

This section documents the deployed site at **https://basketwise-ten.vercel.app/** and turns
it into a presentation. It has three jobs:

1. Explain every page, every button, every number and every sentence a visitor can see.
2. Give a slide-by-slide script for the five-slide deck (`BasketWise.pptx`).
3. Give a click-by-click website demo script, timed so the whole talk fits **10:00**.

The site is a static Next.js export. Its pages are `/`, `/recommend/`, `/rules/`,
`/insights/` and `/notebook/`. Every number on screen is read at runtime from one of four
files in `/data`: `stats.json`, `rules.json`, `recommendations.json` and `items.json`.

---

### 19.1 Route map

| Route | Page title | Job | Files it reads | Main controls |
| --- | --- | --- | --- | --- |
| `/` | BasketWise | Explain the project and show one real recommendation | `stats.json`, `rules.json`, `recommendations.json` | 3 navigation-style buttons |
| `/recommend/` | What leaves with it? | Look up one item or build a basket | `recommendations.json`, `rules.json`, `items.json`, `stats.json` | Mode switch, combobox, remove buttons, two empty-state buttons |
| `/rules/` | The rule ledger | Inspect all 500 exported rules | `rules.json` | Search, two range sliders, four sortable headers, reset, previous/next |
| `/insights/` | The shape of the data | Show the data and algorithm evidence | `stats.json` | Chart hover tooltips |
| `/notebook/` | The notebook is the method | Explain the method in prose | `stats.json`, `rules.json`, `recommendations.json`, `items.json` | In-page anchor links, GitHub button |

All routes use a trailing slash. That is deliberate: `next.config.ts` sets
`trailingSlash: true` and `output: "export"`, so the same files work on Vercel, Netlify,
GitHub Pages or a plain static server.

---

### 19.2 What appears on every page

These elements are shared by all five routes.

#### The skip link

The first focusable element is **“Skip to content”**. It is visually hidden until a keyboard
user presses Tab, then it jumps to `<main id="main">`. It exists so the navigation is not
repeated on every tab press.

#### The header

| Element | Exact text / label | Action |
| --- | --- | --- |
| Wordmark | `BasketWise` + small `CSE 426` | Goes to `/` |
| Nav link | `Recommender` | Goes to `/recommend/` |
| Nav link | `Rules` | Goes to `/rules/` |
| Nav link | `Insights` | Goes to `/insights/` |
| Nav link | `Notebook` | Goes to `/notebook/` |
| Theme button | aria-label `Switch to dark mode` when light, `Switch to light mode` when dark; tooltip `Dark mode` / `Light mode` | Flips the palette |
| Active link | `aria-current="page"` | Screen-reader state only; the visual state is a colour change |

The wordmark is the project name plus the course code. The nav is the whole site: there are
only five pages, so there is no dropdown, search bar or hamburger menu.

**Theme behaviour.** The first visit follows the operating system
(`prefers-color-scheme`). A click stores the choice in `localStorage` under
`basketwise-mode`, so it survives a reload. If storage is blocked, the switch still works
for the session. The icon is a moon in light mode and a sun in dark mode.

#### The demo banner

`DataBanner` reads `stats.json`. If `data_source` is `"synthetic"` it shows:

> **Demo data.** This site is showing the synthetic stand-in, not the Complete Journey
> sample. [How to run the real data]

The link goes to `/notebook#data-source`. With the current real run, the banner is absent.
This is the fastest way to prove the site is showing real data.

#### The footer

| Block | Exact copy | Meaning |
| --- | --- | --- |
| Wordmark | `BasketWise` | Project name |
| Note | “A CSE 426 Data Mining and Warehouse Lab project by Md. Shahriar Hossain Srabon. The notebook mines the baskets; this site reads what it exported.” | Authorship and the division of labour |
| Pages | `Recommender`, `Rule explorer`, `Insights`, `Methodology` | Same four routes, different labels |
| Project | `Notebook on GitHub`, `Source repository`, `Complete Journey (84.51°)` | Notebook, repo, data citation |
| Bottom | “Built with Next.js. Data is read from four JSON files in `public/data`.” | Confirms the static architecture |

Note the deliberate label difference: the nav says **Rules**, the footer says **Rule
explorer**; the nav says **Notebook**, the footer says **Methodology**. Both point to the
same page.

#### The three data states

Every page that fetches JSON can show three non-content states:

| State | What the user sees | When |
| --- | --- | --- |
| Loading | A heading such as “Reading the exported rules”, “Reading the statistics export”, “Reading the recommendation tables” or “Reading the notebook's exports”, plus “Reading the exported JSON. This only takes a moment.” and three skeleton lines | First paint before the fetch resolves |
| Error | “The data did not load.” + the actual fetch error + a **Try again** button | Missing file, network failure or non-200 response |
| Empty | Page-specific: “No recommendations for this item”, “Start with a staple”, “No rule covers this basket”, “No rule survives these filters” | The query is valid but matches nothing |

No page is allowed to render a silent blank. That is a deliberate contract in
`web/src/lib/useJson.ts`.

---

### 19.3 Home page — `/`

The home page is a single scrolling argument: what the project is, what the data is, how the
pipeline works, what the strongest rule is, and where to click next.

#### 19.3.1 Hero

| Element | Exact text | What it means |
| --- | --- | --- |
| Heading | `BasketWise` | Project name |
| Lead | “Grocery baskets, mined for what sells together.” | The one-line product statement |
| Primary button | `Find a recommendation` | Goes to `/recommend/` |
| Secondary button | `Read the notebook` | Goes to `/notebook/` |

`Find a recommendation` is the green primary button; `Read the notebook` is the outlined
secondary. They are the two intended paths: use the product, or inspect the method.

#### 19.3.2 The recommendation slip

This is the most important element on the page. It is a paper-like card that reads the first
entry of `recommendations.json["cheeses"]`.

| Line | Exact text | Source |
| --- | --- | --- |
| Label | `Recommendation slip` | Static |
| Figure | `lift 8.78` | `recommendations.json` |
| In the basket | `cheeses` | The lookup key |
| Also bought | `deli meats` | First recommendation |
| Explanation | “63.5% of baskets with cheeses also had deli meats.” | `confidence = 0.6349` |
| Footer left | `Sample from recommendations.json` | Provenance |
| Footer right | `confidence 63.5%` | Same confidence, repeated as a figure |

**Why this card matters.** It is not a screenshot or a hard-coded example. It is the same
data the recommender uses, rendered in a receipt idiom. If `cheeses` disappeared from the
file, the component would fall back to the first available item; if the file failed, it
would show “The recommendation file is not available yet.” and an **Open the recommender**
button. While the fetch is in flight it shows the label “Reading the recommendation sheet”
and three skeleton lines, so the card never collapses.

#### 19.3.3 Dataset figures band

Four large numbers, each with a label:

| Label | Value | Source |
| --- | --- | --- |
| `Baskets` | **25,431** | `stats.total_transactions` |
| `Items in the data` | **294** | `stats.total_items` |
| `Members` | **500** | `stats.total_members` |
| `Exported rules` | **500** | `rules.length` |

“Items in the data” means product categories, not SKUs. “Exported rules” is the length of
the JSON array, not the 2,451 rules the notebook generated. Both distinctions are worth
saying out loud in a presentation.

While loading, each value is an ellipsis (`…`), not a zero. That avoids the false impression
that the dataset is empty.

#### 19.3.4 “From receipt to rule”

| Element | Exact text |
| --- | --- |
| Heading | `From receipt to rule` |
| Lead | “Six steps, one reproducible notebook, four JSON files the site can read.” |

The six steps:

| # | Title | Description |
| --- | --- | --- |
| 01 | `Raw data` | “One line per purchase: member, date, item.” |
| 02 | `Cleaning` | “Hidden missing values, duplicates and name variants removed.” |
| 03 | `Baskets` | “One member and one date become one transaction.” |
| 04 | `Apriori and FP-Growth` | “Both algorithms mine the same support threshold.” |
| 05 | `Rules` | “Support, confidence and lift rank every combination.” |
| 06 | `Recommender` | “The site reads the exported rules, never the raw CSV.” |

This is the same pipeline as section 5 of the guide, compressed to six readable steps. Step
06 is the architectural claim: the browser is a reader, not a miner.

#### 19.3.5 The statement band

A large editorial sentence, generated from `rules[0]`:

> “deli meats appears in 63.5% of the baskets that hold cheeses.”

Under it, in smaller type:

> “Strongest rule by lift, from the 500 exported rules. Lift **8.78**.”

This is the plain-English version of the top rule. The sentence is built by
`ruleSide(strongest.consequents)` + `formatPercent(strongest.confidence)` +
`ruleSide(strongest.antecedents)`, so it stays correct if the data changes. The meta line
names the ranking basis (lift) and the size of the exported ledger (500).

#### 19.3.6 “The notebook is the source.”

| Element | Exact text |
| --- | --- |
| Heading | `The notebook is the source.` |
| Lead | “The website holds no mining code. It reads the four files the notebook writes.” |
| Button | `Read the methodology` → `/notebook/` |

Beside it are four numbered method rows:

| # | Title | Description |
| --- | --- | --- |
| 01 | `Preprocess` | “Missing values, duplicates, names and day-first dates.” |
| 02 | `Build baskets` | “One member on one date, one-hot encoded for mining.” |
| 03 | `Mine and rank` | “Apriori and FP-Growth, timed, then ranked by lift.” |
| 04 | `Export` | “Rules, recommendations, items and statistics as JSON.” |

This block is the answer to “is the website doing the data mining?” It is not. The notebook
is the source of truth; the site is a presentation layer.

#### 19.3.7 Closing band

| Element | Exact text | Action |
| --- | --- | --- |
| Heading | `Pick an item. See what leaves with it.` | — |
| Button | `Open the recommender` | Goes to `/recommend/` |

The last button repeats the primary call to action. The home page therefore has two visible
routes into the recommender (`Find a recommendation` and this closing button), plus the
`Open the recommender` fallback that only appears if the recommendation file fails. It also
has two routes into the notebook (`Read the notebook` and `Read the methodology`).

---

### 19.4 Recommender page — `/recommend/`

This is the interactive product page. It has two modes that answer two different questions.

#### 19.4.1 Page head

| Element | Exact text |
| --- | --- |
| Heading | `What leaves with it?` |
| Lead | “Pick one product or build a small basket. Every card is a mined rule.” |

#### 19.4.2 Left panel

| Element | Exact text |
| --- | --- |
| Heading | `Build the basket` |
| Description | “Look up one product, or assemble a small basket and let every matching rule vote.” |
| Mode button 1 | `One item` |
| Mode button 2 | `Basket` |
| Persistent note | “Ranked by lift, then confidence. Items already in the basket are never recommended back.” |

The two mode buttons form a segmented control. The active one is indicated by
`aria-pressed` and a filled style. Switching modes keeps the item selection and the basket
contents, so a presenter can move back and forth without retyping.

#### 19.4.3 Item mode

The default state is **One item** with `cheeses` already selected. This is why the page is
never empty on first load.

| Element | Exact text / behaviour |
| --- | --- |
| Label | `Find an item` |
| Placeholder | `cheeses, pasta sauce, milk…` |
| Input role | `combobox`, `aria-autocomplete="list"` |
| Suggestions | Up to 8 items, prefix matches first, then alphabetical |
| Keyboard | ↑ / ↓ move, Enter selects, Escape closes, Tab closes |
| Helper, exact match | “cheeses is selected. Type to choose another item.” |
| Helper, partial query | “N matches shown. Use the arrow keys and Enter.” |
| Helper, empty input | “67 items have recommendations. Use the arrow keys and Enter.” |
| No match | “No item matches “xyz”.” |

The helper text is live. It tells the user how many options exist, how many match, and
whether the typed word is an exact selection. This is a small accessibility detail that
matters in a demo: the presenter never has to guess whether the input accepted the word.

**Result header**

| Element | Exact text |
| --- | --- |
| Heading | `Bought with cheeses` |
| Sub-line | `3 recommendations from recommendations.json` |
| Empty sub-line | `No rule reaches this item` |

**Result cards.** Each card shows the recommended item, a plain-English reason, a
confidence bar, the confidence as a percentage, and the lift as a number.

For `cheeses`, the three cards are:

| Rank | Item | Reason sentence | Confidence | Lift |
| --- | --- | --- | --- | --- |
| 1 | `deli meats` | “63.5% of baskets with cheeses also had deli meats.” | 63.5% | 8.78 |
| 2 | `baked bread/buns/rolls` | “62.9% of baskets with cheeses also had baked bread/buns/rolls.” | 62.9% | 2.36 |
| 3 | `fluid milk products` | “60.4% of baskets with cheeses also had fluid milk products.” | 60.4% | 2.02 |

The visual bar is driven by confidence, not lift. That is why the second card can look
almost as long as the first while its lift is less than a third. The number labels are what
separate reliability from association strength.

**Empty state.** If an item has no rules, the page shows:

- Heading: `No recommendations for this item`
- Body: “This product never clears the support threshold in an antecedent, so the mined
  rules cannot say what leaves with it. Try a more common item.”
- Button: `Try cheeses` (sets the selection back to `cheeses`)

**Footnote.** Below the results:

> “Data source: `recommendations.json` for one item, `rules.json` for a basket. Minimum
> confidence in the export is 10.0% and minimum support is 2.25%.”
>
> “Strongest rule currently exported: cheeses → deli meats at 63.5% confidence.”

The values are read from `stats.parameters`, so they cannot drift from the export.

#### 19.4.4 Basket mode

| Element | Exact text / behaviour |
| --- | --- |
| Label | `Add an item to the basket` |
| Placeholder | `cheeses, pasta sauce, milk…`; becomes `Basket is full` at 6 items |
| Selection | Clicking a suggestion adds it and clears the input |
| Basket cap | 6 items (`MAX_BASKET = 6`) |
| Empty note | “Add up to 6 items. A recommendation only fires when a rule’s whole antecedent is in the basket.” |
| Selected list | One row per item with a `Remove` button; aria-label “Remove {item} from the basket” |
| Result heading | `What to add next` |
| Empty sub-line | `An empty basket has nothing to match` |
| Filled sub-line | `2 items in the basket · 5 matches` |

**Empty basket state**

- Heading: `Start with a staple`
- Body: “Cheeses, pasta sauce and fluid milk sit at the top of the data; small baskets around
  them match the most rules.”
- Button: `Try dry noodles and beef` (sets the basket to
  `["dry noodles/pasta", "beef"]`)

This shortcut exists so a demo or a first-time visitor can see a multi-item result in one
click.

**No-match state**

- Heading: `No rule covers this basket`
- Body: “The rules need every antecedent item present. Remove one and try a more common
  combination, or start from cheeses.”
- Button: `Clear the basket`

**Result cards in basket mode.** The reason sentence changes to avoid claiming that a
multi-item antecedent is one product:

> “{confidence}% of baskets with this combination also had {item}.”

For the canonical demo basket `dry noodles/pasta + beef`, the five results are:

| Rank | Item | Confidence | Lift |
| --- | --- | --- | --- |
| 1 | `pasta sauce` | 44.7% | 8.75 |
| 2 | `vegetables - shelf stable` | 42.2% | 3.97 |
| 3 | `baked bread/buns/rolls` | 14.1% | 3.56 |
| 4 | `fluid milk products` | 14.1% | 3.56 |
| 5 | `bag snacks` | 13.9% | 3.55 |

The reason text is generated, not stored. `RecommendationList` picks the basket sentence
when `basketMode` is true and the item sentence otherwise.

#### 19.4.5 What the browser actually does

`recommendForBasket(rules, basket, topN)` in `web/src/lib/data.ts`:

1. keeps every rule whose **entire antecedent** is inside the basket;
2. drops any consequent already in the basket;
3. keeps the best entry per consequent (highest lift, then confidence);
4. sorts by lift, then confidence;
5. returns the top five.

This is a filter over the 500 exported rules. It is **not** Apriori, FP-Growth, or any new
mining. If the basket is rare enough that no exported rule covers it, the page says so
instead of inventing a recommendation.

---

### 19.5 Rules page — `/rules/`

The rules page is the evidence ledger. It exposes the 500 exported rules so a reader can
audit any recommendation.

#### 19.5.1 Page head

| Element | Exact text |
| --- | --- |
| Heading | `The rule ledger` |
| Lead | “Every exported rule with the numbers that judge it. Sort a column or filter the list.” |

#### 19.5.2 Controls

| Control | Type | Range / default | Effect |
| --- | --- | --- | --- |
| `Filter by item` | Search input | empty | Substring match on either side of the rule; case-insensitive |
| Helper | Static text | — | “Matches either side of the rule. Case does not matter.” |
| `Minimum confidence` | Range slider | 10–100, step 5, default 10 | Hides rules below the chosen confidence |
| `Minimum lift` | Range slider | 1–9, step 0.5, default 1 | Hides rules below the chosen lift |
| `Reset filters` | Button | — | Restores query `""`, confidence 10, lift 1, sort lift descending, page 1 |
| `Rule` / `Support` / `Confidence` / `Lift` | Sortable column headers | default lift ↓ | First click sorts; second click reverses |
| `Previous` / `Next` | Pagination buttons | 20 rows per page | Move one page; disabled at the ends |

The lift slider maximum is computed from the data: `Math.ceil(max lift)` = `ceil(8.7796)` =
**9**. It is not hard-coded, so a new export with a stronger rule would widen the slider
automatically.

#### 19.5.3 Summary line

Above the table, a live region announces:

> “**500** of 500 rules match. Sorted by lift, descending. Page 1 of 25.”

After typing `cheeses`:

> “**5** of 500 rules match. Sorted by lift, descending. Page 1 of 1.”

After raising minimum lift to 8.5 while `cheeses` is still in the search box:

> “**2** of 500 rules match. Sorted by lift, descending. Page 1 of 1.”

This line is the fastest way to show that filters are applied to the whole file, not just the
visible page.

#### 19.5.4 Table

Columns: `Rule`, `Support`, `Confidence`, `Lift`.

| Column | Format | Example from row 1 |
| --- | --- | --- |
| Rule | antecedent → consequent, with a literal arrow | `cheeses` → `deli meats` |
| Support | one decimal percent | `2.9%` |
| Confidence | one decimal percent | `63.5%` |
| Lift | two decimals | `8.78` |

The active sort column shows `↓` or `↑`; inactive columns show a middle dot `·`. The header
is a real `<button>` inside `<th>`, and `aria-sort` is set, so the control is keyboard and
screen-reader accessible.

At the default settings the first five rows are:

| Rule | Support | Confidence | Lift |
| --- | --- | --- | --- |
| `cheeses` → `deli meats` | 2.9% | 63.5% | 8.78 |
| `deli meats` → `cheeses` | 2.9% | 40.2% | 8.78 |
| `pasta sauce` → `dry noodles/pasta` | 2.7% | 52.7% | 8.75 |
| `dry noodles/pasta` → `pasta sauce` | 2.7% | 44.7% | 8.75 |
| `fluid milk products + vegetables - shelf stable` → `baked bread/buns/rolls + beef` | 2.4% | 40.5% | 4.68 |

Notice the symmetry: support and lift are identical in both directions of a pair, while
confidence is not. `cheeses → deli meats` is 63.5%, but `deli meats → cheeses` is 40.2%.
That is the clearest one-screen demonstration of the metric definitions.

#### 19.5.5 Empty state

If no rule survives:

> “No rule survives these filters. Lower the minimum confidence or lift, or clear the item
> filter.”

The table is replaced, but the pagination line still reads `Showing 0 to 0 of 0`.

#### 19.5.6 Pagination

| Text | Meaning |
| --- | --- |
| `Showing 1 to 20 of 500` | First page, 20 rows visible, 500 rows after filtering |
| `Page 1 of 25` | 500 ÷ 20 = 25 pages |
| `Previous` disabled on page 1 | No earlier page |
| `Next` disabled on page 25 | No later page |

The page number resets to 1 whenever a filter or sort changes, so the user never lands on a
page that no longer exists.

#### 19.5.7 “Reading the columns”

Below the table:

> “**Support** is the share of all baskets containing the whole rule. **Confidence** is the
> share of baskets with the antecedent that also contain the consequent. **Lift** compares
> that confidence with the consequent's normal popularity: 1 means no association, above 1
> means the two items appear together more often than chance.”

This is the plain-language metric definition. It is the sentence to point at if a reviewer
asks what lift means.

---

### 19.6 Insights page — `/insights/`

This page shows what the rules rest on. It is descriptive analytics, not a second model.

#### 19.6.1 Page head

| Element | Exact text |
| --- | --- |
| Heading | `The shape of the data` |
| Lead | “Four figures from the recommender's export, showing what the rules rest on.” |

#### 19.6.2 Figure row

| Label | Value | Source |
| --- | --- | --- |
| `Transactions` | **25,431** | `stats.total_transactions` |
| `Distinct items` | **294** | `stats.total_items` |
| `Minimum support` | **2.25%** | `stats.parameters.min_support` |
| `Minimum confidence` | **10%** | `stats.parameters.min_confidence` |

The support value is shown to two decimals because `0.0225 × 100 = 2.25`. The confidence
value is shown to zero decimals because it is exactly `0.1`.

#### 19.6.3 Chart 1 — “What the baskets are built on”

| Element | Copy |
| --- | --- |
| Heading | `What the baskets are built on` |
| Lead | “The fifteen most purchased items. A long head of staples makes them easy to recommend and easy to support.” |
| Chart | Horizontal bars, one per item, count on the x-axis |
| Tooltip | Item name + `N purchase lines` |
| Caption | “Counts are purchase lines after cleaning, from stats.json.” |

The top five bars are `soft drinks` (7,753), `fluid milk products` (7,622),
`baked bread/buns/rolls` (6,763), `cheese` (5,514) and `bag snacks` (4,673). Note the
distinction between `cheese` (5,514 lines, a top seller) and `cheeses` (1,164 baskets, the
antecedent of the strongest rule). They are different category labels in the source data.
Do not conflate them on stage.

#### 19.6.4 Chart 2 — “A year of shopping”

| Element | Copy |
| --- | --- |
| Heading | `A year of shopping` |
| Lead | “Purchase lines per month. The series is steady rather than seasonal, which is one reason the rules ignore time.” |
| Chart | Line, x = month, y = purchase lines |
| X-axis labels | Shortened from `2017-01` to `17-01`; every fourth label is shown |
| Tooltip | Month + `N purchase lines` |
| Caption | “Axis labels shorten 2017-01 to 17-01. Every month from January 2017 to January 2018 is present.” |

The counts sit between roughly 16,258 and 18,585 per month. The last point, January 2018,
is only 88 because the sample ends on 1 January. If asked, say the final point is a partial
month, not a collapse in demand.

#### 19.6.5 Chart 3 — “How big is a basket?”

| Element | Copy |
| --- | --- |
| Heading | `How big is a basket?` |
| Lead | “Most trips carry one to five distinct categories. Baskets are counted once and repeated items collapse into a set.” |
| Chart | Vertical bars, x = basket size, y = number of baskets |
| Tooltip | “N items” + `N baskets` |
| Caption | “The chart shows baskets up to 20 categories. Longer visits exist (the longest is 73) but hold only a handful of baskets each.” |

The distribution peaks at size 1 (3,923 baskets) and falls steadily: 3,182 at size 2, 2,584
at size 3, 2,081 at size 4, 1,598 at size 5. The mean is 8.25 and the median is 5. The long
tail is real but thin, so the chart is clipped at 20 for readability while `stats.json`
keeps every size up to 73.

#### 19.6.6 Chart 4 — “Two algorithms, one answer”

| Element | Copy |
| --- | --- |
| Heading | `Two algorithms, one answer` |
| Lead | “Apriori and FP-Growth returned identical itemsets. On 294 categories, Apriori's simpler counting won on time.” |
| Chart | Horizontal bars, seconds on the x-axis, Apriori green and FP-Growth muted |
| Tooltip | Algorithm + `N seconds` |
| Caption | “763 itemsets each. Apriori 2.04 s, FP-Growth 24.57 s. Results are identical.” |

This is the honest result. The textbook expectation is that FP-Growth wins on large data;
here the data is moderate (294 columns, ~25k rows), and Python's FP-tree construction costs
more than Apriori's counting. The identical item count is the correctness check.

#### 19.6.7 Interaction note

All four charts are Recharts SVGs. Hovering a bar or point opens a small tooltip; there is no
zoom, filter or drill-down. The page is explanatory, not exploratory. On a projector, the
tooltips are a nice touch but not required for the script.

---

### 19.7 Notebook page — `/notebook/`

This is the written methodology: the same story as the notebook, without the plots.

#### 19.7.1 Page head

| Element | Exact text |
| --- | --- |
| Heading | `The notebook is the method` |
| Lead | “Cleaning, thresholds, one worked rule and the four exports. The notebook remains the source.” |

#### 19.7.2 Left sidebar

> “The executed notebook is the deliverable. This page is the short version for a reader who
> wants the method without the plots.”

Below it is an in-page table of contents with nine anchor links:

| Link label | Anchor |
| --- | --- |
| `Notebook and site` | `#division` |
| `Cleaning` | `#cleaning` |
| `Baskets and thresholds` | `#baskets` |
| `A worked rule` | `#worked-example` |
| `Apriori and FP-Growth` | `#algorithms` |
| `The four exports` | `#exports` |
| `Real or demo data` | `#data-source` |
| `Limits and next steps` | `#limits` |
| `Run it yourself` | `#run` |

These are plain `<a href="#...">` links, so they work with JavaScript disabled and update the
URL hash.

#### 19.7.3 Section: “One pipeline, two roles”

> “`grocery_basket_recommender.ipynb` is where every decision is made: reading the CSV,
> cleaning it, building baskets, running Apriori and FP-Growth, generating rules and ranking
> recommendations. It writes four JSON files.”
>
> “This site performs no mining. Each page fetches those files from `/data` in the browser
> and renders them. Re-run the notebook, copy the exports, and the site follows.”

This is the division of responsibility in two sentences.

#### 19.7.4 Section: “Cleaning before counting”

The page lists four cleaning actions:

1. Read `?`, `n/a`, `missing`, `--`, `NULL` and empty strings as missing, then drop rows with
   no member, date or item.
2. Remove exact duplicate rows, but keep genuine repeat purchases.
3. Trim, lowercase and collapse whitespace in item names so near-duplicates do not split the
   counts.
4. Parse dates day-first, then add `Year` and `Month`.

It then prints the live counts: **25,431 baskets**, **294 items**, **500 members**, from
**2017-01-01** to **2018-01-01**.

#### 19.7.5 Section: “One member, one date, one basket”

Key sentences:

> “A basket is everything the same member bought on the same date. Repeated lines of one
> product collapse into a single item, because buying two loaves is not a new association.”

> “Support and confidence are the two filters. The notebook starts at support `0.01` and
> confidence `0.1`; if the rule set is empty or larger than 5,000 rows, a safety loop moves
> support until it is readable. This run settled at **2.3%** support and **10.0%**
> confidence. Both values are written to `stats.json`, and the tuning table is in the
> notebook.”

This is the one place where the same threshold is formatted differently: the notebook page
uses `formatPercent()` (one decimal), so `0.0225` renders as **2.3%**. The Insights page and
the recommender footnote use `toFixed(2)`, so the same value renders as **2.25%**. The value
is identical; only the display precision differs.

This is the place to explain why the threshold is not the PRD's `0.005`: dense category data
ran out of memory, and `0.01` produced 39,858 rules. The safety loop is the answer.

#### 19.7.6 Section: “A worked rule”

The block is filled from `rules[0]`:

| Line | Exact rendered content |
| --- | --- |
| Rule | `cheeses → deli meats` |
| Support | **2.9%** support: about **740** of the 25,431 baskets contain both sides. |
| Confidence | **63.5%** confidence: when the basket has cheeses, it also has deli meats about 63.5% of the time. |
| Lift | **8.78** lift. The pair appears 8.78 times more often than independent popularity would predict. This is the strongest rule in the export, sorted by lift. |

The page computes the basket count as `round(support × total_transactions)`. Because
`support` is already rounded to `0.0291`, the page shows **740**. The exact count is **739**
(`739 / 25,431 = 0.02906`, and `739 / 1,164 = 0.6349` matches the exported confidence). The
one-basket difference is a display artefact of multiplying a rounded value; sections 5 and 11
of this guide use the exact count.

After the box:

> “Support answers ‘how common is this?’, confidence answers ‘how reliable is the guess?’,
> and lift answers ‘is it better than guessing the consequent anyway?’. A rule can have high
> confidence and almost no lift when the consequent is a staple that appears in most
> baskets, which is why the site never ranks on confidence alone.”

That last sentence is the conceptual heart of the project. It also explains the second
recommendation card, where confidence is high but lift is only 2.36.

#### 19.7.7 Section: “Apriori and FP-Growth”

> “Both algorithms mined the same support threshold and returned the same **763** frequent
> itemsets. Apriori builds candidate sets and counts them; FP-Growth compresses baskets into
> an FP-tree and avoids candidate generation.”

The table:

| Algorithm | Itemsets | Runtime |
| --- | --- | --- |
| Apriori | 763 | 2.04 s |
| FP-Growth | 763 | 24.57 s |

> “FP-Growth was slower here, not faster. With only 294 category columns and about 25,000
> baskets, Apriori's counting is cheaper than building and walking the tree in Python. The
> textbook advantage needs larger, denser data; the measured numbers are reported as they
> came out.”

#### 19.7.8 Section: “The four exports”

> “Every file is UTF-8 JSON, every float is rounded to four decimals, and sets become sorted
> lists so the output is stable between runs.”

| File | Contents | Rows |
| --- | --- | --- |
| `rules.json` | The strongest rules by lift, capped at 500, with each item's best five item-to-item rules guaranteed. | 500 |
| `recommendations.json` | Each item mapped to five items that follow it, using rules whose antecedent is that item alone, by lift then confidence. | 67 |
| `items.json` | Items that have recommendations, ordered by purchase count. | 67 |
| `stats.json` | Headline counts, chart series, parameters, algorithm comparison and the data-source flag. | 1 |

> “`scripts/validate_exports.py` checks all four files against the contract: keys, rounding,
> ordering, probabilities, and that items and recommendations describe the same item set. It
> exits non-zero on any mismatch.”

Note the “Rows” column for `recommendations.json` is the number of **items**, not the number
of recommendation entries (285).

#### 19.7.9 Section: “Real or demo data”

> “The notebook prefers `data/Groceries_dataset.csv`, a product-category extract of the
> Complete Journey study (84.51° / Dunnhumby) built by
> `scripts/fetch_completejourney.py`. If that file is absent,
> `scripts/make_synthetic_data.py` builds a seeded stand-in with realistic popularity,
> basket sizes and planted co-purchases, and writes `data/DATA_SOURCE.txt`.”
>
> “While that marker exists, the run is labelled **synthetic** in `stats.json` and the site
> shows the demo banner; without it, the label is **real**. To switch: replace the CSV,
> delete the marker, re-run the notebook, copy the four files into `web/public/data/`.
> Nothing in the site needs editing.”

The bold label is dynamic: it reads `stats.data_source` and prints `synthetic` or `real`. In
the current run it says **real**, and the banner is absent.

#### 19.7.10 Section: “Limits and next steps”

The four limits:

1. **No ratings or quantities** — the data records that an item was bought, not how much it
   was liked.
2. **No time awareness** — a rule learned across one year may not hold this week.
3. **Sampled and coarse** — 500 households and product categories, not individual SKUs, so
   rare products never reach the support threshold. That is why only **67** items have
   recommendations.
4. **Association is not causation** — “bought together” does not mean one product causes the
   other.

> “Natural extensions are time-aware rules, quantity weighting, category-level
> generalisation, and a hold-out evaluation of the recommender instead of ranking by lift
> alone.”

#### 19.7.11 Section: “Run it yourself”

```bash
pip install -r requirements.txt
python scripts/build_notebook.py
python -m nbconvert --to notebook --execute --inplace notebooks/grocery_basket_recommender.ipynb
python scripts/validate_exports.py
```

> “The executed notebook is committed with its outputs and plots, so it can be read without
> running anything. Open it on GitHub or in Jupyter.”

Button: **Open the notebook on GitHub** → the repository's `notebooks/` folder (new tab).

---

### 19.8 Every button and control, in one table

| Page | Control | Element | Exact label / aria | What it does | Demo use |
| --- | --- | --- | --- | --- | --- |
| All | Skip link | `<a href="#main">` | `Skip to content` | Jumps focus to main content | Not used on stage |
| All | Wordmark | Link | `BasketWise CSE 426` | Goes home | — |
| All | Nav × 4 | Links | `Recommender`, `Rules`, `Insights`, `Notebook` | Route change | Primary navigation |
| All | Theme toggle | Button | `Switch to dark mode` / `Switch to light mode` | Toggles palette, saves choice | Optional 5 s flourish |
| All | Footer pages × 4 | Links | `Recommender`, `Rule explorer`, `Insights`, `Methodology` | Same routes | — |
| All | Footer project × 3 | External links | `Notebook on GitHub`, `Source repository`, `Complete Journey (84.51°)` | New tab | Credibility |
| All | Retry | Button in error state | `Try again` | Refetches the JSON | Fallback only |
| Home | Primary CTA | Link | `Find a recommendation` | `/recommend/` | Opens the demo |
| Home | Secondary CTA | Link | `Read the notebook` | `/notebook/` | Optional |
| Home | Slip fallback | Link | `Open the recommender` | `/recommend/` | Only if recs fail |
| Home | Method CTA | Link | `Read the methodology` | `/notebook/` | Optional |
| Home | Close CTA | Link | `Open the recommender` | `/recommend/` | Alternate entry |
| Recommender | Mode | Button | `One item` | Switches to item lookup | Start here |
| Recommender | Mode | Button | `Basket` | Switches to basket matching | Second beat |
| Recommender | Combobox | Input | `Find an item` | Type + select an item | Type `cheeses` |
| Recommender | Combobox | Input | `Add an item to the basket` | Adds selection, clears input | Add two items |
| Recommender | Remove | Button per item | `Remove {item} from the basket` | Deletes that item | Optional |
| Recommender | Empty action | Button | `Try cheeses` | Resets item selection | Fallback |
| Recommender | Empty action | Button | `Try dry noodles and beef` | Seeds the canonical basket | One-click demo |
| Recommender | Empty action | Button | `Clear the basket` | Empties the basket | Reset |
| Rules | Search | Input | `Filter by item` | Substring filter, case-insensitive | Type `cheeses` |
| Rules | Confidence | Range | `Minimum confidence`, 10–100 step 5 | Filters by confidence | Optional |
| Rules | Lift | Range | `Minimum lift`, 1–9 step 0.5 | Filters by lift | Drag to 8.5 |
| Rules | Reset | Button | `Reset filters` | Restores defaults | Reset before leaving |
| Rules | Sort × 4 | Header buttons | `Rule`, `Support`, `Confidence`, `Lift` | Sort asc/desc | Optional |
| Rules | Page back | Button | `Previous` | Previous 20 rows | Optional |
| Rules | Page forward | Button | `Next` | Next 20 rows | Optional |
| Insights | Charts × 4 | SVG hover | Tooltips | Show exact values | Hover one bar |
| Notebook | TOC × 9 | Anchor links | Section names | Jump within the page | Optional |
| Notebook | GitHub | Link | `Open the notebook on GitHub` | Opens the notebook | Closing proof |

There are no other buttons. There is no login, no cart, no checkout, no settings page and no
search across the whole site.

---

### 19.9 Every number on the site and where it comes from

Use this table to answer “where does that number come from?” without opening the code.

| Number | Where it appears | Source field |
| --- | --- | --- |
| **25,431** | Home “Baskets”; Insights “Transactions”; Notebook prose | `stats.total_transactions` |
| **294** | Home “Items in the data”; Insights “Distinct items”; Notebook prose | `stats.total_items` |
| **500** | Home “Members”; Notebook prose | `stats.total_members` |
| **500** | Home “Exported rules”; Rules total; rules summary | `rules.length` |
| **67** | Recommender helper “67 items have recommendations”; Notebook tables and limits | `recommendations.json` keys / `items.length` |
| **3** | item-mode sub-line for `cheeses` | `recommendations.json["cheeses"].length` |
| **2.25% / 2.3%** | Insights “Minimum support”; recommender footnote show 2.25%; notebook shows 2.3% | `stats.parameters.min_support` |
| **10% / 10.0%** | Insights “Minimum confidence”; recommender footnote | `stats.parameters.min_confidence` |
| **63.5%** | Home slip and statement; recommender card; rules row; notebook worked rule | `rules[0].confidence` |
| **8.78** | Home slip and statement meta; recommender card; rules row; notebook | `rules[0].lift` |
| **2.9%** | Rules support column; notebook worked rule | `rules[0].support = 0.0291`, displayed to one decimal |
| **739 / 740** | Notebook “about 740 of the 25,431 baskets” | True count is 739; the page renders 740 by multiplying the rounded `support × total_transactions` |
| **2.36** | Recommender second card for `cheeses` | `recommendations.json` |
| **2.02** | Recommender third card for `cheeses` | `recommendations.json` |
| **44.7%** | Basket-mode top card for pasta sauce | matching rule confidence |
| **8.75** | Basket-mode top card lift | matching rule lift |
| **763** | Insights chart 4; Notebook algorithm section | `stats.algorithm_comparison.*.itemsets` |
| **2.04 s** | Insights chart 4; Notebook table | `stats.algorithm_comparison.apriori.runtime_sec` |
| **24.57 s** | Insights chart 4; Notebook table | `stats.algorithm_comparison.fpgrowth.runtime_sec` |
| **3,923** | Insights basket-size chart, size 1 | `stats.basket_size_distribution` |
| **73** | Insights basket-size caption | max size in `stats.basket_size_distribution` |
| **7,753** | Insights top-items chart, first bar | `stats.top_items[0]` |
| **1** (rows) | Notebook exports table, `stats.json` | Static fact |
| **25** (pages) | Rules summary “Page 1 of 25” | `ceil(500 / 20)` |

No page formats a raw float directly. `formatPercent` multiplies by 100 and fixes one
decimal; `formatLift` fixes two; `formatSeconds` fixes two and appends `s`; `formatInteger`
adds thousands separators.

---

### 19.10 The 10-minute presentation script

#### 19.10.1 Timing budget

| Clock | Segment | Length |
| --- | --- | --- |
| 0:00–0:45 | Slide 1 — Title and hook | 0:45 |
| 0:45–1:40 | Slide 2 — Real baskets, real signal | 0:55 |
| 1:40–2:35 | Slide 3 — One pipeline, one source of truth | 0:55 |
| 2:35–3:45 | Slide 4 — What the baskets revealed | 1:10 |
| 3:45–4:30 | Slide 5 — From notebook to live product | 0:45 |
| 4:30–5:15 | Demo — Home | 0:45 |
| 5:15–6:15 | Demo — Recommender, one item | 1:00 |
| 6:15–7:05 | Demo — Recommender, basket | 0:50 |
| 7:05–7:55 | Demo — Rules | 0:50 |
| 7:55–8:35 | Demo — Insights | 0:40 |
| 8:35–9:00 | Demo — Notebook | 0:25 |
| 9:00–9:30 | Close and thank you | 0:30 |
| 9:30–10:00 | Buffer for clicks, laughter, a slow load | 0:30 |

The spoken text below is about 1,270 words. At a measured 135–140 words per minute it runs
9:00–9:25; the clicks and natural pauses bring it to about 9:30, leaving the last 30 seconds
as buffer. Do not rush the numbers; the pauses are what make them land.

#### 19.10.2 Before you start

1. Open **https://basketwise-ten.vercel.app/** in a browser window, not a tab you will
   accidentally close.
2. Use **light mode**, 100% zoom, full screen. The dark palette is attractive but projects
   worse in a bright room.
3. Open the deck in presenter view on the other display.
4. Pre-load the recommender page once, then go back to home, so the JSON is warm in cache.
5. Have a local fallback ready: `cd web && npx serve out`, then open the printed
   `localhost` URL. The build is already in `web/out`.
6. Keep this guide open at section 19.10 on a phone or second screen.
7. Say the numbers slowly. “Twenty-five thousand four hundred and thirty-one” is hard to
   follow; “about twenty-five thousand baskets” is not. Use the rounded form when speaking
   and the exact form on screen.

---

#### Slide 1 — Title (0:00–0:45)

**On screen:** `BasketWise`, subtitle “From grocery receipts to recommendations people can
explain”, the receipt visual, three product chips, and the rule chip
`cheeses → deli meats · lift 8.78`.

**Say:**

> “Good morning. Every grocery receipt is a small puzzle. One basket tells you what one
> household bought on one day. But across twenty-five thousand baskets, patterns start to
> repeat. BasketWise mines those patterns and turns them into a recommendation you can
> explain in one sentence: customers who bought cheeses also bought deli meats, sixty-three
> point five percent of the time — eight point seven eight times more often than chance.
>
> I'm Shahriar, and this is my CSE 426 project. I'll spend the first half on the method and
> the evidence, then demo the live site.”

**Transition:** “The first question was not which algorithm. It was which data.”

**Why this works:** it states the product, the strongest result and the structure of the
talk in under a minute, without a slide full of agenda bullets.

---

#### Slide 2 — Real baskets, real signal (0:45–1:40)

**On screen:** four stat cards — **500** households, **289,425** receipt lines, **25,431**
baskets, **294** product categories — plus the source line and the callout “Product
categories, not SKUs”.

**Say:**

> “I started with the supplied Kaggle grocery file. At half a percent support it produced
> exactly one positive item-to-item rule, and the maximum lift was one point one two. That is
> barely better than guessing.
>
> I switched to Complete Journey, the 84.51° and Dunnhumby household study. I sampled five
> hundred households with a fixed seed, kept two hundred eighty-nine thousand receipt lines,
> and grouped them into twenty-five thousand four hundred and thirty-one baskets across two
> hundred ninety-four product categories.
>
> Two deliberate reductions: five hundred households, and categories instead of SKUs. The
> categories keep the rules readable and the matrix small enough to mine on a laptop.”

**Transition:** “Once the data was settled, the pipeline had to be reproducible.”

**If asked about the Kaggle file:** the switch is documented in `ASSUMPTIONS.md`; the Kaggle
run was not discarded silently, it was measured and rejected for lack of signal.

---

#### Slide 3 — One pipeline, one source of truth (1:40–2:35)

**On screen:** six-step pipeline Clean → Basket → Encode → Mine → Rank → Export; the formula
strip; the callout “The website reads JSON only. No mining in the browser.”

**Say:**

> “There is one source of truth: the notebook. It reads the CSV and cleans it — hidden
> missing values, exact duplicates, name variants, day-first dates. It groups one member and
> one date into one basket and one-hot encodes the result.
>
> Apriori and FP-Growth then mine the same matrix at the same support threshold. The rules
> are ranked by support, confidence and lift, and four JSON files are exported.
>
> Support is how common the combination is. Confidence is how often the consequent appears
> when the antecedent is there. Lift compares that with the consequent's normal popularity:
> is this a relationship, or just a popular item?
>
> The website reads only those four files. There is no mining in the browser, no database,
> and no hard-coded number on any page.”

**Transition:** “So what did the baskets actually reveal?”

**Demo tie-in:** the formula strip is the same arithmetic you will point at on the rules
page.

---

#### Slide 4 — What the baskets revealed (2:35–3:45)

**On screen:** three rule cards, the stat row, and the algorithm footnote.

**Say:**

> “These are the results. The strongest rule is cheeses to deli meats: two point nine one
> percent support, sixty-three point five percent confidence, lift eight point seven eight.
> In plain terms, deli meats are already popular, but they are almost nine times more likely
> when cheese is in the basket.
>
> The second rule is pasta sauce to dry noodles, lift eight point seven five. The third card
> shows the method goes beyond pairs: bread and beef together point to vegetables and milk.
>
> At two point two five percent support and ten percent confidence, the notebook produced
> seven hundred sixty-three frequent itemsets and two thousand four hundred fifty-one rules.
> Two thousand four hundred forty-nine are positive associations; I export a readable five
> hundred, keeping each recommendable item's best rules.
>
> Both algorithms returned exactly the same seven hundred sixty-three itemsets. That is the
> correctness check. Apriori took two point zero one seconds; FP-Growth took twenty-seven
> point zero nine. On two hundred ninety-four categories, Apriori's simple counting wins —
> the honest result.”

**Transition:** “A notebook alone is not a product. Here is what makes it usable.”

**Do not say:** “FP-Growth is always faster.” It is not, on this data. The measured result
is the interesting part.

---

#### Slide 5 — From notebook to live product (3:45–4:30)

**On screen:** three proof points (Reproducible, Validated, Live), the limits line, the next
steps, and the green `Live demo →` band with the URL.

**Say:**

> “So this is more than a notebook. It is reproducible: one seeded notebook writes every
> number. It is validated: four JSON contracts are checked before anything is published —
> keys, rounding, ordering, and lift above one. And it is live: five pages, four charts, light
> and dark, and every figure on screen comes from the JSON.
>
> The limits are real: five hundred households, category-level items, no quantity or time
> awareness, and correlation is not causation. The next step is time-aware rules and a
> precision-at-k evaluation.
>
> The best way to see it is to use it. Let me switch to the live site.”

**Transition:** click the browser. Do not read the URL aloud; point at it and move.

---

#### Demo — Home (4:30–5:15)

**Action:** switch to the browser, already on `/`. Scroll once so the figures and the slip are
both visible.

**Say:**

> “This is the home page. Every number here is read at runtime from the JSON: twenty-five
> thousand four hundred and thirty-one baskets, two hundred ninety-four items, five hundred
> members, five hundred exported rules.
>
> The slip on the right is not a mock-up. It is the first recommendation for cheeses in
> recommendations.json: deli meats, lift eight point seven eight, and the sentence reads
> ‘sixty-three point five percent of baskets with cheeses also had deli meats.’
>
> Below, the six-step pipeline is the same one from the slides, and this band repeats the
> strongest rule in plain English.”

**Click:** `Find a recommendation`.

**Timing note:** if the network is slow, the card shows “Reading the recommendation sheet”
with skeleton lines. Keep talking; it resolves in under a second on a warm cache.

---

#### Demo — Recommender, one item (5:15–6:15)

**Action:** the page opens in **One item** mode with `cheeses` selected. Point at the three
cards in order.

**Say:**

> “This is the recommender. One-item mode is selected by default, and cheeses is already
> chosen. The cards are ranked by lift, then confidence.
>
> Deli meats is first: sixty-three point five percent confidence, lift eight point seven
> eight. Baked bread is second: sixty-two point nine percent confidence — almost the same
> reliability — but lift is only two point three six. Fluid milk is third: sixty point four
> percent confidence, lift two point zero two.
>
> That gap is the whole reason the site ranks on lift and never on confidence alone. If I
> ranked by confidence, I would recommend the most popular staple to everyone, and the
> recommendation would stop being interesting.
>
> The bar is confidence; the number on the right is lift; the sentence under each item is the
> rule in plain English.”

**Optional 10-second beat:** type a rare item, show the empty state (“No recommendations for
this item” + `Try cheeses`), then click `Try cheeses`. This proves the page handles failure
without a blank screen. Skip it if you are behind.

**Click:** `Basket`.

---

#### Demo — Recommender, basket (6:15–7:05)

**Action:** click `Try dry noodles and beef` in the empty state. If the basket is not empty,
add the two items through the combobox instead.

**Say:**

> “Basket mode answers a harder question. I add two items — dry noodles and beef — and every
> rule whose whole antecedent fits the basket gets to vote. Items already in the basket are
> never recommended back.
>
> Five rules match. Pasta sauce is first: forty-four point seven percent confidence, lift
> eight point seven five. Vegetables shelf stable is second at forty-two point two percent,
> lift three point nine seven. Then bread, milk and bag snacks.
>
> Notice the confidence is lower than the one-item case because a two-item antecedent is more
> specific, but lift is still high.
>
> And this is a lookup over the exported rules, not new mining. The browser filters five
> hundred rules; it does not run Apriori.”

**Click:** `Rules` in the top nav.

---

#### Demo — Rules (7:05–7:55)

**Action:** the page opens at the default: 500 of 500, sorted by lift descending, page 1 of
25.

**Say:**

> “The rule ledger shows all five hundred exported rules, twenty per page, twenty-five pages.
> By default they are sorted by lift, descending. Every row gives support, confidence and
> lift.
>
> I can type ‘cheeses’ — five rules match, including both directions of the strongest pair.
> Look at the two rows together: cheeses to deli meats is sixty-three point five percent
> confidence, but deli meats to cheeses is forty point two. Same support, same lift, different
> confidence. That is the clearest proof that confidence is directional and lift is not.
>
> The two sliders add constraints. If I raise minimum lift to eight point five, only those
> two directions survive. Reset filters puts everything back.”

**Actions:** type `cheeses`; drag lift to 8.5; pause; click `Reset filters`.

**Optional:** click the `Support` header once to show sorting, then reset again.

**Click:** `Insights`.

---

#### Demo — Insights (7:55–8:35)

**Action:** scroll slowly through the four figures and four charts. Hover one bar in chart 1
if the projector is bright.

**Say:**

> “Insights is the data behind the rules: twenty-five thousand four hundred and thirty-one
> transactions, two hundred ninety-four items, two point two five percent minimum support,
> ten percent minimum confidence.
>
> The first chart is the top fifteen items. The second is a year of shopping — steady rather
> than seasonal, which is one reason the rules ignore time. The third is basket size: most
> trips carry one to five categories, and the longest has seventy-three.
>
> The fourth is the algorithm comparison: seven hundred sixty-three itemsets each, two point
> zero one seconds versus twenty-seven point zero nine, identical results.”

**Click:** `Notebook`.

---

#### Demo — Notebook (8:35–9:00)

**Action:** the page opens at the top. Scroll to “A worked rule”; do not read the whole page.

**Say:**

> “The last page is the method without the plots: cleaning, thresholds, one worked rule, the
> algorithms, the exports, and the limits.
>
> The worked rule is the one from the slides, with the arithmetic spelled out: about seven
> hundred forty of the twenty-five thousand baskets contain both sides.
>
> Everything here is generated from the same four JSON files. Nothing is retyped.”

**Optional:** click `Open the notebook on GitHub` to show the executed notebook, then go back.
Only if you have spare time.

---

#### Close (9:00–9:30)

**Action:** return to the home page or leave the notebook page. Face the room.

**Say:**

> “To close: the notebook explains it, the exports validate it, and the site makes it usable.
>
> One sentence to remember: customers who bought cheeses also bought deli meats sixty-three
> point five percent of the time — eight point seven eight times more often than chance.
>
> Thank you. I'm happy to take questions.”

**Then stop talking.** Do not fill the buffer. The silence invites the first question and
keeps you inside 10:00.

---

### 19.11 If something breaks during the demo

| Problem | What to do | What to say |
| --- | --- | --- |
| Vercel is slow or offline | Switch to the local build: `cd web`, `npx serve out`, open the printed localhost URL | “The site is a static export, so the local copy is identical.” |
| A JSON file 404s | The page shows “The data did not load.” Click **Try again** once, then switch to the local copy | “This is the error state, which is also part of the design — no silent blank pages.” |
| The combobox will not accept a typed word | Click the suggestion in the dropdown; Enter only selects when the list is open | “I'll pick it from the list.” |
| A filter returns nothing | Click **Reset filters** | “The filters are cumulative, so I'll reset them.” |
| The projector washes out the green | Switch to dark mode with the header button | “The site ships both palettes.” |
| You are running over time | Skip the Notebook page and the optional empty-state beat; close after Insights | “The notebook is linked from every page; let me close on the result.” |
| You are under time | Add the empty-state beat in the recommender and open the GitHub notebook | — |

Keep a PDF or screenshots of the five pages on the desktop as a last resort. A live demo is
better, but a calm fallback is better than dead air.

---

### 19.12 Likely questions and short answers

**“Why is support 2.25% and not 0.5%?”**
Category-level baskets are dense. At `0.005`, Apriori tried to allocate roughly 40 GB and ran
out of memory. At `0.01` it produced 39,858 rules, which is unreadable. The notebook's safety
loop raised support until the rule count was useful; it settled at `0.0225`, which still
requires about 572 supporting baskets per itemset.

**“Why was Apriori faster than FP-Growth?”**
FP-Growth's advantage appears on larger, denser databases. Here there are only 294 columns
and about 25k baskets; Python's tree construction costs more than Apriori's counting. Both
returned identical itemsets, so the comparison is fair.

**“Why product categories instead of SKUs?”**
`product_type` has 2,242 labels, many unreadable and extremely sparse. `product_category`
has about 300 readable labels. Categories produce interpretable rules and a matrix small
enough to mine. The trade-off is recorded in `ASSUMPTIONS.md`.

**“Why do only 67 items have recommendations?”**
The recommender needs a rule whose antecedent is exactly that one item and whose consequent
is a single item. Many categories never clear support as an antecedent, so they have no
single-item follow-up. The site says so explicitly instead of inventing one.

**“What is the difference between the two recommender modes?”**
Item mode uses `recommendations.json` and requires the antecedent to be exactly the chosen
item. Basket mode filters `rules.json` and requires the rule's entire antecedent to be a
subset of the basket, then removes items already in the basket.

**“Is lift 8.78 causal?”**
No. It means the pair appears together 8.78 times more often than independence would predict.
It does not mean cheese causes deli-meat purchases.

**“Why does `coupon/misc items` show a lift below 1?”**
It has fewer than five positive single-item follow-ups, so `recommend()` fills the list with
the remaining rules, and two of those are below chance. The site displays the lift honestly
rather than hiding it. A future fix is a lift floor inside `recommend()`.

**“Does the website mine anything?”**
No. It fetches four static JSON files. `recommendForBasket()` is a filter and sort over the
500 exported rules.

**“Can it handle new data?”**
Yes. Re-run `scripts/fetch_completejourney.py`, execute the notebook, run
`scripts/validate_exports.py`, copy the four JSON files into `web/public/data/`, and rebuild.
No page code changes.

**“What would you do with more time or data?”**
Time-aware rules, quantity-weighted support, SKU-level mining on a larger sample, and a
hold-out evaluation using precision@k and recall@k instead of ranking by lift alone.

---

### 19.13 One-page cue card

Print this and keep it beside the keyboard.

```
0:00  S1  Receipt → 25k baskets → cheeses/deli 63.5%, lift 8.78
0:45  S2  Kaggle too weak (1 rule, lift 1.12) → Complete Journey
          500 households · 289,425 lines · 25,431 baskets · 294 categories
1:40  S3  Clean → Basket → Encode → Mine → Rank → Export
          support · confidence · lift; no mining in the browser
2:35  S4  cheeses → deli meats 63.5% / 8.78
          pasta sauce → dry noodles 52.7% / 8.75
          763 itemsets · 2,451 rules · 500 exported
          Apriori 2.04 s · FP-Growth 24.57 s · identical
3:45  S5  Reproducible · Validated · Live → switch to browser

4:30  HOME     25,431 / 294 / 500 / 500; slip = deli meats 63.5%
5:15  ITEM     cheeses → deli 8.78, bread 2.36, milk 2.02
6:15  BASKET   dry noodles + beef → pasta sauce 44.7% / 8.75
7:05  RULES    500 of 500, page 1 of 25; filter cheeses → 5;
                lift 8.5 → 2; reset
7:55  INSIGHTS 4 figures, 4 charts; 763 each; 2.04 vs 24.57
8:35  NOTEBOOK worked rule = 740 shown (exact 739) of 25,431 baskets
9:00  CLOSE    notebook explains · exports validate · site uses
```

---

That is the full site and the full talk. The walkthrough is accurate to the deployed build;
if the data changes, the sentences and numbers update themselves, but the layout, controls
and script structure stay the same.
