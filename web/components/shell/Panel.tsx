"use client";

import { type ReactNode } from "react";

// Every UI panel has four states (Part 2 rule 7): loading skeleton, empty,
// error with retry, and live data. This wrapper standardizes them.

export type PanelState = "loading" | "empty" | "error" | "live";

export function Panel({
  state,
  title,
  onRetry,
  emptyLabel = "Nothing to show yet.",
  errorLabel = "Could not load data.",
  children,
}: {
  state: PanelState;
  title?: string;
  onRetry?: () => void;
  emptyLabel?: string;
  errorLabel?: string;
  children?: ReactNode;
}) {
  return (
    <section className="rounded-card border border-border bg-surface p-5">
      {title ? (
        <h2 className="mb-4 font-heading text-xl font-semibold text-text">
          {title}
        </h2>
      ) : null}

      {state === "loading" && (
        <div
          data-testid="panel-loading"
          className="space-y-3"
          aria-busy="true"
          aria-live="polite"
        >
          <div className="h-4 w-1/2 animate-pulse rounded bg-elevated" />
          <div className="h-4 w-3/4 animate-pulse rounded bg-elevated" />
          <div className="h-4 w-2/3 animate-pulse rounded bg-elevated" />
        </div>
      )}

      {state === "empty" && (
        <p data-testid="panel-empty" className="text-sm text-muted">
          {emptyLabel}
        </p>
      )}

      {state === "error" && (
        <div data-testid="panel-error" className="space-y-3">
          <p className="text-sm text-danger">{errorLabel}</p>
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="rounded-btn border border-border bg-elevated px-4 py-2 text-sm font-medium text-text hover:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
            >
              Retry
            </button>
          ) : null}
        </div>
      )}

      {state === "live" && <div data-testid="panel-live">{children}</div>}
    </section>
  );
}
