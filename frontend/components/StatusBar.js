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
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            {backendOk && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            )}
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                backendOk ? "bg-green-500" : "bg-red-500"
              }`}
            />
          </span>
          <span className="text-[11px] text-zinc-500 font-mono">
            {backendOk ? "backend online" : "backend offline"}
          </span>
        </div>

        {/* Last refresh */}
        {lastRefresh && (
          <span className="text-[11px] text-zinc-600 font-mono">
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
          className="text-[11px] bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40 disabled:cursor-not-allowed text-zinc-300 px-3 py-1.5 rounded border border-zinc-700 transition-all duration-300 font-mono flex items-center gap-1.5"
        >
          {checking ? (
            <>
              <svg className="animate-spin h-3.5 w-3.5 text-zinc-400" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>checking…</span>
            </>
          ) : (
            <>
              <span>↻</span>
              <span>run check now</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
