"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./ThemeToggle";

const links = [
  { href: "/recommend", label: "Recommender" },
  { href: "/rules", label: "Rules" },
  { href: "/insights", label: "Insights" },
  { href: "/notebook", label: "Notebook" },
];

export function SiteNav() {
  const pathname = usePathname();

  return (
    <header className="site-nav">
      <div className="container nav-inner">
        <Link href="/" className="wordmark" aria-label="BasketWise home" prefetch={false}>
          BasketWise <span>CSE 426</span>
        </Link>
        <div className="nav-cluster">
          <nav aria-label="Main">
            <ul className="nav-links">
              {links.map((link) => {
                const active =
                  pathname === link.href || pathname === `${link.href}/`;
                return (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      prefetch={false}
                      aria-current={active ? "page" : undefined}
                    >
                      {link.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
