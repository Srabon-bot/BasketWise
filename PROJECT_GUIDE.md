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

At the starting threshold `0.01`, this dataset produced **6,302 itemsets** in about **25 s**.

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
| `formatSeconds(value)` | `web/src/lib/data.ts` | `2.0092 → "2.01 s"` |
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
| Apriori | 763 | 2.01 s |
| FP-Growth | 763 | 27.09 s |

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
    "apriori": { "itemsets": 763, "runtime_sec": 2.0092 },
    "fpgrowth": { "itemsets": 763, "runtime_sec": 27.0901 },
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
