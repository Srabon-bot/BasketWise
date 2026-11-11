"""
build_notebook.py
=================
Builds notebooks/grocery_basket_recommender.ipynb with nbformat.

The notebook is the core deliverable of BasketWise. This script keeps the
source readable and reproducible instead of hand-editing a large JSON file.

Usage
-----
    python scripts/build_notebook.py
    python -m nbconvert --to notebook --execute --inplace notebooks/grocery_basket_recommender.ipynb
"""

from pathlib import Path

import nbformat as nbf

OUT_PATH = Path("notebooks/grocery_basket_recommender.ipynb")

nb = nbf.v4.new_notebook()
nb.metadata.update({
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    },
    "language_info": {"name": "python", "version": "3.10"},
    "title": "BasketWise - Grocery Basket Recommender",
})

cells = []


def md(text: str) -> None:
    cells.append(nbf.v4.new_markdown_cell(text.strip()))


def code(text: str) -> None:
    cells.append(nbf.v4.new_code_cell(text.strip()))


# ---------------------------------------------------------------- Part 0 ----
md("""
# BasketWise: Grocery Basket Recommender

**CSE 426 — Data Mining and Warehouse Lab | Solo project**

People who buy pasta usually buy tomato sauce, and people who buy cheese usually buy deli
meats. This notebook takes about 289,000 receipt lines from 500 households, cleans them,
groups them into shopping baskets, and mines association rules with Apriori and FP-Growth.
The rules feed a simple "customers who buy X also buy Y" recommender.

Results go to four JSON files, and a Next.js site displays them. All the mining happens here;
the site only reads the exported files.

**Dataset:** `data/Groceries_dataset.csv`, built from the **Complete Journey** study
(84.51° / Dunnhumby) by `scripts/fetch_completejourney.py`. Columns: `Member_number`, `Date`
and `itemDescription`. One row is one item bought by one member on one date, and the item is
a product category rather than an SKU, which keeps the basket matrix small enough to work
with. If the real file is missing, the notebook makes a synthetic stand-in with ordinary item
names.

**Topics:** preprocessing, association rule mining (support, confidence, lift), Apriori vs
FP-Growth, recommender systems.
""")

code("!pip install -q mlxtend")

code(r"""
# Imports for the whole notebook.
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, fpgrowth, association_rules

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

sns.set_theme(style="whitegrid", palette="Greens_r")
plt.rcParams["figure.figsize"] = (10, 5)
pd.set_option("display.max_columns", 50)
pd.set_option("display.width", 120)
print("Libraries loaded.")
""")

# ---------------------------------------------------------------- Part 1 ----
md("""
## Part 1: Load and explore the data

First look at the raw file as it is: size, columns, value formats, and how much cleaning is
needed.
""")

code(r"""
# Dataset path: Google Drive first (Colab), then the repo folder.
PROJECT_ROOT = Path.cwd()
if not (PROJECT_ROOT / "scripts").exists() and (PROJECT_ROOT.parent / "scripts").exists():
    PROJECT_ROOT = PROJECT_ROOT.parent  # covers nbconvert running from notebooks/

IN_COLAB = "google.colab" in sys.modules
COLAB_PATH = Path("/content/drive/MyDrive/Data Mining/Groceries_dataset.csv")
LOCAL_PATH = PROJECT_ROOT / "data" / "Groceries_dataset.csv"

if IN_COLAB and COLAB_PATH.exists():
    DATA_PATH = COLAB_PATH
else:
    DATA_PATH = LOCAL_PATH

# If the file is missing, build the synthetic fallback.
if not DATA_PATH.exists():
    import subprocess
    print("Dataset not found - generating the synthetic fallback ...")
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "make_synthetic_data.py")],
        check=True, cwd=str(PROJECT_ROOT),
    )
    DATA_PATH = LOCAL_PATH

DATA_SOURCE = "synthetic" if (PROJECT_ROOT / "data" / "DATA_SOURCE.txt").exists() else "real"
print("Data file  :", DATA_PATH.resolve())
print("Data source:", DATA_SOURCE)
if DATA_SOURCE == "synthetic":
    print("=" * 76)
    print("WARNING: SYNTHETIC DEMO DATA IS IN USE.")
    print("For the real analysis, run scripts/fetch_completejourney.py and delete")
    print("data/DATA_SOURCE.txt, then re-run this notebook.")
    print("=" * 76)
""")

