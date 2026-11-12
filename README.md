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
