"use client";

import Link from "next/link";
import type { RecommendationMap, Rule, Stats } from "@/lib/types";
import { useJson } from "@/lib/useJson";
import {
  formatInteger,
  formatLift,
  formatPercent,
  ruleSide,
} from "@/lib/data";

const pipeline = [
  {
    title: "Raw data",
    text: "One line per purchase: member, date, item.",
  },
  {
    title: "Cleaning",
    text: "Hidden missing values, duplicates and name variants removed.",
  },
  {
    title: "Baskets",
    text: "One member and one date become one transaction.",
  },
  {
    title: "Apriori and FP-Growth",
    text: "Both algorithms mine the same support threshold.",
  },
  {
    title: "Rules",
    text: "Support, confidence and lift rank every combination.",
  },
  {
    title: "Recommender",
    text: "The site reads the exported rules, never the raw CSV.",
  },
];

export function HomeClient() {
  const statsState = useJson<Stats>("/data/stats.json");
  const rulesState = useJson<Rule[]>("/data/rules.json");
  const recsState = useJson<RecommendationMap>("/data/recommendations.json");

  const stats = statsState.data;
  const rules = rulesState.data;
  const recs = recsState.data;

  const sheetItem =
    recs && recs["cheeses"] ? "cheeses" : recs ? Object.keys(recs)[0] : null;
  const sheetRec = sheetItem && recs ? recs[sheetItem]?.[0] : undefined;
  const strongest = rules?.[0];

  return (
    <>
      <section className="hero">
        <div className="container hero-grid">
          <div className="hero-copy">
            <h1>BasketWise</h1>
            <p className="lead">
              Grocery baskets, mined for what sells together.
            </p>
            <div className="hero-actions">
              <Link href="/recommend" className="btn btn--primary" prefetch={false}>
                Find a recommendation
              </Link>
              <Link href="/notebook" className="btn" prefetch={false}>
                Read the notebook
              </Link>
            </div>
          </div>

          <aside className="rule-sheet" aria-label="Sample recommendation from the exported data">
            {recsState.loading ? (
              <div className="sheet-skeleton" role="status">
                <span className="sheet-label">Reading the recommendation sheet</span>
                <span className="skeleton-line" />
                <span className="skeleton-line skeleton-line--medium" />
                <span className="skeleton-line skeleton-line--short" />
              </div>
            ) : sheetItem && sheetRec ? (
              <>
                <div className="sheet-head">
                  <p className="sheet-label">Recommendation slip</p>
                  <p className="sheet-figure">
                    lift {formatLift(sheetRec.lift)}
                  </p>
                </div>
                <div className="sheet-basket">
                  <div>
                    <p className="sheet-label">In the basket</p>
                    <ul className="sheet-basket-items">
                      <li>{sheetItem}</li>
                    </ul>
                  </div>
                </div>
                <div className="sheet-recommendation">
                  <p className="sheet-label">Also bought</p>
                  <p className="sheet-recommended">{sheetRec.item}</p>
                  <p className="sheet-explanation">
                    {formatPercent(sheetRec.confidence)} of baskets with{" "}
                    {sheetItem} also had {sheetRec.item}.
                  </p>
                </div>
                <div className="sheet-foot">
                  <span>Sample from recommendations.json</span>
                  <span>confidence {formatPercent(sheetRec.confidence)}</span>
                </div>
              </>
            ) : (
              <div className="sheet-skeleton">
                <p className="sheet-label">
                  The recommendation file is not available yet.
                </p>
                <Link href="/recommend" className="btn btn--small" prefetch={false}>
                  Open the recommender
                </Link>
              </div>
            )}
          </aside>
        </div>
      </section>

      <section className="figures-band" aria-label="Dataset at a glance">
        <div className="container">
          <dl className="figure-row">
            <div className="figure-cell">
              <dt className="figure-label">Baskets</dt>
              <dd className="figure-value">
                {stats ? formatInteger(stats.total_transactions) : "…"}
              </dd>
            </div>
            <div className="figure-cell">
              <dt className="figure-label">Items in the data</dt>
              <dd className="figure-value">
                {stats ? formatInteger(stats.total_items) : "…"}
              </dd>
            </div>
            <div className="figure-cell">
              <dt className="figure-label">Members</dt>
              <dd className="figure-value">
                {stats ? formatInteger(stats.total_members) : "…"}
              </dd>
            </div>
            <div className="figure-cell">
              <dt className="figure-label">Exported rules</dt>
              <dd className="figure-value">
                {rules ? formatInteger(rules.length) : "…"}
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="section-head">
            <h2>From receipt to rule</h2>
            <p className="lead">
              Six steps, one reproducible notebook, four JSON files the site can
              read.
            </p>
          </div>
          <ol className="pipeline">
            {pipeline.map((step, index) => (
              <li className="pipeline-step" key={step.title}>
                <p className="step-number">
                  {String(index + 1).padStart(2, "0")}
                </p>
                <div>
                  <h3>{step.title}</h3>
                  <p>{step.text}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="statement-band">
        <div className="container statement-grid">
          <div>
            <div className="statement-rule" aria-hidden="true" />
            <p className="statement-text">
              {strongest
                ? `${ruleSide(strongest.consequents)} appears in ${formatPercent(strongest.confidence)} of the baskets that hold ${ruleSide(strongest.antecedents)}.`
                : "The strongest rule is being read from the export."}
            </p>
          </div>
          <p className="statement-meta">
            {strongest ? (
              <>
                Strongest rule by lift, from the {formatInteger(rules?.length ?? 0)}{" "}
                exported rules. Lift <span className="num">{formatLift(strongest.lift)}</span>.
              </>
            ) : (
              "Ranked by lift, then confidence."
            )}
          </p>
        </div>
      </section>

      <section className="section">
        <div className="container split">
          <div className="section-head">
            <h2>The notebook is the source.</h2>
            <p className="lead">
              The website holds no mining code. It reads the four files the
              notebook writes.
            </p>
            <div className="hero-actions">
              <Link href="/notebook" className="btn" prefetch={false}>
                Read the methodology
              </Link>
            </div>
          </div>
          <ul className="method-rows">
            <li className="method-row">
              <div>
                <h3>Preprocess</h3>
                <p>Missing values, duplicates, names and day-first dates.</p>
              </div>
              <span className="num">01</span>
            </li>
            <li className="method-row">
              <div>
                <h3>Build baskets</h3>
                <p>One member on one date, one-hot encoded for mining.</p>
              </div>
              <span className="num">02</span>
            </li>
            <li className="method-row">
              <div>
                <h3>Mine and rank</h3>
                <p>Apriori and FP-Growth, timed, then ranked by lift.</p>
              </div>
              <span className="num">03</span>
            </li>
            <li className="method-row">
              <div>
                <h3>Export</h3>
                <p>Rules, recommendations, items and statistics as JSON.</p>
              </div>
              <span className="num">04</span>
            </li>
          </ul>
        </div>
      </section>

      <section className="close-band">
        <div className="container close-inner">
          <h2>Pick an item. See what leaves with it.</h2>
          <Link href="/recommend" className="btn btn--primary" prefetch={false}>
            Open the recommender
          </Link>
        </div>
      </section>
    </>
  );
}