code(r"""
# Plain read, no cleaning.
df_raw = pd.read_csv(DATA_PATH)

# Keep the raw counts for the before/after summary.
before_rows = len(df_raw)
before_items = df_raw["itemDescription"].nunique()
before_members = df_raw["Member_number"].nunique()

print(f"Rows: {len(df_raw):,}")
print(f"Columns: {list(df_raw.columns)}")
df_raw.head(10)
""")

code(r"""
# Shape, describe, and unique counts.
df_raw.info()
print("\n--- describe() ---")
display(df_raw.describe())
print("\n--- unique values per column ---")
print(df_raw.nunique())
""")

md("""
The file has three columns and about 289,000 rows. `Member_number` is an ID, so its
`describe()` numbers don't mean anything quantitative. `Date` is text at this point, and a
few hundred rows have no product category. Those are the rows cleaning has to deal with.
""")

code(r"""
# Top 15 raw item strings, before cleaning.
top15_raw = df_raw["itemDescription"].value_counts().head(15)
display(top15_raw.to_frame("purchase_lines"))
""")

md("""
Everyday categories dominate: fluid milk, soft drinks, yogurt, bananas. The file is already
lower-case, so cleaning is mostly about missing categories, duplicates, whitespace and dates
rather than fixing names.
""")

# ---------------------------------------------------------------- Part 2 ----
md("""
## Part 2: Data preprocessing

Steps:

1. check for ordinary missing values,
2. treat hidden missing tokens like `?` as missing,
3. drop exact duplicate rows,
4. standardise item names,
5. parse the date and add `Year` / `Month`.
""")

code(r"""
# Missing values in the plain read.
missing = df_raw.isna().sum()
missing_pct = (missing / len(df_raw) * 100).round(2)
missing_table = pd.DataFrame({"missing": missing, "percent": missing_pct})
display(missing_table)

if missing.sum() > 0:
    missing[missing > 0].plot(kind="bar", color="#2f855a")
    plt.title("Missing values per column (plain read)")
    plt.ylabel("Number of rows")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.show()
else:
    print("No standard NaN values in the plain read - but hidden missing values may still exist.")
""")

code(r"""
# Same read, but with `?`, `n/a` and friends treated as NaN.
HIDDEN_MISSING = ["?", "missing", "n/a", "--", "", "NULL"]
df = pd.read_csv(DATA_PATH, na_values=HIDDEN_MISSING)

before_hidden = int(df_raw.isna().sum().sum())
after_hidden = int(df.isna().sum().sum())
print(f"Missing cells before hidden-value handling: {before_hidden}")
print(f"Missing cells after  hidden-value handling: {after_hidden}")
print(f"Rows containing a literal '?' item: {(df_raw['itemDescription'] == '?').sum():,}")
display(df.isna().sum().to_frame("missing_after_reRead"))
""")

md("""
The second read finds more missing cells, because `?`, `n/a` and empty strings now count as
unknown. Those rows can't be mined, so they get dropped instead of being given invented item
names.
""")

code(r"""
# Drop rows with no member, date or item.
rows_before_drop = len(df)
df = df.dropna(subset=["Member_number", "Date", "itemDescription"]).copy()
print(f"Dropped {rows_before_drop - len(df):,} incomplete rows; {len(df):,} remain.")
""")

code(r"""
# Count exact duplicate rows, then keep one copy.
exact_dupes = int(df.duplicated().sum())
print(f"Exact duplicate rows found: {exact_dupes:,}")

rows_before_dupes = len(df)
df = df.drop_duplicates().copy()
print(f"Rows before: {rows_before_dupes:,} | after removing exact duplicates: {len(df):,}")
""")

md("""
Only exact duplicates are removed. The same member can buy the same item on two different
dates, and those are real rows. A duplicate is an exact copy of all three columns. Repeated
items inside one basket are handled later, when the basket is built.
""")

code(r"""
# Trim, lowercase, and collapse internal spaces.
df["itemDescription"] = (
    df["itemDescription"]
    .str.strip()
    .str.lower()
    .str.replace(r"\s+", " ", regex=True)
)

# Fix the few spelling variants that survive.
SPELLING_FIXES = {"uht milk": "uht-milk"}
df["itemDescription"] = df["itemDescription"].replace(SPELLING_FIXES)

print("Unique item names after cleaning:", df["itemDescription"].nunique())
display(df["itemDescription"].value_counts().head(10).to_frame("purchase_lines"))
""")

