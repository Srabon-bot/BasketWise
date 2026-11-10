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
- [x] Synthetic data generator
- [x] Notebook: preprocessing and baskets (Parts 0–4)
- [x] Notebook: Apriori / FP-Growth / recommender (Parts 5–7)
- [x] Notebook: exports and conclusion (Parts 8–9) + export validation
- [ ] Next.js website
- [ ] Deployment notes and screenshots

Full details are in the project PRD (`prd.md`).

## Quick start: data mining

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. (Optional) create the synthetic demo dataset if data/Groceries_dataset.csv is missing
python scripts/make_synthetic_data.py

# 3. Build and run the notebook
python scripts/build_notebook.py
python -m nbconvert --to notebook --execute --inplace notebooks/grocery_basket_recommender.ipynb

# 4. Validate the exported JSON
python scripts/validate_exports.py
```

The executed notebook is committed with outputs and plots, so you can read it without running
anything. Open it in Jupyter, VS Code, or upload it to Google Colab.

### Real vs synthetic data

If `data/Groceries_dataset.csv` is missing, `scripts/make_synthetic_data.py` creates a realistic
demo file (seed 42) plus `data/DATA_SOURCE.txt`. That marker tells the notebook and the website to
label the run as **synthetic/demo**. To use the real Kaggle file, replace
`data/Groceries_dataset.csv`, delete `data/DATA_SOURCE.txt`, and re-run the notebook.
