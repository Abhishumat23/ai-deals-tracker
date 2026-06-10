/**
 * StatusBar
 * Top bar showing last refresh time, backend status, and manual trigger button.
 */

import { useState } from "react";

export default function StatusBar({ lastRefresh, onManualCheck, backendOk }) {
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState(null);

  async function handleCheck() {
    setChecking(true);
    setResult(null);
    try {
      const res = await fetch("/api/run-check", { method: "POST" });
      const data = await res.json();
      setResult(`✓ ${data.tools_checked} tools checked`);
      // Notify parent to refresh data
      if (onManualCheck) onManualCheck();
    } catch {
      setResult("⚠ Backend unreachable");
    } finally {
      setChecking(false);
      setTimeout(() => setResult(null), 4000);
    }
  }

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 py-2 px-0 border-b border-zinc-800 mb-6">
      <div className="flex items-center gap-3">
        {/* Backend status dot */}
        <div className="flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${
              backendOk ? "bg-green-500" : "bg-red-500"
            }`}
          />
          <span className="text-[11px] text-zinc-500">
            {backendOk ? "backend online" : "backend offline"}
          </span>
        </div>

        {/* Last refresh */}
        {lastRefresh && (
          <span className="text-[11px] text-zinc-600">
            refreshed {lastRefresh}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3">
        {result && (
          <span className="text-[11px] text-zinc-400 font-mono">{result}</span>
        )}
        <button
          onClick={handleCheck}
          disabled={checking}
          className="text-[11px] bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40 disabled:cursor-not-allowed text-zinc-300 px-3 py-1.5 rounded border border-zinc-700 transition-colors font-mono"
        >
          {checking ? "checking…" : "↻ run check now"}
        </button>
      </div>
    </div>
  );
}