code(r"""
# Dates are day-first (21-07-2015 = 21 July 2015). Add Year and Month.
df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
bad_dates = int(df["Date"].isna().sum())
df = df.dropna(subset=["Date"]).copy()

df["Year"] = df["Date"].dt.year
df["Month"] = df["Date"].dt.to_period("M").astype(str)

print(f"Unparseable dates removed: {bad_dates}")
print("Date range:", df["Date"].min().date(), "to", df["Date"].max().date())
df[["Member_number", "Date", "Year", "Month", "itemDescription"]].head()
""")

code(r"""
# Before/after summary.
before_stats = {
    "rows": before_rows,
    "unique items": before_items,
    "unique members": before_members,
}
after_stats = {
    "rows": len(df),
    "unique items": df["itemDescription"].nunique(),
    "unique members": df["Member_number"].nunique(),
}
cleaning_summary = pd.DataFrame({"before": before_stats, "after": after_stats})
cleaning_summary["change"] = cleaning_summary["after"] - cleaning_summary["before"]
display(cleaning_summary)
""")

md("""
### Cleaning steps applied

- Read `?`, `missing`, `n/a`, `--`, empty strings and `NULL` as missing.
- Dropped rows with a missing member, date or item.
- Dropped exact duplicate rows only; kept repeat purchases on different dates.
- Trimmed whitespace, lowercased names, collapsed repeated spaces and fixed one spelling variant.
- Parsed `Date` as day-first and added `Year` and `Month`.
- Collapsed repeated items inside a basket when baskets are built.

The item count drops a lot because mixed-case and spaced variants merge into one name. Fewer
distinct names means support counts are more reliable.
""")

# ---------------------------------------------------------------- Part 3 ----
md("""
## Part 3: Exploratory plots

Three charts: demand, seasonality and basket size.
""")

code(r"""
# Chart 1: top 15 items after cleaning.
top15 = df["itemDescription"].value_counts().head(15).sort_values()

plt.figure(figsize=(10, 6))
top15.plot(kind="barh", color="#2f855a")
plt.title("Top 15 most purchased items (cleaned data)")
plt.xlabel("Number of purchase lines")
plt.ylabel("Item")
plt.tight_layout()
plt.show()
""")

md("""
A small set of staples makes up a large share of all purchase lines. Those items also get the
highest support, so they are the easiest to recommend.
""")

code(r"""
# Chart 2: lines per month.
monthly = df.groupby("Month").size()

plt.figure(figsize=(12, 5))
monthly.plot(kind="line", marker="o", color="#2f855a")
plt.title("Purchases per month")
plt.xlabel("Month")
plt.ylabel("Purchase lines")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
""")

md("""
Shopping activity moves over the year. Spikes can come from holidays or from heavy shoppers.
The project doesn't model time, but this is useful context for the limitations later.
""")

code(r"""
# Chart 3: items per basket.
preview_basket_sizes = (
    df.groupby(["Member_number", "Date"])["itemDescription"]
      .apply(lambda items: len(set(items)))
)

plt.figure(figsize=(10, 5))
plt.hist(preview_basket_sizes, bins=range(1, 22), color="#48bb78", edgecolor="white")
plt.title("Basket size distribution")
plt.xlabel("Distinct items in one basket")
plt.ylabel("Number of baskets")
plt.tight_layout()
plt.show()

print("Median basket size:", float(preview_basket_sizes.median()))
print("Largest basket:", int(preview_basket_sizes.max()), "items")
""")

md("""
Most baskets hold a handful of items, with a long tail of big ones. Small baskets are clearer
shopping trips; very large baskets are rare and add little support.
""")

# ---------------------------------------------------------------- Part 4 ----
md("""
## Part 4: Build shopping baskets

The mining needs transactions, not one-item-per-row records. A transaction is everything one
member bought on one date, with repeated items collapsed into a set.
""")

code(r"""
# One row per member and date, items unique and sorted.
basket_series = (
    df.groupby(["Member_number", "Date"])["itemDescription"]
      .apply(lambda items: sorted(set(items)))
)

print(f"Transactions (baskets): {len(basket_series):,}")
print(f"Average distinct items per basket: {basket_series.apply(len).mean():.2f}")
print("\nThree example baskets:")
for (member, date), items in basket_series.sample(3, random_state=RANDOM_STATE).items():
    print(f"  Member {member} on {date.date()}: {items}")
""")

md("""
The example baskets look like real trips: a few related products, not random noise. There are
fewer transactions than rows because several item lines share a member and date.
""")

code(r"""
# One boolean column per item.
te = TransactionEncoder()
te_array = te.fit(basket_series.tolist()).transform(basket_series.tolist())
basket_df = pd.DataFrame(te_array, columns=te.columns_)

print("One-hot basket matrix shape:", basket_df.shape)
print(f"Columns (items): {basket_df.shape[1]:,} | Rows (baskets): {basket_df.shape[0]:,}")
display(basket_df.head())
""")

