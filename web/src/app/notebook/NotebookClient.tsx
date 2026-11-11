"use client";

import { ErrorState, LoadingState } from "@/components/States";
import {
  formatInteger,
  formatLift,
  formatPercent,
  formatSeconds,
  NOTEBOOK_URL,
  ruleSide,
} from "@/lib/data";
import type { Item, RecommendationMap, Rule, Stats } from "@/lib/types";
import { useJson } from "@/lib/useJson";

const sections = [
  { id: "division", label: "Notebook and site" },
  { id: "cleaning", label: "Cleaning" },
  { id: "baskets", label: "Baskets and thresholds" },
  { id: "worked-example", label: "A worked rule" },
  { id: "algorithms", label: "Apriori and FP-Growth" },
  { id: "exports", label: "The four exports" },
  { id: "data-source", label: "Real or demo data" },
  { id: "limits", label: "Limits and next steps" },
  { id: "run", label: "Run it yourself" },
];

export function NotebookClient() {
  const statsState = useJson<Stats>("/data/stats.json");
  const rulesState = useJson<Rule[]>("/data/rules.json");
  const recsState = useJson<RecommendationMap>("/data/recommendations.json");
  const itemsState = useJson<Item[]>("/data/items.json");

  const stats = statsState.data;
  const rules = rulesState.data;
  const recs = recsState.data;
  const items = itemsState.data;

  if (statsState.loading) {
    return (
      <div className="container">
        <LoadingState label="Reading the notebook's exports" />
      </div>
    );
  }

  if (statsState.error) {
    return (
      <div className="container">
        <ErrorState message={statsState.error} onRetry={statsState.retry} />
      </div>
    );
  }

  const example = rules?.[0];
  const exampleBaskets =
    example && stats
      ? Math.round(example.support * stats.total_transactions)
      : null;

  return (
    <div className="prose-layout">
      <aside className="prose-aside">
        <p>
          The executed notebook is the deliverable. This page is the short version
          for a reader who wants the method without the plots.
        </p>
        <nav aria-label="On this page">
          <ul>
            {sections.map((section) => (
              <li key={section.id}>
                <a href={`#${section.id}`}>{section.label}</a>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      <div className="prose">
        <section id="division">
          <h2>One pipeline, two roles</h2>
          <p>
            <span className="num">grocery_basket_recommender.ipynb</span> is where
            every decision is made: reading the CSV, cleaning it, building baskets,
            running Apriori and FP-Growth, generating rules and ranking
            recommendations. It writes four JSON files.
          </p>
          <p>
            This site performs no mining. Each page fetches those files from{" "}
            <span className="num">/data</span> in the browser and renders them.
            Re-run the notebook, copy the exports, and the site follows.
          </p>
        </section>

        <section id="cleaning">
          <h2>Cleaning before counting</h2>
          <p>
            The raw file has one row per item on a receipt. The notebook applies
            the same cleaning it would use on a raw retail export:
          </p>
          <ul>
            <li>
              reads <span className="num">?</span>, <span className="num">n/a</span>,{" "}
              <span className="num">missing</span>, <span className="num">--</span>,{" "}
              <span className="num">NULL</span> and empty strings as missing, then
              drops rows with no member, date or item;
            </li>
            <li>removes exact duplicate rows, but keeps genuine repeat purchases;</li>
            <li>
              trims, lowercases and collapses whitespace in item names so
              near-duplicates do not split the counts;
            </li>
            <li>
              parses dates day-first, then adds <span className="num">Year</span>{" "}
              and <span className="num">Month</span>.
            </li>
          </ul>
          <p>
            The result for this export is{" "}
            <strong>
              {stats ? formatInteger(stats.total_transactions) : "…"} baskets
            </strong>{" "}
            over{" "}
            <strong>{stats ? formatInteger(stats.total_items) : "…"} items</strong>{" "}
            and{" "}
            <strong>
              {stats ? formatInteger(stats.total_members) : "…"} members
            </strong>
            , from {stats?.date_range.start} to {stats?.date_range.end}.
          </p>
        </section>

        <section id="baskets">
          <h2>One member, one date, one basket</h2>
          <p>
            A basket is everything the same member bought on the same date. Repeated
            lines of one product collapse into a single item, because buying two
            loaves is not a new association. The baskets are one-hot encoded into a
            boolean matrix, which is the input both mining algorithms expect.
          </p>
          <p>
            Support and confidence are the two filters. The notebook starts at
            support <span className="num">0.01</span> and confidence{" "}
            <span className="num">0.1</span>; if the rule set is empty or larger
            than 5,000 rows, a safety loop moves support until it is readable. This
            run settled at{" "}
            <strong className="num">
              {stats ? formatPercent(stats.parameters.min_support) : "…"}
            </strong>{" "}
            support and{" "}
            <strong className="num">
              {stats ? formatPercent(stats.parameters.min_confidence) : "…"}
            </strong>{" "}
            confidence. Both values are written to{" "}
            <span className="num">stats.json</span>, and the tuning table is in the
            notebook.
          </p>
        </section>

        <section id="worked-example">
          <h2>A worked rule</h2>
          {example && stats ? (
            <>
              <div className="example-rule">
                <p className="example-head">
                  {ruleSide(example.antecedents)}{" "}
                  <span aria-hidden="true">→</span>{" "}
                  {ruleSide(example.consequents)}
                </p>
                <p>
                  <strong className="num">
                    {formatPercent(example.support)}
                  </strong>{" "}
                  support: about {formatInteger(exampleBaskets ?? 0)} of the{" "}
                  {formatInteger(stats.total_transactions)} baskets contain both
                  sides.
                </p>
                <p>
                  <strong className="num">
                    {formatPercent(example.confidence)}
                  </strong>{" "}
                  confidence: when the basket has{" "}
                  {ruleSide(example.antecedents)}, it also has{" "}
                  {ruleSide(example.consequents)} about{" "}
                  {formatPercent(example.confidence)} of the time.
                </p>
                <p>
                  <strong className="num">{formatLift(example.lift)}</strong> lift.
                  The pair appears {formatLift(example.lift)} times more often than
                  independent popularity would predict. This is the strongest rule
                  in the export, sorted by lift.
                </p>
              </div>
              <p>
                Support answers &ldquo;how common is this?&rdquo;, confidence
                answers &ldquo;how reliable is the guess?&rdquo;, and lift answers
                &ldquo;is it better than guessing the consequent anyway?&rdquo;. A
                rule can have high confidence and almost no lift when the
                consequent is a staple that appears in most baskets, which is why
                the site never ranks on confidence alone.
              </p>
            </>
          ) : (
            <p>The strongest rule is being read from the export.</p>
          )}
        </section>

        <section id="algorithms">
          <h2>Apriori and FP-Growth</h2>
          <p>
            Both algorithms mined the same support threshold and returned the same{" "}
            {stats ? formatInteger(stats.algorithm_comparison.apriori.itemsets) : "…"}{" "}
            frequent itemsets. Apriori builds candidate sets and counts them;
            FP-Growth compresses baskets into an FP-tree and avoids candidate
            generation.
          </p>
          <table className="metric-table">
            <caption className="visually-hidden">
              Measured runtime and itemset count for each algorithm
            </caption>
            <thead>
              <tr>
                <th scope="col">Algorithm</th>
                <th scope="col">Itemsets</th>
                <th scope="col">Runtime</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Apriori</td>
                <td className="num">
                  {stats ? formatInteger(stats.algorithm_comparison.apriori.itemsets) : "…"}
                </td>
                <td className="num">
                  {stats
                    ? formatSeconds(stats.algorithm_comparison.apriori.runtime_sec)
                    : "…"}
                </td>
              </tr>
              <tr>
                <td>FP-Growth</td>
                <td className="num">
                  {stats ? formatInteger(stats.algorithm_comparison.fpgrowth.itemsets) : "…"}
                </td>
                <td className="num">
                  {stats
                    ? formatSeconds(
                        stats.algorithm_comparison.fpgrowth.runtime_sec,
                      )
                    : "…"}
                </td>
              </tr>
            </tbody>
          </table>
          <p>
            FP-Growth was slower here, not faster. With only 294 category columns
            and about 25,000 baskets, Apriori&rsquo;s counting is cheaper than
            building and walking the tree in Python. The textbook advantage needs
            larger, denser data; the measured numbers are reported as they came out.
          </p>
        </section>

        <section id="exports">
          <h2>The four exports</h2>
          <p>
            Every file is UTF-8 JSON, every float is rounded to four decimals, and
            sets become sorted lists so the output is stable between runs.
          </p>
          <table className="metric-table">
            <caption className="visually-hidden">
              The exported files and their contents
            </caption>
            <thead>
              <tr>
                <th scope="col">File</th>
                <th scope="col">Contents</th>
                <th scope="col">Rows</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="num">rules.json</td>
                <td>
                  The strongest rules by lift, capped at 500, with each
                  item&rsquo;s best five item-to-item rules guaranteed.
                </td>
                <td className="num">
                  {rules ? formatInteger(rules.length) : "…"}
                </td>
              </tr>
              <tr>
                <td className="num">recommendations.json</td>
                <td>
                  Each item mapped to five items that follow it, using rules whose
                  antecedent is that item alone, by lift then confidence.
                </td>
                <td className="num">
                  {recs ? formatInteger(Object.keys(recs).length) : "…"}
                </td>
              </tr>
              <tr>
                <td className="num">items.json</td>
                <td>Items that have recommendations, ordered by purchase count.</td>
                <td className="num">
                  {items ? formatInteger(items.length) : "…"}
                </td>
              </tr>
              <tr>
                <td className="num">stats.json</td>
                <td>
                  Headline counts, chart series, parameters, algorithm comparison
                  and the data-source flag.
                </td>
                <td className="num">1</td>
              </tr>
            </tbody>
          </table>
          <p>
            <span className="num">scripts/validate_exports.py</span> checks all four
            files against the contract: keys, rounding, ordering, probabilities,
            and that items and recommendations describe the same item set. It
            exits non-zero on any mismatch.
          </p>
        </section>

        <section id="data-source">
          <h2>Real or demo data</h2>
          <p>
            The notebook prefers <span className="num">data/Groceries_dataset.csv</span>,
            a product-category extract of the Complete Journey study (84.51° /
            Dunnhumby) built by{" "}
            <span className="num">scripts/fetch_completejourney.py</span>. If that
            file is absent, <span className="num">scripts/make_synthetic_data.py</span>{" "}
            builds a seeded stand-in with realistic popularity, basket sizes and
            planted co-purchases, and writes{" "}
            <span className="num">data/DATA_SOURCE.txt</span>.
          </p>
          <p>
            While that marker exists, the run is labelled{" "}
            <strong>{stats?.data_source === "synthetic" ? "synthetic" : "real"}</strong>{" "}
            in <span className="num">stats.json</span> and the site shows the demo
            banner. To switch: replace the CSV, delete the marker, re-run the
            notebook, copy the four files into{" "}
            <span className="num">web/public/data/</span>. Nothing in the site needs
            editing.
          </p>
        </section>

        <section id="limits">
          <h2>Limits and next steps</h2>
          <ul>
            <li>
              No ratings or quantities: the data records that an item was bought,
              not how much it was liked.
            </li>
            <li>
              No time awareness: a rule learned across one year may not hold this
              week.
            </li>
            <li>
              Sampled and coarse: 500 households and product categories, not
              individual SKUs, so rare products never reach the support threshold.
              That is why only{" "}
              {recs ? formatInteger(Object.keys(recs).length) : "…"} items have
              recommendations.
            </li>
            <li>
              Association is not causation: &ldquo;bought together&rdquo; does not
              mean one product causes the other.
            </li>
          </ul>
          <p>
            Natural extensions are time-aware rules, quantity weighting,
            category-level generalisation, and a hold-out evaluation of the
            recommender instead of ranking by lift alone.
          </p>
        </section>

        <section id="run">
          <h2>Run it yourself</h2>
          <pre className="code-block">
            <code>{`pip install -r requirements.txt
python scripts/build_notebook.py
python -m nbconvert --to notebook --execute --inplace notebooks/grocery_basket_recommender.ipynb
python scripts/validate_exports.py`}</code>
          </pre>
          <p>
            The executed notebook is committed with its outputs and plots, so it can
            be read without running anything. Open it on GitHub or in Jupyter.
          </p>
          <a
            className="btn btn--primary"
            href={NOTEBOOK_URL}
            target="_blank"
            rel="noreferrer"
          >
            Open the notebook on GitHub
          </a>
        </section>
      </div>
    </div>
  );
}
