# BasketWise

**Smart grocery recommendations from shopping data.**

BasketWise is a solo CSE 426 (Data Mining and Warehouse Lab) project. It takes raw grocery
transaction records, cleans them, mines frequent itemsets and association rules with Apriori
and FP-Growth, and turns the rules into an item recommender. A small Next.js site presents the
exported results.

> The Jupyter/Colab notebook is the core deliverable. The website only displays what the
> notebook exports — no data mining logic lives in the web app.

## Project layout

```
BasketWise/
├── README.md
├── ASSUMPTIONS.md
├── data/                  # Groceries_dataset.csv (real or synthetic)
├── scripts/
│   ├── make_synthetic_data.py
│   ├── build_notebook.py
│   └── validate_exports.py
├── notebooks/             # grocery_basket_recommender.ipynb (executed)
├── export/                # rules, recommendations, items, stats (JSON)
└── web/                   # Next.js static site (later milestone)
```

## Roadmap

- [x] Repository scaffold
- [ ] Synthetic data generator
- [ ] Notebook: preprocessing and baskets (Parts 0–4)
- [ ] Notebook: Apriori / FP-Growth / recommender (Parts 5–7)
- [ ] Notebook: exports and conclusion (Parts 8–9) + export validation
- [ ] Next.js website
- [ ] Deployment notes and screenshots

Full details are in the project PRD (`prd.md`).