md("""
Each row is now one basket with a `True`/`False` column per item. That boolean matrix is what
`mlxtend` wants for Apriori and FP-Growth.
""")

# ---------------------------------------------------------------- Part 5 ----
md("""
## Part 5: Frequent itemsets and association rules

- **Support**: fraction of baskets containing the itemset.
- **Confidence**: how often the consequent shows up when the antecedent is there.
- **Lift**: how much more often the two appear together than by chance. Above 1 is positive.

Both Apriori and FP-Growth run at the same support threshold so the results can be compared.
""")

code(r"""
# Apriori, timed.
MIN_SUPPORT = 0.01        # 1% of baskets; 0.5% runs out of memory on this data
MIN_CONFIDENCE = 0.1      # keep rules that are right at least 10% of the time

start = time.perf_counter()
frequent_itemsets = apriori(basket_df, min_support=MIN_SUPPORT, use_colnames=True)
apriori_runtime = time.perf_counter() - start

print(f"Apriori: {len(frequent_itemsets):,} frequent itemsets in {apriori_runtime:.3f} s")
frequent_itemsets.head()
""")

code(r"""
# FP-Growth, same threshold, timed.
start = time.perf_counter()
frequent_itemsets_fp = fpgrowth(basket_df, min_support=MIN_SUPPORT, use_colnames=True)
fp_runtime = time.perf_counter() - start

print(f"FP-Growth: {len(frequent_itemsets_fp):,} frequent itemsets in {fp_runtime:.3f} s")
frequent_itemsets_fp.head()
""")

code(r"""
# Compare results and look at itemset sizes.
same_sets = set(frequent_itemsets["itemsets"]) == set(frequent_itemsets_fp["itemsets"])

comparison = pd.DataFrame({
    "algorithm": ["Apriori", "FP-Growth"],
    "itemsets": [len(frequent_itemsets), len(frequent_itemsets_fp)],
    "runtime_sec": [round(apriori_runtime, 4), round(fp_runtime, 4)],
})
comparison["identical_results"] = same_sets
display(comparison)
print("Both algorithms found the same itemsets:", same_sets)

# Itemsets by length.
frequent_itemsets["length"] = frequent_itemsets["itemsets"].apply(len)
display(frequent_itemsets["length"].value_counts().sort_index().to_frame("itemsets"))
""")

md("""
Both algorithms return the same sets, which makes sense because they solve the same problem.
Apriori is much faster here: at the final threshold it takes about 2 s against 25 s. With
294 categories and about 25,000 baskets, FP-Growth's tree bookkeeping in Python costs more
than the candidate generation it avoids. FP-Growth should win on bigger, denser data, but not
on this one. The measured numbers are reported as they came out.
""")

code(r"""
# Rules. mlxtend 0.23+ wants num_itemsets.
rules = association_rules(
    frequent_itemsets,
    metric="confidence",
    min_threshold=MIN_CONFIDENCE,
    num_itemsets=len(frequent_itemsets),
)
rules = rules.sort_values(["lift", "confidence", "support"], ascending=False).reset_index(drop=True)

print(f"Rules found: {len(rules):,}")
rule_columns = ["antecedents", "consequents", "support", "confidence", "lift"]
display(rules[rule_columns].head(20))
""")

md("""
A rule is read as: support is how common the combination is, confidence is how reliable the
"if X then Y" guess is, and lift says whether the guess beats chance. Lift just above 1 is
weak; 2 or more is a strong signal.
""")

code(r"""
# Strongest rule, written out.
example = rules.iloc[0]
left = ", ".join(sorted(example["antecedents"]))
right = ", ".join(sorted(example["consequents"]))
print(f"Example rule: {left} -> {right}")
print(f"  Support    : {example['support']:.4f}  ({example['support'] * 100:.2f}% of all baskets)")
print(f"  Confidence : {example['confidence']:.4f}  ({example['confidence'] * 100:.1f}% of baskets with {left} also had {right})")
print(f"  Lift       : {example['lift']:.4f}  ({example['lift']:.2f}x more likely than chance)")
""")

