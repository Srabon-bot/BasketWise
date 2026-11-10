import type { Metadata } from "next";
import { NotebookClient } from "./NotebookClient";

export const metadata: Metadata = {
  title: "Methodology",
  description:
    "How the BasketWise notebook cleans the groceries data, builds baskets, mines rules with Apriori and FP-Growth, and exports the JSON the site reads.",
};

export default function Page() {
  return (
    <>
      <section className="page-head">
        <div className="container">
          <h1>The notebook is the method</h1>
          <p className="lead">
            Cleaning, thresholds, one worked rule and the four exports. The
            notebook remains the source.
          </p>
        </div>
      </section>
      <div className="page-body">
        <div className="container">
          <NotebookClient />
        </div>
      </div>
    </>
  );
}
