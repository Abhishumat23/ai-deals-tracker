/**
 * ToolCard
 * Displays the latest pricing snapshot for one AI tool.
 */

// Map tool names to their pricing page URLs
const TOOL_URLS = {
  OpenAI: "https://openai.com/pricing",
  Claude: "https://www.anthropic.com/pricing",
  Gemini: "https://gemini.google/subscriptions/",
  Perplexity: "https://www.perplexity.ai/pro",
  Cursor: "https://www.cursor.com/pricing",
};

// Simple color accent per tool
const TOOL_COLORS = {
  OpenAI: "border-emerald-500",
  Claude: "border-orange-400",
  Gemini: "border-blue-400",
  Perplexity: "border-purple-400",
  Cursor: "border-cyan-400",
};

const TOOL_DOT_COLORS = {
  OpenAI: "bg-emerald-500",
  Claude: "bg-orange-400",
  Gemini: "bg-blue-400",
  Perplexity: "bg-purple-400",
  Cursor: "bg-cyan-400",
};

function formatDate(iso) {
  if (!iso) return "never";
  const d = new Date(iso);
  return d.toLocaleString("en-IN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function formatPriceDisplay(price, billingCycle) {
  if (!price || price.toLowerCase() === "free" || price.toLowerCase() === "not found" || price.toLowerCase() === "see website") {
    return price;
  }
  
  // Strip any existing billing or unit suffixes (user, seat, mo, yr, etc.) to prevent duplicates
  let cleanedPrice = price
    .replace(/\/(user|seat|mo|month|yr|year)\b/ig, "")
    .trim();
    
  if (cleanedPrice.endsWith("/")) {
    cleanedPrice = cleanedPrice.slice(0, -1).trim();
  }

  if (billingCycle === "monthly") {
    if (price.toLowerCase().includes("user")) {
      return `${cleanedPrice}/user/mo`;
    } else if (price.toLowerCase().includes("seat")) {
      return `${cleanedPrice}/seat/mo`;
    }
    return `${cleanedPrice}/mo`;
  } else if (billingCycle === "annually") {
    if (price.toLowerCase().includes("user")) {
      return `${cleanedPrice}/user/yr`;
    } else if (price.toLowerCase().includes("seat")) {
      return `${cleanedPrice}/seat/yr`;
    }
    return `${cleanedPrice}/yr`;
  }
  
  return cleanedPrice;
}

export default function ToolCard({ tool, index = 0 }) {
  const borderColor = TOOL_COLORS[tool.tool_name] || "border-zinc-600";
  const dotColor = TOOL_DOT_COLORS[tool.tool_name] || "bg-zinc-500";
  const url = TOOL_URLS[tool.tool_name] || "#";
  
  const rawTiers = tool.tiers || [];
  const rawPreviousTiers = tool.previous_tiers || [];
  
  const tiers = rawTiers.map(t => ({
    ...t,
    price: formatPriceDisplay(t.price, t.billing_cycle)
  }));
  const previousTiers = rawPreviousTiers.map(pt => {
    const currentTier = rawTiers.find(t => t.name === pt.name);
    const billingCycle = pt.billing_cycle && pt.billing_cycle !== "Unpublished"
      ? pt.billing_cycle
      : (currentTier ? currentTier.billing_cycle : "Unpublished");
    return {
      ...pt,
      price: formatPriceDisplay(pt.price, billingCycle)
    };
  });
  
  const hasPriceChange = previousTiers.length > 0 && JSON.stringify(tiers) !== JSON.stringify(previousTiers);

  return (
    <div
      style={{ animationDelay: `${index * 50}ms` }}
      className={`bg-zinc-900/40 backdrop-blur-md border-l-2 ${borderColor} rounded-r border border-l-0 border-zinc-900 p-4 flex flex-col gap-2 animate-fade-in-up hover:border-zinc-800 hover:shadow-xl hover:shadow-black/20 hover:-translate-y-0.5 transition-all duration-300`}
    >
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${dotColor} flex-shrink-0`} />
          <span className="text-sm font-semibold text-zinc-100 tracking-wide">
            {tool.tool_name}
          </span>
        </div>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          ↗ pricing page
        </a>
      </div>

      {/* Strict Tiers Layout */}
      <div className="flex flex-col gap-1.5 min-h-[24px]">
        {tiers.length > 0 ? (
          tiers.map((t, i) => {
            const isNotFound = t.price === "Not found";
            
            // Find old price for this tier if it exists
            const prevTier = previousTiers.find((pt) => pt.name === t.name);
            const oldPriceStr = prevTier && prevTier.price !== t.price ? ` (was: ${prevTier.price})` : "";
            
            if (isNotFound) {
              console.warn(`[Telemetry Warning] Price for tier ${t.name} on ${tool.tool_name} was 'Not found'.`);
            }
            
            return (
              <div 
                key={i} 
                className={`flex items-baseline text-[12px] font-mono ${isNotFound ? 'opacity-30' : 'text-zinc-200'}`}
              >
                <span className="font-semibold">{t.name || "Unknown"}</span>
                <span className="mx-2 text-zinc-600">➔</span>
                <span className={isNotFound ? "italic" : "text-emerald-400 font-bold"}>
                  {t.price}
                </span>
                {oldPriceStr && (
                  <span className="ml-2 text-[10px] text-amber-500">
                    {oldPriceStr}
                  </span>
                )}
              </div>
            );
          })
        ) : (
          <span className="text-[11px] text-zinc-600 italic">
            no tiers extracted
          </span>
        )}
      </div>

      {/* Last checked */}
      <div className="text-[10px] text-zinc-600 mt-1">
        last snapshot: {formatDate(tool.created_at)}
      </div>
    </div>
  );
}