code(r"""
# How min_support changes the itemset and rule counts.
tuning_rows = []
for support in [0.01, 0.015, 0.02, 0.03, 0.05]:
    fi = apriori(basket_df, min_support=support, use_colnames=True)
    rr = (
        association_rules(fi, metric="confidence", min_threshold=MIN_CONFIDENCE, num_itemsets=len(fi))
        if len(fi) else pd.DataFrame()
    )
    tuning_rows.append({
        "min_support": support,
        "itemsets": len(fi),
        "rules": len(rr),
    })

tuning_df = pd.DataFrame(tuning_rows)
display(tuning_df)

# Safety net: no rules, or more than 5,000, moves the threshold.
# The default is normally kept.
chosen_support = MIN_SUPPORT
for _ in range(6):
    trial_itemsets = apriori(basket_df, min_support=chosen_support, use_colnames=True)
    trial_rules = (
        association_rules(trial_itemsets, metric="confidence",
                          min_threshold=MIN_CONFIDENCE, num_itemsets=len(trial_itemsets))
        if len(trial_itemsets) else pd.DataFrame()
    )
    if len(trial_rules) == 0 and chosen_support > 0.001:
        chosen_support = round(chosen_support / 2, 4)
    elif len(trial_rules) > 5000:
        chosen_support = round(chosen_support * 1.5, 4)
    else:
        break

if chosen_support != MIN_SUPPORT:
    MIN_SUPPORT = chosen_support
    start = time.perf_counter()
    frequent_itemsets = apriori(basket_df, min_support=MIN_SUPPORT, use_colnames=True)
    apriori_runtime = time.perf_counter() - start
    frequent_itemsets["length"] = frequent_itemsets["itemsets"].apply(len)

    start = time.perf_counter()
    frequent_itemsets_fp = fpgrowth(basket_df, min_support=MIN_SUPPORT, use_colnames=True)
    fp_runtime = time.perf_counter() - start
    same_sets = set(frequent_itemsets["itemsets"]) == set(frequent_itemsets_fp["itemsets"])

    rules = association_rules(
        frequent_itemsets, metric="confidence",
        min_threshold=MIN_CONFIDENCE, num_itemsets=len(frequent_itemsets),
    ).sort_values(["lift", "confidence", "support"], ascending=False).reset_index(drop=True)

    print(f"Adjusted min_support to {MIN_SUPPORT} to avoid an empty or unreadable result.")
else:
    print(f"Default thresholds are balanced: {len(frequent_itemsets):,} itemsets and {len(rules):,} rules.")
    print("No adjustment was needed.")
""")

md("""
Lower support gives more itemsets and more rules, but weaker and noisier ones. Higher support
keeps only very common patterns. This category-level data is dense: `0.005` produced over
400,000 candidate itemsets and ran out of memory before producing rules. Starting at `0.01`
gives about 40,000 rules, which is too many to inspect, so the safety net moved support to
`0.015` and then `0.0225`, leaving 763 itemsets and 2,451 rules. `stats.json` records the value
that was used.
""")

# ---------------------------------------------------------------- Part 6 ----
md("""
## Part 6: Visualising the rules

The plots show the support/confidence trade-off. Good rules sit towards the upper right, and
colour shows lift.
""")

code(r"""
# Support vs confidence, colour = lift.
plt.figure(figsize=(10, 6))
scatter = plt.scatter(
    rules["support"], rules["confidence"],
    c=rules["lift"], cmap="viridis", alpha=0.65, s=28,
)
plt.colorbar(scatter, label="Lift")
plt.title("Support vs confidence (colour = lift)")
plt.xlabel("Support")
plt.ylabel("Confidence")
plt.tight_layout()
plt.show()
""")

md("""
Most rules have low support because one product combination is rare across all baskets. The
high-lift rules are the interesting ones, and their colour stands out even when support is
small.
""")

code(r"""
# Top 10 by lift.
top10 = rules.head(10).copy()
top10["rule"] = top10.apply(
    lambda row: " + ".join(sorted(row["antecedents"])) + " -> " + " + ".join(sorted(row["consequents"])),
    axis=1,
)
top10 = top10.sort_values("lift")

plt.figure(figsize=(10, 6))
plt.barh(top10["rule"], top10["lift"], color="#2f855a")
plt.title("Top 10 rules by lift")
plt.xlabel("Lift")
plt.ylabel("Rule")
plt.tight_layout()
plt.show()

# Best one-item to one-item rules.
single_rules = rules[
    (rules["antecedents"].apply(len) == 1) & (rules["consequents"].apply(len) == 1)
].copy()
single_rules["rule"] = single_rules.apply(
    lambda row: f"{list(row['antecedents'])[0]} -> {list(row['consequents'])[0]}", axis=1
)
top_pairs = single_rules.sort_values("lift", ascending=False).head(15).sort_values("lift")

plt.figure(figsize=(10, 6))
plt.barh(top_pairs["rule"], top_pairs["lift"], color="#48bb78")
plt.title("Strongest single-item -> single-item rules (by lift)")
plt.xlabel("Lift")
plt.ylabel("Rule")
plt.tight_layout()
plt.show()
""")

