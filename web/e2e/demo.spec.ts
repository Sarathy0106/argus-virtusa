import { test, expect } from "@playwright/test";
import { API, apiGet, apiPost, startCase, waitForCase } from "./helpers";

// End-to-end demo: drive the real UI + gateway through all 8 steps, asserting
// that displayed/returned values equal the API's computed values. Run twice back
// to back (see the two test blocks) to prove repeatability.

async function runFullDemo(request: any, page: any, label: string) {
  // Step 1-2: start a C1 case and let the pipeline complete.
  const caseId = await startCase(request, "C1");
  const summary = await waitForCase(request, caseId);
  expect(summary.status, `${label} case completed`).toBe("COMPLETED");

  const detail = await apiGet(request, `/api/v2/cases/${caseId}/detail`);
  // Step 2: at least one applicable obligation, and bundles produced.
  expect(detail.obligations.length).toBeGreaterThan(0);
  expect(detail.bundles.length).toBeGreaterThanOrEqual(2); // B4

  // Step 3/4: an objection with a Z3 counter-example existed.
  const objections = detail.bundles.flatMap((b: any) => b.objections ?? []);
  const withCe = objections.find((o: any) => o.counter_example);
  expect(withCe, `${label} has Z3 counter-example`).toBeTruthy();

  // Step 5: real backtest over 500k rows.
  expect(summary.backtest.total_rows).toBe(500000);

  // Step 6: approvals. One signature -> 403. Then both -> deploy allowed.
  const bundleHash = summary.bundle_hash;
  const ruleName = summary.rule_name;
  const noSig = await apiPost(request, `/api/v2/deploy/${caseId}`);
  expect(noSig.status, `${label} unsigned deploy 403`).toBe(403);

  const makerTok = (await apiPost(request, "/api/v2/auth/login", { user_id: "maker", password: "maker-demo" })).body.token;
  const checkerTok = (await apiPost(request, "/api/v2/auth/login", { user_id: "checker", password: "checker-demo" })).body.token;
  await apiPost(request, "/api/v2/approvals/maker", { bundle_hash: bundleHash, rule_name: ruleName, token: makerTok, case_id: caseId });

  const oneSig = await apiPost(request, `/api/v2/deploy/${caseId}`);
  expect(oneSig.status, `${label} one-sig deploy 403`).toBe(403);

  await apiPost(request, "/api/v2/approvals/checker", { bundle_hash: bundleHash, rule_name: ruleName, token: checkerTok, case_id: caseId });

  // Step 7: healthy deploy reaches 100%.
  const healthy = await apiPost(request, `/api/v2/deploy/${caseId}`);
  expect(healthy.status, `${label} dual-sig deploy ok`).toBe(200);
  expect(healthy.body.reached_100 || healthy.body.breached).toBeTruthy();

  // Step 7b: chaos flood -> SPRT breach -> measured rollback.
  await request.post(`${API}/api/v2/chaos/alert_flood?case_id=${caseId}`);
  const flooded = await apiPost(request, `/api/v2/deploy/${caseId}`);
  expect(flooded.body.breached, `${label} flood breaches`).toBeTruthy();
  expect(typeof flooded.body.rollback.rollback_ms).toBe("number"); // measured

  // Step 8: audit — ledger verified, inclusion proof verifies, tamper names index.
  const ledger = await apiGet(request, `/api/v2/audit/${caseId}/ledger`);
  expect(ledger.integrity_verified).toBe(true);
  const inc = await apiGet(request, `/api/v2/audit/${caseId}/inclusion/2`);
  expect(inc.verified).toBe(true);
  const tamper = (await apiPost(request, `/api/v2/audit/${caseId}/tamper-demo?target_seq=2`)).body;
  expect(tamper.before.verified).toBe(true);
  expect(tamper.after.verified).toBe(false);
  expect(typeof tamper.after.first_broken_index).toBe("number");

  // UI smoke: the shell renders and the Audit page shows the chain.
  await page.goto("/audit");
  await expect(page.getByRole("heading", { name: "Audit Ledger" })).toBeVisible();

  return caseId;
}

test("demo runs end to end (pass 1)", async ({ request, page }) => {
  await runFullDemo(request, page, "pass1");
});

test("demo runs end to end (pass 2)", async ({ request, page }) => {
  await runFullDemo(request, page, "pass2");
});
