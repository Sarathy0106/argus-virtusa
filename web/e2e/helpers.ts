import { type APIRequestContext, expect } from "@playwright/test";

const API = process.env.E2E_API_BASE ?? "http://localhost:8000";

export async function startCase(request: APIRequestContext, preset = "C1"): Promise<string> {
  const res = await request.post(`${API}/api/v2/cases`, {
    multipart: { preset_id: preset },
  });
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  return body.case_id as string;
}

export async function waitForCase(request: APIRequestContext, caseId: string): Promise<any> {
  for (let i = 0; i < 60; i++) {
    const r = await request.get(`${API}/api/v2/cases/${caseId}`);
    const body = await r.json();
    if (body.status === "COMPLETED" || body.status === "FAILED") return body;
    await new Promise((res) => setTimeout(res, 500));
  }
  throw new Error("case did not complete in time");
}

export async function apiGet(request: APIRequestContext, path: string): Promise<any> {
  const r = await request.get(`${API}${path}`);
  expect(r.ok()).toBeTruthy();
  return r.json();
}

export async function apiPost(
  request: APIRequestContext,
  path: string,
  json?: unknown,
): Promise<{ status: number; body: any }> {
  const r = await request.post(`${API}${path}`, json ? { data: json } : {});
  return { status: r.status(), body: await r.json().catch(() => ({})) };
}

export { API };