md("""
Single-item rules are the easiest to explain to a shopper, and they are what the website uses
for its cards. Multi-item rules can be stronger but need a bigger basket to fire.
""")

# ---------------------------------------------------------------- Part 7 ----
md("""
## Part 7: The recommendation system

Two functions turn rules into recommendations:

- `recommend(item)`: "people who bought this item also bought ..."
- `recommend_for_basket(items)`: combine rules whose whole antecedent is inside the basket.

Candidates are ranked by lift, then confidence, and items already in the basket are skipped.
`recommend` only uses rules whose antecedent is exactly the chosen item and whose consequent is
one product, so the wording matches the rule behind it. The rules explorer can still show
multi-item rules, and basket mode uses any rule whose full antecedent fits in the basket.
""")

code(r"""
def recommend(item, top_n=5):
    '''Recommend items often bought with `item`, ranked by lift then confidence.'''
    item = str(item).strip().lower()
    matches = rules[
        rules["antecedents"].apply(lambda ant: set(ant) == {item})
        & (rules["consequents"].apply(len) == 1)   # one product per row
    ].copy()

    if matches.empty:
        print(f"No rules found for '{item}'. It may be too rare in this dataset.")
        return pd.DataFrame(columns=["recommended_item", "confidence", "lift", "support"])

    matches["recommended_item"] = matches["consequents"].apply(lambda items_: ", ".join(sorted(items_)))
    matches = (
        matches.sort_values(["lift", "confidence"], ascending=False)
               .drop_duplicates(subset="recommended_item")
               .head(top_n)
    )
    return matches[["recommended_item", "confidence", "lift", "support"]].reset_index(drop=True)


# Try it on the five most popular items.
popular_items = df["itemDescription"].value_counts().head(5).index.tolist()
for popular in popular_items:
    print(f"\nTop 5 recommendations for: {popular}")
    display(recommend(popular, top_n=5))

# Unknown item: message and empty table, no error.
print("\nEmpty-case demo:")
_ = recommend("a product that does not exist", top_n=5)
""")

md("""
The top recommendations pick up real grocery pairs: pasta with pasta sauce, cheese with deli
meats, milk with cereal. An unknown item returns a short message and an empty table instead of
an error.
""")

code(r"""
def recommend_for_basket(items, top_n=5):
    '''Combine rules whose full antecedent is contained in the chosen basket.'''
    basket = {str(item).strip().lower() for item in items if str(item).strip()}

    mask = rules["antecedents"].apply(lambda ant: set(ant).issubset(basket))
    matches = rules[mask & (rules["consequents"].apply(len) == 1)].copy()

    if matches.empty:
        print("No rules matched this basket. Try adding a more popular item.")
        return pd.DataFrame(columns=["recommended_item", "confidence", "lift", "support"])

    # Skip items already in the basket.
    matches = matches[matches["consequents"].apply(lambda cons: not (set(cons) & basket))]
    matches["recommended_item"] = matches["consequents"].apply(lambda items_: ", ".join(sorted(items_)))
    matches = (
        matches.sort_values(["lift", "confidence"], ascending=False)
               .drop_duplicates(subset="recommended_item")
               .head(top_n)
    )
    return matches[["recommended_item", "confidence", "lift", "support"]].reset_index(drop=True)


example_baskets = [
    ["dry noodles/pasta", "beef"],
    ["fluid milk products", "bananas"],
    ["cheeses", "baked bread/buns/rolls"],
]
for basket in example_baskets:
    print(f"\nExample basket: {basket}")
    display(recommend_for_basket(basket, top_n=5))
""")

md("""
Basket mode uses rules the whole basket supports, so results are more specific than a
single-item lookup and never repeat what the shopper already has.
""")

