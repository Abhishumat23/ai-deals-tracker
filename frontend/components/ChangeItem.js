/**
 * ChangeItem
 * Renders a single detected pricing change record with grouped plan changes.
 */

const PROVIDER_METADATA = {
  OpenAI: {
    color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    text_color: "text-emerald-400",
    initials: "O",
    logo_svg: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    )
  },
  Claude: {
    color: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    text_color: "text-orange-400",
    initials: "C",
    logo_svg: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    )
  },
  Gemini: {
    color: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    text_color: "text-blue-400",
    initials: "G",
    logo_svg: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
      </svg>
    )
  },
  Perplexity: {
    color: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    text_color: "text-purple-400",
    initials: "P",
    logo_svg: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    )
  },
  Cursor: {
    color: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
    text_color: "text-cyan-400",
    initials: "Cr",
    logo_svg: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
      </svg>
    )
  }
};

const CHANGE_TYPE_MAP = {
  price_increase: {
    label: "Price Increased",
    icon: (
      <svg className="w-3 h-3 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
      </svg>
    ),
    color: "text-red-400 bg-red-500/10 border-red-500/25"
  },
  price_decrease: {
    label: "Price Decreased",
    icon: (
      <svg className="w-3 h-3 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
      </svg>
    ),
    color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/25"
  },
  new_plan: {
    label: "New Plan Added",
    icon: (
      <svg className="w-3 h-3 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
      </svg>
    ),
    color: "text-blue-400 bg-blue-500/10 border-blue-500/25"
  },
  plan_removed: {
    label: "Plan Removed",
    icon: (
      <svg className="w-3 h-3 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
    color: "text-zinc-400 bg-zinc-500/10 border-zinc-500/25"
  },
  pricing_structure_change: {
    label: "Pricing Structure Changed",
    icon: (
      <svg className="w-3 h-3 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3-3 3 3" />
      </svg>
    ),
    color: "text-amber-400 bg-amber-500/10 border-amber-500/25"
  },
  price_change: {
    label: "Price Changed",
    icon: (
      <svg className="w-3 h-3 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3-3 3 3" />
      </svg>
    ),
    color: "text-amber-400 bg-amber-500/10 border-amber-500/25"
  }
};

function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

function formatFull(iso) {
  return new Date(iso).toLocaleString("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export default function ChangeItem({ change, index }) {
  const company = change.company || "Unknown";
  const metadata = PROVIDER_METADATA[company] || {
    color: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
    text_color: "text-zinc-400",
    initials: company.substring(0, 1),
    logo_svg: null
  };
  
  const url_map = {
    OpenAI: "https://openai.com/pricing",
    Claude: "https://www.anthropic.com/pricing",
    Gemini: "https://gemini.google/subscriptions/",
    Perplexity: "https://www.perplexity.ai/pro",
    Cursor: "https://cursor.com/pricing",
  };
  const source_url = url_map[company] || "#";

  return (
    <div
      style={{ animationDelay: `${(index + 2) * 80}ms` }}
      className="border border-zinc-900 bg-zinc-900/40 backdrop-blur-md hover:border-zinc-800 hover:shadow-xl hover:shadow-black/20 hover:-translate-y-0.5 transition-all duration-300 rounded-lg p-5 flex flex-col justify-between gap-4 font-sans relative overflow-hidden animate-fade-in-up"
    >
      {/* Brand Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg border flex items-center justify-center ${metadata.color} font-bold text-sm tracking-wider shadow-inner`}>
            {metadata.logo_svg || metadata.initials}
          </div>
          <div className="flex flex-col">
            <span className="text-zinc-100 font-bold text-base tracking-tight">{company}</span>
            <span className="text-[11px] text-zinc-500 font-medium">Pricing Updated</span>
          </div>
        </div>
        <span
          className="text-[10px] font-mono text-zinc-600 bg-zinc-900/60 px-2.5 py-1 rounded border border-zinc-900"
          title={formatFull(change.detected_at)}
        >
          {timeAgo(change.detected_at)}
        </span>
      </div>

      {/* Changed Prices Area */}
      <div className="flex flex-col gap-3.5 mt-2">
        <div className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
          Changed Prices
        </div>
        <div className="h-px bg-zinc-800/60 w-full" />
        
        <div className="flex flex-col gap-4">
          {(change.changes || []).map((chg, idx) => {
            const typeInfo = CHANGE_TYPE_MAP[chg.type] || {
              label: "Plan Changed",
              icon: "🔄",
              color: "text-zinc-400 bg-zinc-500/10 border-zinc-500/25"
            };
            
            return (
              <div key={idx} className="flex flex-col gap-1.5 pl-2 border-l-2 border-zinc-800">
                {/* Plan Header */}
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-zinc-300 font-mono">
                    {chg.plan || "Plan"}
                  </span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full border ${typeInfo.color} font-medium flex items-center gap-1`}>
                    <span>{typeInfo.icon}</span>
                    <span>{typeInfo.label}</span>
                  </span>
                </div>
                
                {/* Plan Prices */}
                <div className="flex items-center gap-3 text-[11px] font-mono text-zinc-400 mt-0.5">
                  {chg.old_price && (
                    <>
                      <span className="text-zinc-500">Old: {chg.old_price}</span>
                      <span className="text-zinc-600">➔</span>
                    </>
                  )}
                  <span className="text-emerald-400 font-bold">
                    {chg.new_price ? chg.new_price : "Plan Removed"}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer link */}
      <div className="mt-2 flex items-center justify-end">
        <a
          href={source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs font-semibold text-zinc-500 hover:text-zinc-300 transition-colors flex items-center gap-1 font-mono tracking-tight"
        >
          View Details <span className="text-zinc-600 font-sans">→</span>
        </a>
      </div>
    </div>
  );
}
