"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Inbox,
  ListChecks,
  Code2,
  Network,
  BarChart3,
  ShieldCheck,
  Rocket,
  FileLock2,
} from "lucide-react";

const NAV = [
  { href: "/", label: "Mission Control", icon: LayoutDashboard },
  { href: "/inbox", label: "Inbox", icon: Inbox },
  { href: "/obligations", label: "Obligations", icon: ListChecks },
  { href: "/studio", label: "Rule Studio", icon: Code2 },
  { href: "/mesh", label: "Agent Mesh", icon: Network },
  { href: "/impact", label: "Impact", icon: BarChart3 },
  { href: "/approvals", label: "Approvals", icon: ShieldCheck },
  { href: "/rollout", label: "Rollout", icon: Rocket },
  { href: "/audit", label: "Audit", icon: FileLock2 },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Primary"
      className="flex w-[264px] shrink-0 flex-col gap-1 border-r border-border bg-surface p-4"
    >
      <div className="mb-4 px-2">
        <span className="font-heading text-lg font-bold text-text">
          ARGUS <span className="text-primary">v2</span>
        </span>
        <p className="text-xs text-muted">Regulatory Mission Control</p>
      </div>
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-3 rounded-btn px-3 py-2 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-primary ${
              active
                ? "bg-elevated text-text"
                : "text-muted hover:bg-elevated hover:text-text"
            }`}
            aria-current={active ? "page" : undefined}
          >
            <Icon size={16} className={active ? "text-primary" : ""} aria-hidden />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