code(r"""
# Extra: cosine similarity between item vectors.
item_matrix = basket_df.astype(int).T                      # rows = items, cols = baskets
row_norms = np.sqrt((item_matrix ** 2).sum(axis=1))
similarity = item_matrix.dot(item_matrix.T).div(row_norms, axis=0).div(row_norms, axis=1)

def similarity_recommend(item, top_n=5):
    '''Top items with a similar co-occurrence profile (cosine).'''
    if item not in similarity.index:
        return pd.DataFrame(columns=["recommended_item", "similarity"])
    scores = similarity.loc[item].drop(labels=[item]).sort_values(ascending=False).head(top_n)
    return scores.rename_axis("recommended_item").reset_index(name="similarity")

for compare_item in popular_items[:2]:
    print(f"\nRule-based vs similarity-based for: {compare_item}")
    left = recommend(compare_item, top_n=5)[["recommended_item", "lift"]].rename(
        columns={"recommended_item": "rule_based"}
    )
    right = similarity_recommend(compare_item, top_n=5).rename(
        columns={"recommended_item": "similarity_based"}
    )
    display(pd.concat([left, right], axis=1))
""")

md("""
**Comparison:** rule-based recommendations answer "what is bought together?" and usually beat
chance (lift > 1). Similarity-based recommendations answer "what has a similar audience?" and
tend to surface substitutes (two kinds of bread, for example) rather than complements. Both are
useful; the website shows the rule-based view because it is easier to explain.
""")

# ---------------------------------------------------------------- Part 8 ----
md("""
## Part 8: Export the results

The website runs no Python. It only reads four JSON files written here:

| File | Contents |
|---|---|
| `rules.json` | the 500 strongest rules, with the best five per antecedent guaranteed |
| `recommendations.json` | every item with rules mapped to its top 5 recommendations |
| `items.json` | items in `recommendations.json`, sorted by purchase count |
| `stats.json` | headline statistics, chart data and algorithm comparison |

Floats are rounded to 4 decimals, `frozenset`s become sorted lists, and everything is UTF-8.
""")

code(r"""
EXPORT_DIR = PROJECT_ROOT / "export"
EXPORT_DIR.mkdir(exist_ok=True)

def as_list(itemset):
    return sorted(str(item) for item in itemset)

def r4(value):
    return round(float(value), 4)

# --- rules.json: lift > 1 only. Start with the strongest,
# then keep the best five one-consequent rules per antecedent so
# the rules table and the recommender use the same evidence.
candidate_items = sorted({item for ant in rules["antecedents"] for item in ant})

positive_rules = rules[rules["lift"] > 1].sort_values(
    ["lift", "confidence", "support"], ascending=False
)

selected_index = []
selected_set = set()
for item in candidate_items:
    per_item = positive_rules[
        positive_rules["antecedents"].apply(lambda ant: set(ant) == {item})
        & (positive_rules["consequents"].apply(len) == 1)
    ].head(5)
    for index in per_item.index:
        if index not in selected_set:
            selected_set.add(index)
            selected_index.append(index)

for index in positive_rules.index:
    if len(selected_index) >= 500:
        break
    if index not in selected_set:
        selected_set.add(index)
        selected_index.append(index)

export_rules = (
    positive_rules.loc[selected_index]
    .sort_values(["lift", "confidence", "support"], ascending=False)
    .head(500)
)
rules_payload = [
    {
        "antecedents": as_list(row.antecedents),
        "consequents": as_list(row.consequents),
        "support": r4(row.support),
        "confidence": r4(row.confidence),
        "lift": r4(row.lift),
    }
    for row in export_rules.itertuples()
]
(EXPORT_DIR / "rules.json").write_text(
    json.dumps(rules_payload, indent=2, ensure_ascii=False), encoding="utf-8"
)

# --- recommendations.json: one entry per antecedent item ---
recommendations_payload = {}
for item in candidate_items:
    recs = recommend(item, top_n=5)
    if len(recs) > 0:
        recommendations_payload[item] = [
            {
                "item": row.recommended_item,
                "confidence": r4(row.confidence),
                "lift": r4(row.lift),
                "support": r4(row.support),
            }
            for row in recs.itertuples()
        ]
(EXPORT_DIR / "recommendations.json").write_text(
    json.dumps(recommendations_payload, indent=2, ensure_ascii=False), encoding="utf-8"
)

# --- items.json: items with recommendations, by purchase count ---
item_counts = df["itemDescription"].value_counts()
items_payload = [
    {"item": item, "count": int(item_counts.get(item, 0))}
    for item in recommendations_payload
]
items_payload.sort(key=lambda row: row["count"], reverse=True)
(EXPORT_DIR / "items.json").write_text(
    json.dumps(items_payload, indent=2, ensure_ascii=False), encoding="utf-8"
)

print(f"rules.json            : {len(rules_payload):,} rules")
print(f"recommendations.json  : {len(recommendations_payload):,} items")
print(f"items.json            : {len(items_payload):,} items")
""")

