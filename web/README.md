# ARGUS v2 — Mission Control (Next.js)

The frontend for ARGUS v2. It renders **only** values computed by the FastAPI
gateway (the TRUTH RULE). No pipeline logic runs here; no result values are
hardcoded.

## Develop

```bash
pnpm install
pnpm dev            # http://localhost:3000  (proxies /api/* -> :8000)
```

The gateway must be running on `http://localhost:8000` (see root `Makefile`:
`make api`). Dev requests to `/api/*` and `/health` are proxied there by
`next.config.ts`.

## Generate API types

```bash
pnpm gen:types      # openapi-typescript from the live gateway -> lib/types.generated.ts
```

## Structure (Part 4)

- `app/` — App Router pages (Mission Control home + feature pages added in R4)
- `components/shell/` — TruthBadge, Panel (four-state wrapper), shell chrome
- `lib/` — `api.ts`, `meta.ts`, `schemas.ts` (zod), `types.generated.ts`
- `styles/` — `globals.css`, `tokens.css` (mirrors `ui/theme/tokens.json`)
- `e2e/` — Playwright specs (added in R5)
