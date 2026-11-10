import type { Metadata } from "next";
import { InsightsClient } from "./InsightsClient";

export const metadata: Metadata = {
  title: "Insights",
  description:
    "Charts drawn from the notebook's statistics export: top items, monthly purchases, basket sizes and the Apriori versus FP-Growth comparison.",
};

export default function Page() {
  return (
    <>
      <section className="page-head">
        <div className="container">
          <h1>The shape of the data</h1>
          <p className="lead">
            Four figures from the recommender&rsquo;s export, showing what the
            rules rest on.
          </p>
        </div>
      </section>
      <div className="page-body">
        <div className="container">
          <InsightsClient />
        </div>
      </div>
    </>
  );
}
