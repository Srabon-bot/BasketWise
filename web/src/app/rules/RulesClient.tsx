"use client";

import { useMemo, useState } from "react";
import { ErrorState, LoadingState } from "@/components/States";
import {
  formatInteger,
  formatLift,
  formatPercent,
  ruleSide,
} from "@/lib/data";
import type { Rule } from "@/lib/types";
import { useJson } from "@/lib/useJson";

type SortKey = "rule" | "support" | "confidence" | "lift";
type Direction = "asc" | "desc";

const PAGE_SIZE = 20;
const DEFAULT_CONFIDENCE = 10;
const DEFAULT_LIFT = 1;

const columns: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: "rule", label: "Rule", numeric: false },
  { key: "support", label: "Support", numeric: true },
  { key: "confidence", label: "Confidence", numeric: true },
  { key: "lift", label: "Lift", numeric: true },
];

function ruleKey(rule: Rule): string {
  return `${rule.antecedents.join("|")}=>${rule.consequents.join("|")}`;
}

export function RulesClient() {
  const { data, loading, error, retry } = useJson<Rule[]>("/data/rules.json");

  const [query, setQuery] = useState("");
  const [minConfidence, setMinConfidence] = useState(DEFAULT_CONFIDENCE);
  const [minLift, setMinLift] = useState(DEFAULT_LIFT);
  const [sort, setSort] = useState<SortKey>("lift");
  const [direction, setDirection] = useState<Direction>("desc");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    if (!data) return [];
    const needle = query.trim().toLowerCase();
    const rows = data.filter((rule) => {
      if (rule.confidence * 100 < minConfidence) return false;
      if (rule.lift < minLift) return false;
      if (!needle) return true;
      return [...rule.antecedents, ...rule.consequents].some((item) =>
        item.includes(needle),
      );
    });

    const factor = direction === "asc" ? 1 : -1;
    rows.sort((a, b) => {
      if (sort === "rule") {
        const aText = `${a.antecedents.join(" ")} ${a.consequents.join(" ")}`;
        const bText = `${b.antecedents.join(" ")} ${b.consequents.join(" ")}`;
        return factor * aText.localeCompare(bText);
      }
      return factor * (a[sort] - b[sort]);
    });
    return rows;
  }, [data, query, minConfidence, minLift, sort, direction]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const start = (currentPage - 1) * PAGE_SIZE;
  const visible = filtered.slice(start, start + PAGE_SIZE);

  const maxLift = useMemo(() => {
    if (!data?.length) return 24;
    return Math.max(1, Math.ceil(Math.max(...data.map((rule) => rule.lift))));
  }, [data]);

  function applySort(key: SortKey) {
    if (key === sort) {
      setDirection((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSort(key);
      setDirection(key === "rule" ? "asc" : "desc");
    }
    setPage(1);
  }

  function reset() {
    setQuery("");
    setMinConfidence(DEFAULT_CONFIDENCE);
    setMinLift(DEFAULT_LIFT);
    setSort("lift");
    setDirection("desc");
    setPage(1);
  }

  if (loading) {
    return (
      <div className="container">
        <LoadingState label="Reading the exported rules" />
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

  return (
    <div className="rules-page">
      <div className="rules-controls">
        <div className="field">
          <label htmlFor="rule-search">Filter by item</label>
          <input
            id="rule-search"
            type="search"
            value={query}
            placeholder="cheese, pasta, milk…"
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(1);
            }}
          />
          <p className="field-help">
            Matches either side of the rule. Case does not matter.
          </p>
        </div>

        <div className="field">
          <label htmlFor="rule-confidence">Minimum confidence</label>
          <div className="range-row">
            <input
              id="rule-confidence"
              type="range"
              min={10}
              max={100}
              step={5}
              value={minConfidence}
              aria-valuetext={`${minConfidence} percent`}
              onChange={(event) => {
                setMinConfidence(Number(event.target.value));
                setPage(1);
              }}
            />
            <output className="range-value" htmlFor="rule-confidence">
              {minConfidence}%
            </output>
          </div>
        </div>

        <div className="field">
          <label htmlFor="rule-lift">Minimum lift</label>
          <div className="range-row">
            <input
              id="rule-lift"
              type="range"
              min={DEFAULT_LIFT}
              max={maxLift}
              step={0.5}
              value={minLift}
              aria-valuetext={`${minLift.toFixed(1)}`}
              onChange={(event) => {
                setMinLift(Number(event.target.value));
                setPage(1);
              }}
            />
            <output className="range-value" htmlFor="rule-lift">
              {minLift.toFixed(1)}
            </output>
          </div>
        </div>
      </div>

      <div className="rules-summary" role="status" aria-live="polite">
        <p>
          <span className="num">{formatInteger(filtered.length)}</span> of{" "}
          {formatInteger(data?.length ?? 0)} rules match. Sorted by{" "}
          {sort === "rule" ? "item name" : sort},{" "}
          {direction === "asc" ? "ascending" : "descending"}. Page{" "}
          {currentPage} of {totalPages}.
        </p>
        <button type="button" className="btn btn--small" onClick={reset}>
          Reset filters
        </button>
      </div>

      {visible.length === 0 ? (
        <div className="rules-empty">
          <p>
            No rule survives these filters. Lower the minimum confidence or lift,
            or clear the item filter.
          </p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="rules-table">
            <caption className="visually-hidden">
              Association rules with support, confidence and lift
            </caption>
            <thead>
              <tr>
                {columns.map((column) => {
                  const active = sort === column.key;
                  const ariaSort = active
                    ? direction === "asc"
                      ? "ascending"
                      : "descending"
                    : "none";
                  return (
                    <th
                      key={column.key}
                      scope="col"
                      aria-sort={ariaSort}
                      className={column.numeric ? "num" : undefined}
                    >
                      <button type="button" onClick={() => applySort(column.key)}>
                        {column.label}
                        <span className="sort-mark" aria-hidden="true">
                          {active ? (direction === "asc" ? "↑" : "↓") : "·"}
                        </span>
                      </button>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {visible.map((rule) => (
                <tr key={ruleKey(rule)}>
                  <td data-label="Rule">
                    <span className="rule-side rule-antecedent">
                      {ruleSide(rule.antecedents)}
                    </span>
                    <span className="rule-arrow" aria-hidden="true">
                      →
                    </span>
                    <span className="rule-side rule-consequent">
                      {ruleSide(rule.consequents)}
                    </span>
                  </td>
                  <td className="num" data-label="Support">
                    {formatPercent(rule.support)}
                  </td>
                  <td className="num" data-label="Confidence">
                    {formatPercent(rule.confidence)}
                  </td>
                  <td className="num" data-label="Lift">
                    {formatLift(rule.lift)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="pagination">
        <p>
          Showing{" "}
          <span className="num">
            {filtered.length === 0 ? 0 : start + 1} to{" "}
            {Math.min(start + PAGE_SIZE, filtered.length)}
          </span>{" "}
          of <span className="num">{formatInteger(filtered.length)}</span>
        </p>
        <div className="pagination-actions">
          <button
            type="button"
            className="btn btn--small"
            onClick={() => setPage((value) => Math.max(1, value - 1))}
            disabled={currentPage === 1}
          >
            Previous
          </button>
          <button
            type="button"
            className="btn btn--small"
            onClick={() =>
              setPage((value) => Math.min(totalPages, value + 1))
            }
            disabled={currentPage === totalPages}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
