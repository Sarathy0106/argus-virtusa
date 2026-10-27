export function fmtInt(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString("en-IN");
}

export function fmtPct(n: number | null | undefined, digits = 2): string {
  if (n === null || n === undefined) return "—";
  return `${n.toFixed(digits)}%`;
}

export function fmtMs(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return `${n.toFixed(3)} ms`;
}

export function shortHash(h: string | null | undefined, len = 10): string {
  if (!h) return "—";
  if (h.length <= len * 2) return h;
  return `${h.slice(0, len)}…${h.slice(-len)}`;
}
