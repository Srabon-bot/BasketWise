import type { Recommendation, Rule } from "./types";

export const REPO_URL = "https://github.com/Srabon-bot/BasketWise";
export const NOTEBOOK_URL =
  "https://github.com/Srabon-bot/BasketWise/blob/main/notebooks/grocery_basket_recommender.ipynb";

const integerFormat = new Intl.NumberFormat("en-US");

export function formatInteger(value: number): string {
  return integerFormat.format(value);
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function formatLift(value: number): string {
  return value.toFixed(2);
}

export function formatSeconds(value: number): string {
  return `${value.toFixed(2)} s`;
}

export function ruleSide(items: string[]): string {
  return items.join(" + ");
}

export function ruleSentence(rule: Rule): string {
  return `${ruleSide(rule.antecedents)} implies ${ruleSide(rule.consequents)}`;
}

/**
 * Basket mode: keep rules whose entire antecedent is in the basket,
 * exclude anything the shopper already has, and rank by lift then confidence.
 */
export function recommendForBasket(
  rules: Rule[],
  basket: string[],
  topN = 5,
): Recommendation[] {
  const chosen = new Set(basket);
  const seen = new Set<string>();
  const matches: Recommendation[] = [];

  for (const rule of rules) {
    if (rule.consequents.length !== 1) continue;
    if (!rule.antecedents.every((item) => chosen.has(item))) continue;

    const item = rule.consequents[0];
    if (chosen.has(item) || seen.has(item)) continue;

    seen.add(item);
    matches.push({
      item,
      confidence: rule.confidence,
      lift: rule.lift,
      support: rule.support,
    });
  }

  return matches
    .sort((a, b) => b.lift - a.lift || b.confidence - a.confidence)
    .slice(0, topN);
}
