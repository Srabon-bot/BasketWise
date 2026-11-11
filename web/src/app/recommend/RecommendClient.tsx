"use client";

import { useMemo, useState } from "react";
import { ItemCombobox } from "@/components/ItemCombobox";
import { RecommendationList } from "@/components/RecommendationList";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/States";
import {
  formatInteger,
  formatPercent,
  recommendForBasket,
} from "@/lib/data";
import type {
  Item,
  RecommendationMap,
  Rule,
  Stats,
} from "@/lib/types";
import { useJson } from "@/lib/useJson";

type Mode = "item" | "basket";

const MAX_BASKET = 6;

export function RecommendClient() {
  const recsState = useJson<RecommendationMap>("/data/recommendations.json");
  const itemsState = useJson<Item[]>("/data/items.json");
  const rulesState = useJson<Rule[]>("/data/rules.json");
  const statsState = useJson<Stats>("/data/stats.json");

  const [mode, setMode] = useState<Mode>("item");
  const [item, setItem] = useState("cheeses");
  const [basket, setBasket] = useState<string[]>([]);

  const recs = recsState.data;
  const rules = rulesState.data;

  const itemList = useMemo(() => {
    if (itemsState.data) return itemsState.data.map((row) => row.item);
    if (recs) return Object.keys(recs).sort();
    return [];
  }, [itemsState.data, recs]);

  const basketItemList = useMemo(() => {
    if (!rules) return itemList;
    const seen = new Set<string>();
    for (const rule of rules) {
      for (const entry of rule.antecedents) seen.add(entry);
    }
    return [...seen].sort((a, b) => a.localeCompare(b));
  }, [rules, itemList]);

  const singleResults = item && recs ? recs[item] ?? [] : [];
  const basketResults = useMemo(
    () => (rules ? recommendForBasket(rules, basket) : []),
    [rules, basket],
  );

  const loading =
    recsState.loading ||
    rulesState.loading ||
    (mode === "item" && itemsState.loading);
  const error = recsState.error ?? rulesState.error ?? itemsState.error;
  const retry = () => {
    recsState.retry();
    rulesState.retry();
    itemsState.retry();
  };

  function addToBasket(next: string) {
    setBasket((current) =>
      current.includes(next) || current.length >= MAX_BASKET
        ? current
        : [...current, next],
    );
  }

  return (
    <div className="tool-layout">
      <div className="tool-panel">
        <h2>Build the basket</h2>
        <p>
          Look up one product, or assemble a small basket and let every matching
          rule vote.
        </p>

        <div className="segmented" role="group" aria-label="Recommendation mode">
          <button
            type="button"
            aria-pressed={mode === "item"}
            onClick={() => setMode("item")}
          >
            One item
          </button>
          <button
            type="button"
            aria-pressed={mode === "basket"}
            onClick={() => setMode("basket")}
          >
            Basket
          </button>
        </div>

        {mode === "item" ? (
          <ItemCombobox
            items={itemList}
            onSelect={setItem}
            label="Find an item"
            initialValue={item}
            placeholder="cheeses, pasta sauce, milk…"
          />
        ) : (
          <>
            <ItemCombobox
              items={basketItemList}
              onSelect={addToBasket}
              label="Add an item to the basket"
              clearOnSelect
              placeholder={
                basket.length >= MAX_BASKET
                  ? "Basket is full"
                  : "cheeses, pasta sauce, milk…"
              }
            />
            {basket.length > 0 ? (
              <ul className="selected-items" aria-label="Items in the basket">
                {basket.map((entry) => (
                  <li className="selected-item" key={entry}>
                    <span>{entry}</span>
                    <button
                      type="button"
                      onClick={() =>
                        setBasket((current) =>
                          current.filter((value) => value !== entry),
                        )
                      }
                      aria-label={`Remove ${entry} from the basket`}
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="tool-note">
                Add up to {MAX_BASKET} items. A recommendation only fires when a
                rule&rsquo;s whole antecedent is in the basket.
              </p>
            )}
          </>
        )}

        <p className="tool-note">
          Ranked by lift, then confidence. Items already in the basket are never
          recommended back.
        </p>
      </div>

      <div>
        {loading ? (
          <LoadingState label="Reading the recommendation tables" />
        ) : error ? (
          <ErrorState message={error} onRetry={retry} />
        ) : mode === "item" ? (
          <>
            <div className="result-head">
              <h2>
                Bought with <span className="rec-item-inline">{item}</span>
              </h2>
              <p>
                {singleResults.length > 0
                  ? `${formatInteger(singleResults.length)} recommendation${singleResults.length === 1 ? "" : "s"} from recommendations.json`
                  : "No rule reaches this item"}
              </p>
            </div>
            {singleResults.length > 0 ? (
              <RecommendationList
                recommendations={singleResults}
                source={item}
              />
            ) : (
              <EmptyState
                title="No recommendations for this item"
                action={
                  <button
                    type="button"
                    className="btn"
                    onClick={() => setItem("cheeses")}
                  >
                    Try cheeses
                  </button>
                }
              >
                This product never clears the support threshold in an
                antecedent, so the mined rules cannot say what leaves with it.
                Try a more common item.
              </EmptyState>
            )}
          </>
        ) : (
          <>
            <div className="result-head">
              <h2>What to add next</h2>
              <p>
                {basket.length === 0
                  ? "An empty basket has nothing to match"
                  : `${formatInteger(basket.length)} item${basket.length === 1 ? "" : "s"} in the basket · ${formatInteger(basketResults.length)} match${basketResults.length === 1 ? "" : "es"}`}
              </p>
            </div>
            {basketResults.length > 0 ? (
              <RecommendationList
                recommendations={basketResults}
                source={basket.join(" + ")}
                basketMode
              />
            ) : (
              <EmptyState
                title={
                  basket.length === 0
                    ? "Start with a staple"
                    : "No rule covers this basket"
                }
                action={
                  basket.length > 0 ? (
                    <button
                      type="button"
                      className="btn"
                      onClick={() => setBasket([])}
                    >
                      Clear the basket
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="btn btn--primary"
                      onClick={() =>
                        setBasket(["dry noodles/pasta", "beef"])
                      }
                    >
                      Try dry noodles and beef
                    </button>
                  )
                }
              >
                {basket.length === 0
                  ? "Cheeses, pasta sauce and fluid milk sit at the top of the data; small baskets around them match the most rules."
                  : "The rules need every antecedent item present. Remove one and try a more common combination, or start from cheeses."}
              </EmptyState>
            )}
          </>
        )}

        {!loading && !error ? (
          <div className="tool-footnote">
            <p>
              Data source: <span className="num">recommendations.json</span> for
              one item, <span className="num">rules.json</span> for a basket.
              Minimum confidence in the export is{" "}
              {statsState.data
                ? formatPercent(statsState.data.parameters.min_confidence)
                : "…"}{" "}
              and minimum support is{" "}
              {statsState.data
                ? `${(statsState.data.parameters.min_support * 100).toFixed(2)}%`
                : "…"}
              .
            </p>
            <p>
              Strongest rule currently exported:{" "}
              {rules && rules[0]
                ? `${rules[0].antecedents.join(" + ")} → ${rules[0].consequents.join(" + ")} at ${formatPercent(rules[0].confidence)} confidence.`
                : "reading…"}
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
