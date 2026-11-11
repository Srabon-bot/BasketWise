# Deploying BasketWise to Vercel

This guide deploys the website in `web/` to Vercel as a static site. It takes about five
minutes and needs no environment variables, database or server code.

> The steps below were checked against the Vercel and Next.js documentation and against this
> repository's local production build in `web/out/`. They have not been run against a live
> Vercel account, because the project does not own one. If the dashboard labels differ slightly,
> the values to look for are the ones quoted here: root directory `web`, build command
> `npm run build`, output directory `out`.

## What gets deployed

`web/` is a Next.js app configured for a fully static export (`output: "export"` in
`web/next.config.ts`). `npm run build` writes everything the site needs into `web/out/`:

| Path in `web/out/` | Contents |
| --- | --- |
| `index.html` | home page |
| `recommend/`, `rules/`, `insights/`, `notebook/` | one directory per route, each with its own `index.html` |
| `_next/` | JavaScript, CSS and fonts |
| `data/*.json` | copies of `export/*.json`, fetched by the browser at runtime |
| `404.html` | not-found page |

There are no API routes and no server components that run after the build. The deployed site is
plain HTML, CSS, JavaScript and JSON, so any static host would work — Vercel is simply the least
friction.

## Before you start

- The repository is on GitHub (this one is `Srabon-bot/BasketWise`).
- You have a Vercel account. The free Hobby plan is more than enough for this site.
- Nothing needs to be installed locally for the dashboard route. The command-line route needs
  Node.js 20.9 or newer, which is also what Next.js 16 requires.

**One thing to get right:** the repository root has no `package.json`. The app lives in `web/`,
next to the notebook, the exports and the README. Every deployment route below therefore has to
point at `web/`, not at the repository root. This is the single most common cause of a failed
first deploy.

## Option A — deploy from the dashboard

1. Sign in to Vercel and choose **Add New… → Project**.
2. Under **Import Git Repository**, pick `BasketWise`. Authorise GitHub access first if the
   repository is not listed.
3. On the configuration screen, set:

   | Setting | Value |
   | --- | --- |
   | Project Name | anything you like; it becomes `<name>.vercel.app` |
   | Framework Preset | **Next.js** (detected automatically) |
   | **Root Directory** | **`web`** — click *Edit* and select the folder |
   | Build Command | `npm run build` (the detected default) |
   | Output Directory | leave the detected default |
   | Install Command | leave the detected default (`npm install`) |
   | Environment Variables | none |

4. Leave **Include source files outside of the Root Directory** off. The site does not import
   anything from the repository root.
5. Press **Deploy**. The first build installs dependencies, runs `next build` and uploads
   `web/out/` as static files. It takes a couple of minutes.

After that, every push to `main` redeploys automatically, and every pull request gets its own
preview URL.

## Option B — deploy from the command line

Use this if you would rather not click through the dashboard, or if you already have the
repository cloned locally.

```bash
npm install -g vercel
vercel login

cd web
vercel          # first run: answer the prompts, then get a preview URL
vercel --prod   # promote the same project to production
```

Run both commands **from `web/`**. `vercel` records the linked project in `web/.vercel/`, which is
already ignored by `web/.gitignore`; do not commit it.

The first `vercel` run asks a few questions:

- *Set up and deploy?* — yes.
- *Which scope?* — your personal account, unless you have a team.
- *Link to existing project?* — no on the first run, yes afterwards.
- *What's your project's name?* — defaults to the folder name, `web`; rename it to `basketwise`
  if you prefer a tidier URL.
- *In which directory is your code located?* — `./`, because you are already inside `web`.

If detection ever misfires, confirm with `vercel project ls` that the project's root directory is
`web` and the framework is Next.js.

## Optional: `web/vercel.json`

No config file is required. The dashboard route and the CLI route both work with detection alone.
Add `web/vercel.json` only if you hit one of these situations:

