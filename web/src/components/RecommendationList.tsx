import type { Recommendation } from "@/lib/types";
import { formatLift, formatPercent } from "@/lib/data";

type Props = {
  recommendations: Recommendation[];
  source: string;
  basketMode?: boolean;
};

export function RecommendationList({
  recommendations,
  source,
  basketMode = false,
}: Props) {
  return (
    <ol className="rec-list">
      {recommendations.map((rec) => (
        <li className="rec-row" key={rec.item}>
          <div className="rec-main">
            <p className="rec-item">{rec.item}</p>
            <p className="rec-why">
              {basketMode
                ? `${formatPercent(rec.confidence)} of baskets with this combination also had ${rec.item}.`
                : `${formatPercent(rec.confidence)} of baskets with ${source} also had ${rec.item}.`}
            </p>
            <div className="rec-meter" aria-hidden="true">
              <span style={{ width: `${Math.round(rec.confidence * 100)}%` }} />
            </div>
          </div>
          <div className="rec-figures rec-confidence">
            <p className="rec-figure">{formatPercent(rec.confidence)}</p>
            <p className="rec-label">confidence</p>
          </div>
          <div className="rec-figures rec-lift">
            <p className="rec-figure">{formatLift(rec.lift)}</p>
            <p className="rec-label">lift</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
