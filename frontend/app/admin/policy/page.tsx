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

// One-line description of what each section controls.
const SECTION_HINTS: Record<string, string> = {
  limits: "Overall annual, per-claim, and family floater caps (in ₹).",
  coverage_consultation: "Doctor consultation cover — sub-limit, co-pay %, and network discount %.",
  coverage_diagnostic: "Lab tests & scans — sub-limit, whether pre-auth is needed, and covered tests.",
  coverage_pharmacy: "Medicines — sub-limit, generic-drug rule, and branded-drug co-pay %.",
  coverage_dental: "Dental cover — sub-limit, covered procedures, and cosmetic exclusion.",
  coverage_vision: "Eye care — sub-limit and what's covered (tests, glasses, LASIK).",
  coverage_alternative: "AYUSH / alternative medicine — sub-limit, covered systems, session cap.",
  waiting_periods: "Waiting periods in days before each condition is claimable.",
  exclusions: "List of treatments the policy never covers.",
  network_hospitals: "Cashless network hospitals and cashless facility rules.",
  claim_requirements: "Documents required, submission window, and minimum claim amount.",
};

// Example schema per section — shown as a placeholder and via "Insert example"
// so admins know the exact fields and shape expected.
const SECTION_TEMPLATES: Record<string, unknown> = {
  limits: { annual_limit: 50000, per_claim_limit: 5000, family_floater_limit: 150000 },
  coverage_consultation: { covered: true, sub_limit: 2000, copay_percentage: 10, network_discount: 20 },
  coverage_diagnostic: {
    covered: true,
    sub_limit: 10000,
    pre_authorization_required: false,
    covered_tests: ["Blood tests", "X-rays", "MRI (with pre-auth)", "CT Scan (with pre-auth)"],
  },
  coverage_pharmacy: { covered: true, sub_limit: 15000, generic_drugs_mandatory: true, branded_drugs_copay: 30 },
  coverage_dental: {
    covered: true,
    sub_limit: 10000,
    routine_checkup_limit: 2000,
    procedures_covered: ["Filling", "Extraction", "Root canal", "Cleaning"],
    cosmetic_procedures: false,
  },
  coverage_vision: { covered: true, sub_limit: 5000, eye_test_covered: true, glasses_contact_lenses: true, lasik_surgery: false },
  coverage_alternative: {
    covered: true,
    sub_limit: 8000,
    covered_treatments: ["Ayurveda", "Homeopathy", "Unani"],
    therapy_sessions_limit: 20,
  },
  waiting_periods: {
    initial_waiting: 30,
    pre_existing_diseases: 365,
    maternity: 270,
    specific_ailments: { diabetes: 90, hypertension: 90, joint_replacement: 730 },
  },
  exclusions: { exclusions: ["Cosmetic procedures", "Weight loss treatments", "Infertility treatments"] },
  network_hospitals: {
    network_hospitals: ["Apollo Hospitals", "Fortis Healthcare", "Max Healthcare"],
    cashless_facilities: { available: true, network_only: true, instant_approval_limit: 5000 },
  },
  claim_requirements: {
    documents_required: ["Original bills and receipts", "Prescription from registered doctor"],
    submission_timeline_days: 30,
    minimum_claim_amount: 500,
  },
};

function templateFor(section: string): string {
  return JSON.stringify(SECTION_TEMPLATES[section] ?? {}, null, 2);
}

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
    const isEmpty =
      data == null || (typeof data === "object" && Object.keys(data as object).length === 0);
    // Leave the box blank when empty so the example placeholder shows through.
    setEditorValue(isEmpty ? "" : JSON.stringify(data, null, 2));
    setMsg({ text: "", ok: true });
  }, [activeSection, policy]);

  async function handleSave() {
    if (!editorValue.trim()) {
      setMsg({ text: "This section is empty — click “Insert example” or type JSON to fill it.", ok: false });
      return;
    }
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
          <div className="mb-1 flex items-center justify-between">
            <p className="font-serif text-base font-medium text-ink">{SECTIONS.find((s) => s.key === activeSection)?.label}</p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setEditorValue(templateFor(activeSection))}
                className="btn-secondary text-xs"
              >
                Insert example
              </button>
              <button onClick={handleSave} disabled={saving} className="btn-primary text-sm">
                {saving ? "Saving…" : "Save & Sync RAG"}
              </button>
            </div>
          </div>
          <p className="mb-3 text-xs text-ink-soft">{SECTION_HINTS[activeSection]}</p>
          <textarea
            className="h-96 w-full resize-none rounded-xl border border-ivory-line bg-ivory-head p-4 font-mono text-xs text-ink placeholder:text-ink-faint/70 focus:outline-none focus:ring-2 focus:ring-verdict-violet/20"
            value={editorValue}
            onChange={(e) => setEditorValue(e.target.value)}
            placeholder={`Example structure for this section — click “Insert example” to start from it:\n\n${templateFor(activeSection)}`}
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
