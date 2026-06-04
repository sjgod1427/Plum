"use client";

import { useEffect, useState } from "react";
import { RotateCw, Mail } from "lucide-react";
import { getPolicy, updatePolicySection, rebuildRag, getAdminConfig, updateAdminConfig } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import { PageMotion } from "@/components/motion";

const SECTIONS = [
  { key: "limits", label: "Coverage Limits" },
  { key: "coverage_consultation", label: "Consultation" },
  { key: "coverage_diagnostic", label: "Diagnostic Tests" },
  { key: "coverage_pharmacy", label: "Pharmacy" },
  { key: "coverage_dental", label: "Dental" },
  { key: "coverage_vision", label: "Vision" },
  { key: "coverage_alternative", label: "Alternative Medicine" },
  { key: "waiting_periods", label: "Waiting Periods" },
  { key: "exclusions", label: "Exclusions" },
  { key: "network_hospitals", label: "Network Hospitals" },
  { key: "claim_requirements", label: "Claim Requirements" },
];

export default function PolicyPage() {
  const [policy, setPolicy] = useState<Record<string, unknown>>({});
  const [source, setSource] = useState("");
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState("limits");
  const [editorValue, setEditorValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [msg, setMsg] = useState({ text: "", ok: true });

  const [reviewerEmail, setReviewerEmail] = useState("");
  const [emailSaving, setEmailSaving] = useState(false);
  const [emailMsg, setEmailMsg] = useState({ text: "", ok: true });

  useEffect(() => {
    getPolicy().then((r) => {
      setPolicy(r.policy as Record<string, unknown>);
      setSource(r.source);
    }).finally(() => setLoading(false));
    getAdminConfig().then((r) => setReviewerEmail(r.reviewer_email || ""));
  }, []);

  useEffect(() => {
    const data = policy[activeSection];
    setEditorValue(data ? JSON.stringify(data, null, 2) : "{}");
    setMsg({ text: "", ok: true });
  }, [activeSection, policy]);

  async function handleSave() {
    setSaving(true);
    setMsg({ text: "", ok: true });
    try {
      const parsed = JSON.parse(editorValue);
      await updatePolicySection(activeSection, parsed);
      setPolicy((prev) => ({ ...prev, [activeSection]: parsed }));
      setMsg({ text: "Section saved and RAG synced.", ok: true });
    } catch {
      setMsg({ text: "Invalid JSON or save failed.", ok: false });
    } finally {
      setSaving(false);
    }
  }

  async function handleEmailSave() {
    setEmailSaving(true);
    setEmailMsg({ text: "", ok: true });
    try {
      await updateAdminConfig(reviewerEmail);
      setEmailMsg({ text: "Email saved. Notifications will be sent to this address.", ok: true });
    } catch {
      setEmailMsg({ text: "Failed to save email.", ok: false });
    } finally {
      setEmailSaving(false);
    }
  }

  async function handleRebuild() {
    setRebuilding(true);
    try {
      const r = (await rebuildRag()) as Record<string, unknown>;
      setMsg({ text: `RAG rebuilt — ${r.sections ?? "all"} sections re-embedded.`, ok: true });
    } catch {
      setMsg({ text: "RAG rebuild failed.", ok: false });
    } finally {
      setRebuilding(false);
    }
  }

  if (loading) return <LoadingSpinner />;

  return (
    <PageMotion>
      <div className="mb-6 flex items-end justify-between">
        <div>
          <span className="eyebrow">Configuration</span>
          <h1 className="page-title">
            Policy <em>Config</em>
          </h1>
          <p className="mt-2 text-[13px] text-ink-soft">
            Source: <span className="font-medium text-ink">{source}</span>
          </p>
        </div>
        <button onClick={handleRebuild} disabled={rebuilding} className="btn-secondary">
          <RotateCw size={15} strokeWidth={2} className={rebuilding ? "animate-spin" : ""} />
          {rebuilding ? "Rebuilding…" : "Rebuild RAG"}
        </button>
      </div>

      {/* Notification settings */}
      <div className="card mb-6">
        <p className="mb-1 flex items-center gap-2 font-serif text-base font-medium text-ink">
          <Mail size={16} strokeWidth={1.8} className="text-verdict-violet" />
          Notification Settings
        </p>
        <p className="mb-3 text-xs text-ink-soft">
          Admin reviewer email — all <span className="font-medium text-verdict-amber">MANUAL_REVIEW</span> flags
          and <span className="font-medium text-verdict-violet">appeal</span> submissions are sent here.
          Leave blank to disable email notifications.
        </p>
        <div className="flex items-start gap-3">
          <input
            type="email"
            className="input flex-1"
            placeholder="reviewer@yourcompany.com"
            value={reviewerEmail}
            onChange={(e) => setReviewerEmail(e.target.value)}
          />
          <button onClick={handleEmailSave} disabled={emailSaving} className="btn-primary whitespace-nowrap text-sm">
            {emailSaving ? "Saving…" : "Save Email"}
          </button>
        </div>
        {emailMsg.text && (
          <p className={`mt-2 text-xs ${emailMsg.ok ? "text-verdict-green" : "text-verdict-red"}`}>{emailMsg.text}</p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {/* Section list */}
        <div className="space-y-1">
          {SECTIONS.map((s) => (
            <button
              key={s.key}
              onClick={() => setActiveSection(s.key)}
              className={`w-full rounded-lg px-3.5 py-2.5 text-left text-sm transition-all duration-150 ${
                activeSection === s.key
                  ? "bg-ink font-medium text-white"
                  : "text-ink-soft hover:bg-ivory-hover"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* Editor */}
        <div className="card md:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <p className="font-serif text-base font-medium text-ink">{SECTIONS.find((s) => s.key === activeSection)?.label}</p>
            <button onClick={handleSave} disabled={saving} className="btn-primary text-sm">
              {saving ? "Saving…" : "Save & Sync RAG"}
            </button>
          </div>
          <textarea
            className="h-96 w-full resize-none rounded-xl border border-ivory-line bg-ivory-head p-4 font-mono text-xs text-ink focus:outline-none focus:ring-2 focus:ring-verdict-violet/20"
            value={editorValue}
            onChange={(e) => setEditorValue(e.target.value)}
            spellCheck={false}
          />
          {msg.text && (
            <p className={`mt-2 text-sm ${msg.ok ? "text-verdict-green" : "text-verdict-red"}`}>{msg.text}</p>
          )}
        </div>
      </div>
    </PageMotion>
  );
}
