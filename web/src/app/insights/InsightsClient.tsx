"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ErrorState, LoadingState } from "@/components/States";
import {
  formatInteger,
  formatSeconds,
} from "@/lib/data";
import type { Stats } from "@/lib/types";
import { useJson } from "@/lib/useJson";

const axis = {
  stroke: "var(--color-muted)",
  tick: { fill: "var(--color-muted)", fontSize: 12 },
  tickLine: false,
};

function ChartTooltip({
  active,
  payload,
  label,
  unit,
}: {
  active?: boolean;
  payload?: { value?: number | string; name?: string }[];
  label?: string | number;
  unit: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="chart-tooltip">
      <p>{label}</p>
      <p className="num">
        {typeof payload[0].value === "number"
          ? formatInteger(payload[0].value)
          : payload[0].value}{" "}
        {unit}
      </p>
    </div>
  );
}

export function InsightsClient() {
  const { data, loading, error, retry } = useJson<Stats>("/data/stats.json");

  if (loading) {
    return (
      <div className="container">
        <LoadingState label="Reading the statistics export" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  if (!data) return null;

  const topItems = data.top_items;
  const basketSizes = data.basket_size_distribution.filter(
    (row) => row.size <= 20,
  );
  const algorithmRows = [
    { name: "Apriori", seconds: data.algorithm_comparison.apriori.runtime_sec },
    {
      name: "FP-Growth",
      seconds: data.algorithm_comparison.fpgrowth.runtime_sec,
    },
  ];

  return (
    <>
      <dl className="insight-figures">
        <div>
          <dt>Transactions</dt>
          <dd className="num">{formatInteger(data.total_transactions)}</dd>
        </div>
        <div>
          <dt>Distinct items</dt>
          <dd className="num">{formatInteger(data.total_items)}</dd>
        </div>
        <div>
          <dt>Minimum support</dt>
          <dd className="num">{(data.parameters.min_support * 100).toFixed(2)}%</dd>
        </div>
        <div>
          <dt>Minimum confidence</dt>
          <dd className="num">
            {(data.parameters.min_confidence * 100).toFixed(0)}%
          </dd>
        </div>
      </dl>

      <div className="insights-grid">
        <section className="insight">
          <h2>What the baskets are built on</h2>
          <p className="lead">
            The fifteen most purchased items. A long head of staples makes them
            easy to recommend and easy to support.
          </p>
          <div className="chart-frame chart-frame--tall">
            <ResponsiveContainer width="100%" height={430}>
              <BarChart
                data={topItems}
                layout="vertical"
                margin={{ top: 4, right: 16, bottom: 4, left: 8 }}
              >
                <CartesianGrid
                  horizontal={false}
                  stroke="var(--color-rule)"
                />
                <XAxis type="number" {...axis} />
                <YAxis
                  type="category"
                  dataKey="item"
                  width={140}
                  {...axis}
                  tick={{ fill: "var(--color-ink-2)", fontSize: 12 }}
                />
                <Tooltip
                  cursor={{ fill: "var(--color-paper-2)" }}
                  content={<ChartTooltip unit="purchase lines" />}
                />
                <Bar
                  dataKey="count"
                  fill="var(--color-accent)"
                  barSize={12}
                  radius={[0, 2, 2, 0]}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="chart-caption">
            Counts are purchase lines after cleaning, from stats.json.
          </p>
        </section>

        <section className="insight">
          <h2>A year of shopping</h2>
          <p className="lead">
            Purchase lines per month. The series is steady rather than seasonal,
            which is one reason the rules ignore time.
          </p>
          <div className="chart-frame chart-frame--tall">
            <ResponsiveContainer width="100%" height={430}>
              <LineChart
                data={data.monthly_counts}
                margin={{ top: 12, right: 16, bottom: 4, left: 0 }}
              >
                <CartesianGrid
                  vertical={false}
                  stroke="var(--color-rule)"
                />
                <XAxis
                  dataKey="month"
                  {...axis}
                  interval={3}
                  tickFormatter={(value: string) => value.slice(2)}
                />
                <YAxis
                  {...axis}
                  width={56}
                  tickFormatter={(value: number) => formatInteger(value)}
                />
                <Tooltip content={<ChartTooltip unit="purchase lines" />} />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="var(--color-accent)"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="chart-caption">
            Axis labels shorten 2017-01 to 17-01. Every month from January 2017 to
            January 2018 is present.
          </p>
        </section>

        <section className="insight">
          <h2>How big is a basket?</h2>
          <p className="lead">
            Most trips carry one to five distinct categories. Baskets are counted
            once and repeated items collapse into a set.
          </p>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={basketSizes}
                margin={{ top: 12, right: 16, bottom: 8, left: 0 }}
              >
                <CartesianGrid
                  vertical={false}
                  stroke="var(--color-rule)"
                />
                <XAxis dataKey="size" {...axis} />
                <YAxis
                  {...axis}
                  width={56}
                  tickFormatter={(value: number) => formatInteger(value)}
                />
                <Tooltip
                  cursor={{ fill: "var(--color-paper-2)" }}
                  content={<ChartTooltip unit="baskets" />}
                  labelFormatter={(label) => `${label} items`}
                />
                <Bar
                  dataKey="count"
                  fill="var(--color-accent)"
                  barSize={18}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="chart-caption">
            The chart shows baskets up to 20 categories. Longer visits exist (the
            longest is 73) but hold only a handful of baskets each.
          </p>
        </section>

        <section className="insight">
          <h2>Two algorithms, one answer</h2>
          <p className="lead">
            Apriori and FP-Growth returned identical itemsets. On 294 categories,
            Apriori&rsquo;s simpler counting won on time.
          </p>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={algorithmRows}
                layout="vertical"
                margin={{ top: 12, right: 32, bottom: 8, left: 8 }}
              >
                <CartesianGrid
                  horizontal={false}
                  stroke="var(--color-rule)"
                />
                <XAxis
                  type="number"
                  {...axis}
                  tickFormatter={(value: number) => `${value}s`}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={96}
                  {...axis}
                  tick={{ fill: "var(--color-ink-2)", fontSize: 12 }}
                />
                <Tooltip
                  cursor={{ fill: "var(--color-paper-2)" }}
                  content={<ChartTooltip unit="seconds" />}
                />
                <Bar
                  dataKey="seconds"
                  barSize={22}
                  radius={[0, 2, 2, 0]}
                  isAnimationActive={false}
                >
                  {algorithmRows.map((row, index) => (
                    <Cell
                      key={row.name}
                      fill={
                        index === 0
                          ? "var(--color-accent)"
                          : "var(--color-muted)"
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="chart-caption">
            {formatInteger(data.algorithm_comparison.apriori.itemsets)} itemsets
            each. Apriori {formatSeconds(data.algorithm_comparison.apriori.runtime_sec)},
            FP-Growth{" "}
            {formatSeconds(data.algorithm_comparison.fpgrowth.runtime_sec)}.
            {data.algorithm_comparison.identical_results
              ? " Results are identical."
              : " Results differ."}
          </p>
        </section>
      </div>
    </>
  );
}
