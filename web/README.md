# BasketWise website

The presentation layer for the BasketWise data mining project. It reads the four JSON exports
from `public/data` in the browser and renders them. No mining runs here: the notebook in
`../notebooks/` is the source of truth.

## Run

```bash
npm install
npm run dev      # http://localhost:3000
npm run lint
npm run build    # static export to out/
```

## Data

`public/data/*.json` are copies of `../export/*.json`. The notebook mines
`../data/Groceries_dataset.csv`, a product-category extract of the Complete Journey
study (84.51° / Dunnhumby). That file is not committed; build it once with:

```bash
python ../scripts/fetch_completejourney.py
```

Then, after re-running the notebook:

```bash
python ../scripts/validate_exports.py
cp ../export/*.json public/data/    # Windows: Copy-Item ..\export\*.json public\data\ -Force
```

## Deploy

The app uses `output: "export"`, so `out/` can be served by any static host. Vercel and Netlify
work with the defaults; see the repository README for GitHub Pages caveats. The full Vercel
walkthrough, including the root-directory setting that this monorepo layout requires, is in
[`../docs/DEPLOY_VERCEL.md`](../docs/DEPLOY_VERCEL.md).

Full documentation, screenshots and assumptions live in the root `README.md` and
`ASSUMPTIONS.md`.
