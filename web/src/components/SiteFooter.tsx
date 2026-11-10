import Link from "next/link";
import { NOTEBOOK_URL, REPO_URL } from "@/lib/data";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="container footer-inner">
        <div>
          <p className="footer-wordmark">BasketWise</p>
          <p className="footer-note">
            A CSE 426 Data Mining and Warehouse Lab project by Md. Shahriar
            Hossain Srabon. The notebook mines the baskets; this site reads what
            it exported.
          </p>
        </div>
        <div className="footer-col">
          <h2>Pages</h2>
          <ul>
            <li>
              <Link href="/recommend" prefetch={false}>Recommender</Link>
            </li>
            <li>
              <Link href="/rules" prefetch={false}>Rule explorer</Link>
            </li>
            <li>
              <Link href="/insights" prefetch={false}>Insights</Link>
            </li>
            <li>
              <Link href="/notebook" prefetch={false}>Methodology</Link>
            </li>
          </ul>
        </div>
        <div className="footer-col">
          <h2>Project</h2>
          <ul>
            <li>
              <a href={NOTEBOOK_URL} target="_blank" rel="noreferrer">
                Notebook on GitHub
              </a>
            </li>
            <li>
              <a href={REPO_URL} target="_blank" rel="noreferrer">
                Source repository
              </a>
            </li>
            <li>
              <a
                href="https://www.kaggle.com/datasets/heeraldedhia/groceries-dataset"
                target="_blank"
                rel="noreferrer"
              >
                Kaggle Groceries Dataset
              </a>
            </li>
          </ul>
        </div>
      </div>
      <div className="container footer-bottom">
        <p>
          Built with Next.js. Data is read from four JSON files in{" "}
          <span className="num">public/data</span>.
        </p>
      </div>
    </footer>
  );
}
