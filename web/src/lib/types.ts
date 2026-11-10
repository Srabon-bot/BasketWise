export type Rule = {
  antecedents: string[];
  consequents: string[];
  support: number;
  confidence: number;
  lift: number;
};

export type Recommendation = {
  item: string;
  confidence: number;
  lift: number;
  support: number;
};

export type RecommendationMap = Record<string, Recommendation[]>;

export type Item = {
  item: string;
  count: number;
};

export type AlgorithmBlock = {
  itemsets: number;
  runtime_sec: number;
};

export type Stats = {
  total_transactions: number;
  total_items: number;
  total_members: number;
  date_range: { start: string; end: string };
  top_items: Item[];
  monthly_counts: { month: string; count: number }[];
  basket_size_distribution: { size: number; count: number }[];
  algorithm_comparison: {
    apriori: AlgorithmBlock;
    fpgrowth: AlgorithmBlock;
    identical_results: boolean;
  };
  parameters: { min_support: number; min_confidence: number };
  data_source: "real" | "synthetic";
};
