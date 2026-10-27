"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import { useCaseStore } from "@/store/case";
import { useCaseSummary } from "@/lib/hooks";
import { Panel } from "@/components/shell/Panel";
import { shortHash } from "@/lib/format";

type UserInfo = { user_id: string; name: string; role: string; public_key_fingerprint: string };

// Approvals (step 6): login as demo users, sign the bundle hash with each user's
// own key, and watch the Deploy button stay disabled until both sign. A visible
// "deploy with one signature" button shows the real 403.
export default function ApprovalsPage() {
  const caseId = useCaseStore((s) => s.caseId);
  const summary = useCaseSummary(caseId);
  const bundleHash = summary.data?.bundle_hash as string | undefined;
  const ruleName = (summary.data?.rule_name as string) ?? "bundle";

  const [users, setUsers] = useState<UserInfo[]>([]);
  const [tokens, setTokens] = useState<Record<string, string>>({});
  const [approval, setApproval] = useState<Record<string, unknown>>({});
  const [deployMsg, setDeployMsg] = useState<string>("");

  useEffect(() => {
    apiGet<{ users: UserInfo[] }>("/api/v2/auth/users").then((d) => setUsers(d.users));
  }, []);

  async function login(uid: string) {
    const d = await apiPost<{ token: string }>("/api/v2/auth/login", {
      user_id: uid,
      password: `${uid}-demo`,
    });
    setTokens((t) => ({ ...t, [uid]: d.token }));
  }

  async function sign(slot: "maker" | "checker", uid: string) {
    if (!bundleHash) return;
    await apiPost(`/api/v2/approvals/${slot}`, {
      bundle_hash: bundleHash,
      rule_name: ruleName,
      token: tokens[uid],
    });
    refreshApproval();
  }

  async function refreshApproval() {
    if (!bundleHash) return;
    const a = await apiGet<Record<string, unknown>>(`/api/v2/approvals/${bundleHash}`);
    setApproval(a);
  }

  useEffect(() => {
    if (bundleHash) refreshApproval();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bundleHash]);

  async function deploy() {
    setDeployMsg("…");
    try {
      const res = await fetch(`/api/v2/deploy/${caseId}`, { method: "POST" });
      const body = await res.json();
      setDeployMsg(res.ok ? `Deployed (status ${res.status})` : `Blocked: ${res.status} — ${body.detail}`);
    } catch (e) {
      setDeployMsg(String(e));
    }
  }

  const bothSigned = Boolean(approval.both_signed);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-heading text-2xl font-bold text-text">Approvals</h1>

      <Panel state={caseId ? "live" : "empty"} title="Demo users" emptyLabel="Start a case first.">
        <div className="grid gap-2 sm:grid-cols-2">
          {users.map((u) => (
            <div key={u.user_id} className="flex items-center justify-between rounded-btn border border-border bg-elevated p-3">
              <div>
                <div className="text-sm text-text">{u.name}</div>
                <div className="font-mono text-xs text-muted">
                  {u.role} · {u.public_key_fingerprint}
                </div>
              </div>
              <div className="flex gap-1">
                <button onClick={() => login(u.user_id)} className="rounded-btn border border-border px-2 py-1 text-xs text-muted hover:text-text">
                  {tokens[u.user_id] ? "logged in" : "login"}
                </button>
                {u.role === "maker" && (
                  <button disabled={!tokens[u.user_id]} onClick={() => sign("maker", u.user_id)} className="rounded-btn bg-accent px-2 py-1 text-xs text-bg disabled:opacity-40">
                    sign maker
                  </button>
                )}
                {u.role === "checker" && (
                  <button disabled={!tokens[u.user_id]} onClick={() => sign("checker", u.user_id)} className="rounded-btn bg-accent px-2 py-1 text-xs text-bg disabled:opacity-40">
                    sign checker
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel state={bundleHash ? "live" : "empty"} title="Dual approval" emptyLabel="No bundle to approve yet.">
        <div className="mb-3 font-mono text-xs text-muted">bundle hash: {shortHash(bundleHash)}</div>
        <div className="grid gap-3 sm:grid-cols-2">
          <SigCard label="Maker" sig={approval.maker as Record<string, unknown> | null} />
          <SigCard label="Checker" sig={approval.checker as Record<string, unknown> | null} />
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button
            disabled={!bothSigned}
            onClick={deploy}
            className="rounded-btn bg-ok px-4 py-2 text-sm font-medium text-bg disabled:cursor-not-allowed disabled:opacity-40"
          >
            Deploy {bothSigned ? "" : "(needs both signatures)"}
          </button>
          <button
            onClick={deploy}
            className="rounded-btn border border-danger px-4 py-2 text-sm text-danger"
          >
            Try deploy now (expect 403 if unsigned)
          </button>
          {deployMsg && <span className="font-mono text-xs text-text">{deployMsg}</span>}
        </div>
      </Panel>
    </div>
  );
}

function SigCard({ label, sig }: { label: string; sig: Record<string, unknown> | null }) {
  return (
    <div className={`rounded-btn border p-3 ${sig ? "border-ok" : "border-border"}`}>
      <div className="text-xs text-muted">{label}</div>
      {sig ? (
        <>
          <div className="text-sm text-text">{String(sig.user_id)}</div>
          <div className="font-mono text-[11px] text-ok">signed · {String(sig.fingerprint)}</div>
        </>
      ) : (
        <div className="text-sm text-muted">not signed</div>
      )}
    </div>
  );
}
