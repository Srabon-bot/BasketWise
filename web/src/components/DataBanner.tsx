"use client";

import Link from "next/link";
import { useJson } from "@/lib/useJson";
import type { Stats } from "@/lib/types";

export function DataBanner() {
  const { data } = useJson<Stats>("/data/stats.json");

  if (data?.data_source !== "synthetic") return null;

  return (
    <div className="demo-banner">
      <div className="container">
        <strong>Demo data.</strong>
        <span>
          This site is showing the synthetic stand-in, not the Kaggle file.
        </span>
        <Link href="/notebook#data-source" prefetch={false}>
          How to run the real data
        </Link>
      </div>
    </div>
  );
}
