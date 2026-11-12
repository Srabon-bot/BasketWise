<div align="center">

# BasketWise

Market-basket analysis on real grocery receipts — frequent itemsets, association rules, and a rule-based recommender served as a fast static site.

[![Live Site](https://img.shields.io/badge/Live%20Site-basketwise--ten.vercel.app-22c55e?style=for-the-badge&logo=vercel&logoColor=white)](https://basketwise-ten.vercel.app/)
&nbsp;
[![Notebook](https://img.shields.io/badge/Notebook-View%20on%20GitHub-F37626?style=for-the-badge&logo=jupyter&logoColor=white)](https://github.com/Srabon-bot/BasketWise/blob/main/notebooks/grocery_basket_recommender.ipynb)
&nbsp;
[![Repository](https://img.shields.io/badge/Repository-BasketWise-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Srabon-bot/BasketWise)

</div>

---

## Overview

BasketWise takes the **Complete Journey** household grocery study, cleans 289,425 receipt lines, groups them into 25,431 shopping baskets, and mines what sells together with **Apriori** and **FP-Growth**. The strongest rules become a recommender that answers one practical question: *what leaves with this item?*

This is a solo **CSE 426 — Data Mining and Warehouse Lab** project. The executed Jupyter notebook is the source of truth; the website is a thin presentation layer that does no mining at all.

**Live site:** [https://basketwise-ten.vercel.app](https://basketwise-ten.vercel.app/)

> The best rule says it in one sentence: customers who bought `cheeses` also bought `deli meats` **63.5%** of the time — **8.78×** more often than chance.

---

## Screenshots

<div align="center">

### Home & Recommendation Slip

![Homepage](./docs/screenshots/home.png)

### Recommender — One Item

![Recommender](./docs/screenshots/recommend.png)

### Rule Ledger & Insights

<br />

| Rule Ledger | Insights |
|:---:|:---:|
| <img src="./docs/screenshots/rules.png" width="480" alt="Rule Ledger" /> | <img src="./docs/screenshots/insights.png" width="480" alt="Insights" /> |

### Methodology

![Notebook Guide](./docs/screenshots/notebook.png)

</div>

---

## Features

- One executed notebook that runs the whole pipeline from raw receipts to JSON
- Cleaning for hidden missing values, exact duplicates, name variants, and day-first dates
- Basket construction from one household and one shopping date
- **Apriori** and **FP-Growth** on the same one-hot matrix, with an identical-itemset correctness check
- Automatic support tuning that keeps the rule set readable instead of flooding it
- Support, confidence, and lift calculated for every rule
- Item mode: pick a product and see the strongest single-item follow-ups
- Basket mode: add up to six items and match every rule whose whole antecedent fits
- A searchable, sortable, filterable ledger of all 500 exported rules
- Four charts covering top items, monthly volume, basket sizes, and algorithm runtime
- A JSON contract validator that blocks a broken export before it reaches the site
- Every number on screen read at runtime from JSON — nothing hard-coded
- Fully static Next.js export with light and dark themes
- Responsive layout, keyboard-accessible controls, and visible loading, error, and empty states
- A labelled synthetic fallback so the pipeline still runs without the real dataset

---

## Tech Stack

| Layer | Technology |
|---|---|
| Analysis | ![Python](https://img.shields.io/badge/Python%203-3776AB?style=flat-square&logo=python&logoColor=white) ![pandas](https://img.shields.io/badge/pandas-150458?style=flat-square&logo=pandas&logoColor=white) ![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white) |
| Mining | ![mlxtend](https://img.shields.io/badge/mlxtend-4B8BBE?style=flat-square&logo=python&logoColor=white) Apriori, FP-Growth, `association_rules` |
| Visualisation | ![Matplotlib](https://img.shields.io/badge/Matplotlib-11557C?style=flat-square&logo=python&logoColor=white) ![seaborn](https://img.shields.io/badge/seaborn-4C72B0?style=flat-square&logo=python&logoColor=white) |
| Notebook | ![Jupyter](https://img.shields.io/badge/Jupyter-F37626?style=flat-square&logo=jupyter&logoColor=white) nbconvert, nbformat, pyreadr |
| Framework | ![Next.js](https://img.shields.io/badge/Next.js%2016-000000?style=flat-square&logo=nextdotjs&logoColor=white) App Router, static export |
| UI library | ![React](https://img.shields.io/badge/React%2019-61DAFB?style=flat-square&logo=react&logoColor=black) |
| Language | ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white) |
| Styling | ![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS%204-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white) |
| Charts | ![Recharts](https://img.shields.io/badge/Recharts-22B5BF?style=flat-square&logo=react&logoColor=white) |
| Data | ![Complete Journey](https://img.shields.io/badge/Complete%20Journey-84.51%C2%B0%20%2F%20Dunnhumby-22c55e?style=flat-square) |
| Hosting | ![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=vercel&logoColor=white) |

---

## How It Works

```text
Raw receipts
    │  clean
    ▼
Shopping baskets
    │  one-hot encode
    ▼
Boolean basket matrix
    │  Apriori + FP-Growth
    ▼
Frequent itemsets
    │  association rules
    ▼
Ranked rules
    │  export + validate
    ▼
Four JSON files  ──►  Static Next.js site
```

1. **Clean.** Treat hidden tokens as missing, drop unusable rows, remove exact duplicates, normalise item text, and parse dates day-first.
2. **Build baskets.** One `Member_number` plus one `Date` becomes one transaction; repeated purchases of the same category collapse into a set.
3. **Encode.** mlxtend's `TransactionEncoder` turns the baskets into a boolean matrix — one row per basket, one column per item.
4. **Mine.** Apriori and FP-Growth find frequent itemsets at the same support threshold; `association_rules` splits them into antecedent → consequent rules.
5. **Rank and recommend.** Rules are filtered and ordered by lift, then confidence. Item mode uses exact single-item antecedents; basket mode requires the whole antecedent to be present.
6. **Export and present.** The notebook writes four JSON files, `validate_exports.py` checks their contracts, and the site renders them in the browser.

### The Three Metrics

| Metric | Formula | Question it answers |
|---|---|---|
| **Support** | `count(X ∪ Y) / N` | Is this combination common enough to trust? |
| **Confidence** | `count(X ∪ Y) / count(X)` | When X is in the basket, how often is Y there too? |
| **Lift** | `confidence / support(Y)` | Is this a real relationship, or just a popular item? |

A rule can have high confidence and almost no lift when the consequent is a staple that appears in most baskets. That is why the recommender ranks on **lift first**, never confidence alone.
