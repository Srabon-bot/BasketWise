"""
make_synthetic_data.py
======================
Creates a realistic stand-in for the Kaggle "Groceries Dataset" so the whole
BasketWise pipeline can run even when the real CSV is not available.

The output has exactly the same three columns as the real file:

    Member_number, Date, itemDescription

Design choices
--------------
* ~38,000 rows, ~160 distinct grocery items.
* Item popularity follows a Zipf-like curve (a few very popular staples).
* Basket sizes are drawn from a realistic distribution (mostly 2-6 items).
* Several item pairs are deliberately "planted" so association rules exist.
* A little mess is injected on purpose: extra spaces, mixed case,
  exact duplicate rows, and "?" placeholders for hidden missing values.

Everything is seeded, so re-running the script produces the same file.

Usage
-----
    python scripts/make_synthetic_data.py
    python scripts/make_synthetic_data.py --out data/Groceries_dataset.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
TARGET_ROWS = 38_000

# 160 realistic grocery items, roughly ordered from staples to specialties.
ITEMS = [
    "whole milk", "other vegetables", "rolls/buns", "soda", "yogurt",
    "bottled water", "root vegetables", "tropical fruit", "shopping bags", "sausage",
    "pastry", "citrus fruit", "bottled beer", "newspapers", "canned beer",
    "pip fruit", "whipped/sour cream", "brown bread", "white bread", "domestic eggs",
    "fruit/vegetable juice", "margarine", "coffee", "chicken", "beef",
    "frozen vegetables", "specialty bar", "pork", "butter", "curd",
    "napkins", "tea", "buns", "sugar", "waffles",
    "long life bakery product", "hygiene articles", "cream cheese", "dessert", "cheese",
    "candy", "berries", "canned fish", "canned fruit", "canned vegetables",
    "cereals", "chocolate", "chocolate marshmallow", "cocoa drinks", "condensed milk",
    "cooking chocolate", "crackers", "cream", "decalcifier", "deep frozen vegetables",
    "dental care", "detergent", "dish cleaner", "dishes", "dog food",
    "domestic kitchen towels", "drinking water", "dried fruit", "dried plums", "egg noodles",
    "energy drinks", "finished products", "fish", "flour", "flower (seeds)",
    "flower soil/fertilizer", "frankfurter", "frozen chicken", "frozen fish", "frozen meals",
    "frozen potato products", "grapes", "hair spray", "ham", "hamburger meat",
    "hand towels", "hard cheese", "herbs", "honey", "house keeping products",
    "ice cream", "instant coffee", "instant noodles", "jam", "ketchup",
    "kitchen utensil", "light bulbs", "liqueur", "liqueur/wine", "liver pate",
    "make up remover", "male cosmetics", "mayonnaise", "meat", "miscellaneous",
    "mustard", "nuts/prunes", "oil", "onions", "oral hygiene",
    "organic products", "packaged fruit/vegetables", "pasta", "pet care", "photo/film",
    "pickled vegetables", "popcorn", "pork sausage", "pot plants", "potatoes",
    "poultry", "preservation products", "processed cheese", "prosecco", "pudding powder",
    "ready soups", "rice", "roll products", "rubbing alcohol", "salad dressing",
    "salt", "sauces", "sausage rolls", "seasonal products", "semi-finished bread",
    "skin care", "slow cooking products", "small canned fish", "snacks", "soap",
    "soft cheese", "soups", "sparkling wine", "specialty cheese", "spices",
    "spread cheese", "sweet spreads", "syrup", "tinned fruit", "toilet cleaner",
    "toothpaste", "tortilla", "turkey", "UHT-milk", "vinegar",
    "wafer", "white wine", "whole wheat bread", "wine", "zwieback",
]

# Pairs that are deliberately bought together (anchor, partner, probability).
# Anchors are popular items, so each pair clears a 0.5% support threshold.
PLANTED_PAIRS = [
    ("whole milk", "yogurt", 0.42),
    ("whole milk", "whipped/sour cream", 0.30),
    ("whole milk", "brown bread", 0.24),
    ("rolls/buns", "butter", 0.38),
    ("rolls/buns", "sausage", 0.30),
    ("white bread", "butter", 0.36),
    ("white bread", "domestic eggs", 0.28),
    ("other vegetables", "tropical fruit", 0.32),
    ("other vegetables", "root vegetables", 0.27),
    ("soda", "chips", 0.35),
    ("bottled water", "citrus fruit", 0.28),
    ("coffee", "sugar", 0.40),
    ("coffee", "cream cheese", 0.18),
    ("tea", "biscuits", 0.33),
    ("pasta", "tomato sauce", 0.35),
    ("pasta", "hard cheese", 0.27),
    ("beef", "onions", 0.29),
    ("chicken", "spices", 0.31),
    ("pork", "potatoes", 0.26),
    ("frozen vegetables", "frozen potato products", 0.24),
]

# A few extra items that only appear as partners, plus some pantry basics.
EXTRA_ITEMS = ["chips", "tomato sauce", "biscuits"]

ITEMS = sorted(set(ITEMS + EXTRA_ITEMS))


def make_weights(n_items: int) -> np.ndarray:
    """Zipf-like popularity: rank 1 gets the largest weight."""
    ranks = np.arange(1, n_items + 1)
    weights = 1.0 / np.power(ranks, 1.08)
    return weights / weights.sum()


def choose_basket_items(rng: np.random.Generator, item_index: dict[str, int],
                        weights: np.ndarray) -> list[str]:
    """Draw one realistic basket, then add a few planted co-purchases."""
    size_probs = [0.16, 0.20, 0.18, 0.14, 0.10, 0.08, 0.06, 0.04, 0.03, 0.01]
    size = int(rng.choice(np.arange(1, 11), p=size_probs))

    # Primary items sampled without replacement, weighted by popularity.
    idx = rng.choice(len(ITEMS), size=min(size, len(ITEMS)), replace=False,
                     p=weights)
    basket = {ITEMS[i] for i in idx}

    # Planted pairs: if the anchor is present, sometimes add the partner.
    for anchor, partner, prob in PLANTED_PAIRS:
        if anchor in basket and partner in basket:
            continue
        if anchor in basket and rng.random() < prob:
            basket.add(partner)
        elif partner in basket and rng.random() < prob * 0.35:
            basket.add(anchor)

    return sorted(basket)


def inject_mess(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Add realistic dirt: stray spaces, mixed case and "?" placeholders."""
    df = df.copy()

    # 1) Extra spaces / mixed case on ~2% of rows (more than one flavour).
    dirty_idx = rng.choice(df.index, size=int(len(df) * 0.02), replace=False)
    for i in dirty_idx:
        original = df.at[i, "itemDescription"]
        flavour = rng.integers(0, 3)
        if flavour == 0:
            df.at[i, "itemDescription"] = f"  {original} "
        elif flavour == 1:
            df.at[i, "itemDescription"] = original.upper()
        else:
            df.at[i, "itemDescription"] = original.title()

    # 2) Hidden missing values: "?" (about 0.4%).
    missing_idx = rng.choice(df.index, size=int(len(df) * 0.004), replace=False)
    df.loc[missing_idx, "itemDescription"] = "?"

    # 3) Exact duplicate rows (~120), which preprocessing must remove.
    dup_rows = df.sample(n=120, random_state=SEED)
    df = pd.concat([df, dup_rows], ignore_index=True)

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic grocery data.")
    parser.add_argument("--out", default="data/Groceries_dataset.csv",
                        help="Output CSV path (default: data/Groceries_dataset.csv)")
    args = parser.parse_args()

    rng = np.random.default_rng(SEED)

    item_index = {item: i for i, item in enumerate(ITEMS)}
    weights = make_weights(len(ITEMS))

    members = np.arange(1000, 3600)  # 2600 members
    start = pd.Timestamp("2014-01-01")
    end = pd.Timestamp("2015-12-31")

    rows: list[tuple[int, pd.Timestamp, str]] = []

    # Build baskets until we reach the target row count.
    while len(rows) < TARGET_ROWS:
        member = int(rng.choice(members))
        # Members shop more often around weekends/holidays; keep it simple.
        day_offset = int(rng.integers(0, (end - start).days + 1))
        date = start + pd.Timedelta(days=day_offset)
        basket = choose_basket_items(rng, item_index, weights)
        for item in basket:
            rows.append((member, date, item))

    df = pd.DataFrame(rows, columns=["Member_number", "Date", "itemDescription"])
    df = df.head(TARGET_ROWS)  # trim any overshoot from the last basket
    df["Date"] = df["Date"].dt.strftime("%d-%m-%Y")
    df = inject_mess(df, rng)
    df = df.sample(frac=1.0, random_state=SEED).reset_index(drop=True)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    print(f"Wrote {len(df):,} rows x {df.shape[1]} columns to {out_path}")
    print(f"Distinct raw item strings: {df['itemDescription'].nunique():,}")
    print(f"Members: {df['Member_number'].nunique():,}")
    print("WARNING: this is SYNTHETIC data. Replace it with the Kaggle CSV for the real analysis.")


if __name__ == "__main__":
    main()
