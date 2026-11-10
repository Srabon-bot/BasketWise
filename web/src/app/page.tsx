import type { Metadata } from "next";
import { HomeClient } from "./HomeClient";

export const metadata: Metadata = {
  title: "Grocery basket recommender",
};

export default function Page() {
  return <HomeClient />;
}
