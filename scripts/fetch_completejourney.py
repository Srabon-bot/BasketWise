"""Create data/Groceries_dataset.csv from the Complete Journey study.

The website and the notebook expect one row per purchased item:

    Member_number,Date,itemDescription

This script builds that file from the 84.51° / Dunnhumby *Complete Journey*
sample that ships with the `completejourney` R package. The raw files are
downloaded once into `data/raw/` and are not committed (see .gitignore):

    transactions.rds   one row per item on a receipt
    products.rda       product metadata, including product_category

Because the raw transactions are far larger than this project needs, the
script keeps a fixed random sample of households (seed 42) and uses the
product category as the "item". Categories are coarser than SKUs but they
are readable, and they keep the one-hot basket matrix small enough to mine
with Apriori.

Usage:
    pip install pyreadr
    python scripts/fetch_completejourney.py
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import pyreadr
except ImportError:  # pragma: no cover - dependency hint
    sys.exit("pyreadr is required: pip install pyreadr")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUT_PATH = PROJECT_ROOT / "data" / "Groceries_dataset.csv"

BASE_URL = "https://github.com/bradleyboehmke/completejourney/raw/master/data"
FILES = {
    "transactions.rds": f"{BASE_URL}/transactions.rds",
    "products.rda": f"{BASE_URL}/products.rda",
}

HOUSEHOLD_SAMPLE = 500
RANDOM_STATE = 42


def download(name: str, url: str) -> Path:
    """Download one raw file unless it is already cached."""
    destination = RAW_DIR / name
    if destination.exists():
        print(f"Using cached {destination.name} ({destination.stat().st_size / 1e6:.1f} MB)")
        return destination

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {name} ...")
    urllib.request.urlretrieve(url, destination)
    print(f"  saved {destination.name} ({destination.stat().st_size / 1e6:.1f} MB)")
    return destination


def read_r(path: Path) -> pd.DataFrame:
    """Read an .rds/.rda file and return its only data frame."""
    frames = pyreadr.read_r(str(path))
    if not frames:
        raise ValueError(f"No data frame found in {path}")
    return next(iter(frames.values()))


def main() -> None:
    transactions = read_r(download("transactions.rds", FILES["transactions.rds"]))
    products = read_r(download("products.rda", FILES["products.rda"]))

    print(f"Raw transactions: {len(transactions):,} lines")

    # Attach the product category, which becomes the mined "item".
    df = transactions.merge(
        products[["product_id", "product_category"]],
        on="product_id",
        how="left",
    )
    df = df[df["quantity"] > 0].copy()

    # A fixed household sample keeps the file and the one-hot matrix small.
    households = np.sort(df["household_id"].unique())
    chosen = np.random.RandomState(RANDOM_STATE).choice(
        households, size=min(HOUSEHOLD_SAMPLE, len(households)), replace=False
    )
    df = df[df["household_id"].isin(chosen)].copy()

    df["Member_number"] = df["household_id"].astype(int)
    df["Date"] = pd.to_datetime(df["transaction_timestamp"]).dt.normalize()
    df["itemDescription"] = df["product_category"].str.strip().str.lower()

    df = df.sort_values(["Member_number", "Date", "itemDescription"])
    out = df[["Member_number", "Date", "itemDescription"]].copy()
    date_min = out["Date"].min().date()
    date_max = out["Date"].max().date()
    out["Date"] = out["Date"].dt.strftime("%d-%m-%Y")

    out.to_csv(OUT_PATH, index=False)

    baskets = df.groupby(["Member_number", "Date"]).size()
    print()
    print(f"Households sampled : {out['Member_number'].nunique():,}")
    print(f"Rows written       : {len(out):,}")
    print(f"Baskets            : {len(baskets):,}")
    print(f"Product categories : {out['itemDescription'].nunique():,}")
    print(f"Missing categories : {out['itemDescription'].isna().sum():,} (kept for cleaning)")
    print(f"Date range         : {date_min} to {date_max} (day-first, as the notebook expects)")
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
