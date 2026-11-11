import type { Metadata } from "next";
import { RulesClient } from "./RulesClient";

export const metadata: Metadata = {
  title: "Rules",
  description:
    "Sort and filter the association rules the notebook exported: antecedent, consequent, support, confidence and lift.",
};

export default function Page() {
  return (
    <>
      <section className="page-head">
        <div className="container">
          <h1>The rule ledger</h1>
          <p className="lead">
            Every exported rule with the numbers that judge it. Sort a column or
            filter the list.
          </p>
        </div>
      </section>
      <div className="page-body">
        <div className="container">
          <RulesClient />
          <div className="prose-note">
            <h2>Reading the columns</h2>
            <p>
              <strong>Support</strong> is the share of all baskets containing the
              whole rule. <strong>Confidence</strong> is the share of baskets with
              the antecedent that also contain the consequent.{" "}
              <strong>Lift</strong> compares that confidence with the
              consequent&rsquo;s normal popularity: 1 means no association, above
              1 means the two items appear together more often than chance.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
