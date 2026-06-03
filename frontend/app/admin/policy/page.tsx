"use client";

import { useEffect, useState } from "react";
import { getPolicy, updatePolicySection, rebuildRag } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";

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

  useEffect(() => {
    getPolicy().then((r) => {
      setPolicy(r.policy as Record<string, unknown>);
      setSource(r.source);
    }).finally(() => setLoading(false));
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

  async function handleRebuild() {
    setRebuilding(true);
    try {
      const r = await rebuildRag() as Record<string, unknown>;
      setMsg({ text: `RAG rebuilt — ${r.sections ?? "all"} sections re-embedded.`, ok: true });
    } catch {
      setMsg({ text: "RAG rebuild failed.", ok: false });
    } finally {
      setRebuilding(false);
    }
  }

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Policy Configuration</h1>
          <p className="text-sm text-slate-500 mt-1">
            Source: <span className="font-medium">{source}</span>
          </p>
        </div>
        <button onClick={handleRebuild} disabled={rebuilding} className="btn-secondary">
          {rebuilding ? "Rebuilding..." : "🔄 Rebuild RAG"}
        </button>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Section list */}
        <div className="space-y-1">
          {SECTIONS.map((s) => (
            <button key={s.key} onClick={() => setActiveSection(s.key)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                activeSection === s.key ? "bg-plum-600 text-white font-medium" : "text-slate-600 hover:bg-slate-100"
              }`}>
              {s.label}
            </button>
          ))}
        </div>

        {/* JSON editor */}
        <div className="col-span-2 card">
          <div className="flex justify-between items-center mb-4">
            <p className="font-semibold">{SECTIONS.find((s) => s.key === activeSection)?.label}</p>
            <button onClick={handleSave} disabled={saving} className="btn-primary text-sm">
              {saving ? "Saving..." : "Save & Sync RAG"}
            </button>
          </div>
          <textarea
            className="w-full font-mono text-xs bg-slate-50 border border-slate-200 rounded-lg p-4 h-96 resize-none focus:outline-none focus:ring-2 focus:ring-plum-500"
            value={editorValue}
            onChange={(e) => setEditorValue(e.target.value)}
            spellCheck={false}
          />
          {msg.text && (
            <p className={`mt-2 text-sm ${msg.ok ? "text-green-600" : "text-red-600"}`}>{msg.text}</p>
          )}
        </div>
      </div>
    </div>
  );
}
