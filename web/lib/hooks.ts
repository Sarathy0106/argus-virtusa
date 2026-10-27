"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "./api";
import { fetchMeta } from "./meta";

export function useMeta() {
  return useQuery({ queryKey: ["meta"], queryFn: fetchMeta, refetchInterval: 4000 });
}

export function useCaseSummary(caseId: string | null) {
  return useQuery({
    queryKey: ["case", caseId],
    queryFn: () => apiGet<Record<string, unknown>>(`/api/v2/cases/${caseId}`),
    enabled: !!caseId,
    refetchInterval: 1500,
  });
}

export function useCaseDetail(caseId: string | null) {
  return useQuery({
    queryKey: ["case-detail", caseId],
    queryFn: () => apiGet<Record<string, unknown>>(`/api/v2/cases/${caseId}/detail`),
    enabled: !!caseId,
    refetchInterval: 2000,
  });
}