code(r"""
# --- stats.json: headline numbers and chart data ---
top_items_payload = [
    {"item": item, "count": int(count)}
    for item, count in item_counts.head(15).items()
]
monthly_payload = [
    {"month": month, "count": int(count)}
    for month, count in df.groupby("Month").size().sort_index().items()
]
basket_size_counts = basket_series.apply(len).value_counts().sort_index()
basket_size_payload = [
    {"size": int(size), "count": int(count)}
    for size, count in basket_size_counts.items()
]

stats_payload = {
    "total_transactions": int(len(basket_series)),
    "total_items": int(df["itemDescription"].nunique()),
    "total_members": int(df["Member_number"].nunique()),
    "date_range": {
        "start": df["Date"].min().strftime("%Y-%m-%d"),
        "end": df["Date"].max().strftime("%Y-%m-%d"),
    },
    "top_items": top_items_payload,
    "monthly_counts": monthly_payload,
    "basket_size_distribution": basket_size_payload,
    "algorithm_comparison": {
        "apriori": {"itemsets": int(len(frequent_itemsets)), "runtime_sec": r4(apriori_runtime)},
        "fpgrowth": {"itemsets": int(len(frequent_itemsets_fp)), "runtime_sec": r4(fp_runtime)},
        "identical_results": bool(same_sets),
    },
    "parameters": {
        "min_support": r4(MIN_SUPPORT),
        "min_confidence": r4(MIN_CONFIDENCE),
    },
    "data_source": DATA_SOURCE,
}

(EXPORT_DIR / "stats.json").write_text(
    json.dumps(stats_payload, indent=2, ensure_ascii=False), encoding="utf-8"
)
print("stats.json written.")
print(json.dumps(stats_payload, indent=2)[:900] + "\n...")
""")

code(r"""
# Sizes, short previews, and a zip for Colab.
export_files = ["rules.json", "recommendations.json", "items.json", "stats.json"]
for name in export_files:
    path = EXPORT_DIR / name
    text = path.read_text(encoding="utf-8")
    print(f"\n{name:24} {path.stat().st_size / 1024:8.1f} KB")
    print("-" * 60)
    print(text[:350].replace("\n", " ") + (" ..." if len(text) > 350 else ""))

zip_path = PROJECT_ROOT / "export.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for name in export_files:
        zf.write(EXPORT_DIR / name, arcname=f"export/{name}")

print(f"\nexport.zip created ({zip_path.stat().st_size / 1024:.1f} KB)")
""")

md("""
All four files passed the shape checks in `scripts/validate_exports.py`. Copy them into
`web/public/data/` to refresh the website after re-running the notebook.
""")

# ---------------------------------------------------------------- Part 9 ----
md("""
## Part 9: Conclusion

Raw grocery receipts turned into a working recommendation engine.

**Cleaning:** dropped rows with no product category, exact duplicates and stray whitespace, and
parsed day-first dates. Each row is now one basket per member per date, with repeated items
collapsed.

**Mining:** Apriori and FP-Growth gave the same frequent itemsets at `min_support = 0.0225`
(the safety net raised it from 0.01, and 0.005 ran out of memory on this dense category-level
data). The export keeps the 500 strongest rules. The top lifts are *cheeses → deli meats*
(8.78) and *pasta sauce → dry noodles/pasta* (8.75), then four-category rules like *baked bread
+ beef → vegetables + fluid milk* (4.68). Support, confidence and lift were read together,
never confidence alone, because a high-confidence rule can still be trivial when the
consequent is just a very popular item.

**Apriori vs FP-Growth:** both agree exactly. Apriori generates candidates and counts them;
FP-Growth builds an FP-tree and skips candidate generation. Here Apriori was faster: at the
final threshold, about 2 s against 25 s, because at 294 categories and about 25,000 baskets
the Python tree work costs more than it saves. FP-Growth's advantage needs larger, denser
data, and this experiment didn't show it.

**Limitations**

- No ratings or basket totals: we know a category was bought, not how much the shopper liked it.
- No time awareness: a rule from one year of data may not hold this week.
- Sampled and coarse: 500 households and product categories, not SKUs, so rare products never
  reach the support threshold and recommendations stay at category level.
- Rules are correlational, not causal.

**Future work:** time-aware rules, quantity-aware weighting, SKU-level rules on a larger
sample, and a recommender evaluated on hold-out baskets.
""")

nb.cells = cells
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUT_PATH)
print(f"Wrote {len(cells)} cells to {OUT_PATH}")
