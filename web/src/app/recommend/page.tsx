import type { Metadata } from "next";
import { RecommendClient } from "./RecommendClient";

export const metadata: Metadata = {
  title: "Recommender",
  description:
    "Look up a grocery item or build a small basket and read the association rules that recommend what to add next.",
};

export default function Page() {
  return (
    <>
      <section className="page-head">
        <div className="container">
          <h1>What leaves with it?</h1>
          <p className="lead">
            Pick one product or build a small basket. Every card is a mined rule.
          </p>
        </div>
      </section>
      <div className="page-body">
        <div className="container">
          <RecommendClient />
        </div>
      </div>
    </>
  );
}
