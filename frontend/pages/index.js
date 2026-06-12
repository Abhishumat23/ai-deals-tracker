/**
 * Main Dashboard — AI Deals & Pricing Intelligence Tracker
 *
 * Auto-refreshes every 60 seconds.
 * Shows: backend status, tool snapshots, change feed.
 */

import { useState, useEffect, useCallback } from "react";
import Head from "next/head";
import ToolCard from "../components/ToolCard";
import ChangeItem from "../components/ChangeItem";
import StatusBar from "../components/StatusBar";

const API = "/api"; // proxied to http://localhost:8000 via next.config.js
const REFRESH_MS = 60_000; // auto-refresh interval

function now() {
  return new Date().toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function groupChangesByCompany(changesList) {
  const grouped = {};
  
  // Process older first to let newer changes overwrite/merge
  const list = [...changesList].reverse();
  
  for (const c of list) {
    const company = c.company;
    if (!grouped[company]) {
      grouped[company] = {
        company: company,
        detected_at: c.detected_at,
        timestamp: c.timestamp,
        plans: {}
      };
    }
    
    grouped[company].detected_at = c.detected_at;
    grouped[company].timestamp = c.timestamp;
    
    for (const chg of (c.changes || [])) {
      const plan = chg.plan || "Plan";
      const existing = grouped[company].plans[plan];
      if (existing) {
        grouped[company].plans[plan] = {
          type: chg.type,
          plan: plan,
          old_price: existing.old_price !== null ? existing.old_price : chg.old_price,
          new_price: chg.new_price
        };
      } else {
        grouped[company].plans[plan] = {
          type: chg.type,
          plan: plan,
          old_price: chg.old_price,
          new_price: chg.new_price
        };
      }
    }
  }
  
  return Object.values(grouped)
    .map(g => {
      const plansList = Object.values(g.plans).filter(p => p.old_price !== p.new_price);
      return {
        ...g,
        changes: plansList
      };
    })
    .filter(g => g.changes.length > 0)
    .sort((a, b) => new Date(b.detected_at) - new Date(a.detected_at));
}

export default function Dashboard() {
  const [tools, setTools] = useState([]);
  const [changes, setChanges] = useState([]);
  const [backendOk, setBackendOk] = useState(false);
  const [lastRefresh, setLastRefresh] = useState("");
  const [loading, setLoading] = useState(true);
  
  const groupedChanges = groupChangesByCompany(changes);

  const fetchData = useCallback(async () => {
    try {
      // Parallel fetches
      const [toolsRes, changesRes] = await Promise.all([
        fetch(`${API}/tools`),
        fetch(`${API}/changes?limit=50`),
      ]);

      if (!toolsRes.ok || !changesRes.ok) throw new Error("Bad response");

      const [toolsData, changesData] = await Promise.all([
        toolsRes.json(),
        changesRes.json(),
      ]);

      setTools(toolsData);
      setChanges(changesData);
      setBackendOk(true);
    } catch {
      setBackendOk(false);
    } finally {
      setLoading(false);
      setLastRefresh(now());
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh every 60 seconds
  useEffect(() => {
    const timer = setInterval(fetchData, REFRESH_MS);
    return () => clearInterval(timer);
  }, [fetchData]);

  return (
    <>
      <Head>
        <title>AI Deals Tracker</title>
        <meta name="description" content="Monitor AI tool pricing changes" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div className="min-h-screen bg-zinc-950 text-zinc-200">
        <div className="max-w-5xl mx-auto px-4 py-6">

          {/* Header */}
          <header className="mb-6">
            <div className="flex items-baseline gap-3">
              <h1 className="text-xl font-bold text-zinc-100 tracking-tight font-mono">
                ai-deals-tracker
              </h1>
              <span className="text-[11px] text-zinc-600 font-mono">
                v1.0 · local-first
              </span>
            </div>
            <p className="text-[12px] text-zinc-500 mt-0.5 font-mono">
              monitors openai · anthropic · gemini · perplexity · cursor
            </p>
          </header>

          {/* Status bar */}
          <StatusBar
            lastRefresh={lastRefresh}
            onManualCheck={fetchData}
            backendOk={backendOk}
          />

          {loading ? (
            <div className="flex items-center justify-center py-20 text-zinc-600 font-mono text-sm">
              loading…
            </div>
          ) : !backendOk ? (
            <BackendOfflineMessage />
          ) : (
            <>
              {/* Tool snapshots */}
              <section className="mb-8">
                <SectionLabel
                  label="current snapshots"
                  count={tools.length}
                />
                {tools.length === 0 ? (
                  <EmptyState
                    message='No data yet. Click "run check now" or wait for the first scheduled scrape.'
                  />
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {tools.map((t, idx) => (
                      <ToolCard key={t.tool_name} tool={t} index={idx} />
                    ))}
                  </div>
                )}
              </section>

              {/* Changes feed */}
              <section>
                <SectionLabel
                  label="detected changes"
                  count={groupedChanges.length}
                />
                {groupedChanges.length === 0 ? (
                  <EmptyState
                    message="No changes detected yet. Changes appear here when pricing pages update."
                  />
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {groupedChanges.map((c, i) => (
                      <ChangeItem key={c.company} change={c} index={i} />
                    ))}
                  </div>
                )}
              </section>
            </>
          )}

          {/* Footer */}
          <footer className="mt-12 pt-4 border-t border-zinc-900 text-[10px] text-zinc-700 font-mono flex justify-between">
            <span>auto-refreshes every 60s</span>
            <span>scrapes every {process.env.NEXT_PUBLIC_INTERVAL || "60"}min</span>
          </footer>
        </div>
      </div>
    </>
  );
}

// ─────────────────────────────────────────────────────────────
// Small helper components
// ─────────────────────────────────────────────────────────────

function SectionLabel({ label, count }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span className="text-[11px] uppercase tracking-widest text-zinc-500 font-mono">
        {label}
      </span>
      <span className="text-[10px] bg-zinc-800 text-zinc-500 px-1.5 py-0.5 rounded font-mono">
        {count}
      </span>
      <span className="flex-1 h-px bg-zinc-900" />
    </div>
  );
}

function EmptyState({ message }) {
  return (
    <div className="border border-dashed border-zinc-800 rounded p-6 text-center">
      <p className="text-[12px] text-zinc-600 font-mono">{message}</p>
    </div>
  );
}

function BackendOfflineMessage() {
  return (
    <div className="border border-red-900/40 bg-red-950/20 rounded p-6 text-center">
      <p className="text-sm text-red-400 font-mono mb-1">⚠ Backend unreachable</p>
      <p className="text-[11px] text-zinc-500 font-mono">
        Make sure FastAPI is running:
        <code className="ml-1 bg-zinc-900 px-1.5 py-0.5 rounded text-zinc-300">
          cd backend && uvicorn app:app --reload
        </code>
      </p>
    </div>
  );
}