- you run `vercel` from the repository root instead of `web/`;
- the output directory gets misdetected and the deployment serves a 404 for every route;
- you later add redirects, headers or custom caching.

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "outputDirectory": "out"
}
```

Keep it to those four keys. Do not add a catch-all rewrite to `/index.html`: this is not a
single-page app with client-side routing. Next.js emits a real `index.html` per route, and a
catch-all rewrite would break the four inner pages by serving the home page for all of them.

## Verify the deployment

Open the production URL and walk through this list. The trailing slashes matter — the site is
built with `trailingSlash: true`, so `/recommend` redirects to `/recommend/`.

- [ ] `/` loads the hero, the "Dataset at a glance" figures and the demo-data banner.
- [ ] `/recommend/` — searching `coffee` returns five follow-up items; basket mode with
      `whole milk` and `yogurt` returns ranked suggestions.
- [ ] `/rules/` — the ledger reports 500 rules, sorting and the support/lift sliders work, and
      pagination shows 20 rows per page.
- [ ] `/insights/` — four figures render: three bar charts and one line chart.
- [ ] `/notebook/` — the methodology page loads, linked in the footer as "Methodology".
- [ ] The theme toggle switches to dark and survives a reload.
- [ ] At 375px wide there is no horizontal scrolling; at desktop width the layout is centred.
- [ ] The browser console is free of errors.

The four data files are the part most likely to be missing, so check them directly:

```bash
curl -I https://<your-project>.vercel.app/data/stats.json
curl -I https://<your-project>.vercel.app/data/rules.json
```

Each should return `200` with `content-type: application/json`. A `404` here means the copies in
`web/public/data/` were not committed — see the next section.

## Updating the data and redeploying

The site never runs Python. It only reads the JSON files committed in `web/public/data/`, so a
data refresh is a three-step loop:

```bash
# 1. Re-run the notebook, then validate the exports
python scripts/validate_exports.py

# 2. Copy the fresh exports into the site
cp export/*.json web/public/data/          # macOS / Linux
Copy-Item export\*.json web\public\data\ -Force   # Windows PowerShell

# 3. Commit and push — Vercel rebuilds automatically
git add web/public/data
git commit -m "data: refresh exports"
git push
```

Do not skip step 2 and expect the deployment to pick up `export/*.json`. Only
`web/public/data/` is inside the Next.js project, and only files under it are published.

If a redeploy seems to show old numbers, confirm the copies were committed
(`git log -1 --stat`), then redeploy from **Deployments → … → Redeploy** with the build cache
cleared. Browser caching is not usually the culprit, because Vercel serves static files with
revalidation rather than a long-lived cache.

## Custom domain (optional)

**Project → Settings → Domains → Add**, enter your domain, and add the DNS records Vercel shows
in the dialog — typically an `A` record for the apex and a `CNAME` for `www`. Do not copy record
values from an old blog post; Vercel's dialog is authoritative. HTTPS is provisioned
automatically once the records resolve.

Because the site is served from the domain root, no `basePath` change is needed. (GitHub Pages
project sites are the case that needs one — see the main README.)

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Build fails with "No package.json found" or "Couldn't find any `pages` or `app` directory" | Root Directory left at the repository root | Set **Root Directory** to `web` and redeploy |
| Build succeeds, every route returns `404` | Output directory is wrong for a static export | Set Output Directory to `out`; if you are deploying from a config outside the dashboard, add `web/vercel.json` |
| All routes 200 but `/data/stats.json` is `404` | `web/public/data/*.json` not committed | Copy the exports, commit `web/public/data/`, push |
| Numbers or charts are stale after a data refresh | Exports updated in `export/` but not copied into `web/public/data/` | Repeat the copy step, commit, redeploy |
| Build error mentioning the Node.js version | Project pinned to an old runtime | **Settings → General → Node.js Version** → 22.x, then redeploy |
| Framework preset is "Other" and the build command is empty | Detection missed `web/` | Set Framework Preset to Next.js and Build Command to `npm run build` |
| `/recommend` shows a redirect in the address bar | Expected: `trailingSlash: true` | Nothing to fix; links in the site already include the slash |
| Deployment is fine locally but blank on Vercel | Assets requested from a path that assumed a subdirectory | Confirm no `basePath` is set in `next.config.ts`; Vercel serves from the root |

## Rolling back

**Deployments →** pick an earlier successful deployment **→ Promote to Production**. This is
instant and needs no rebuild, so it is the fastest response to a bad data push.

## What this deployment does not do

- It does not run the notebook, Apriori or FP-Growth. Those are offline, in the repository.
- It does not refresh data on a schedule. Refresh is a manual commit, as above.
- It uses no serverless functions, so it stays inside the Hobby plan's free allowances and cold
  starts are not a concern.
- It stores no state and collects no analytics.

For the site's local run instructions see [`web/README.md`](../web/README.md); for the mining
pipeline and the data contract, see the [main README](../README.md).
