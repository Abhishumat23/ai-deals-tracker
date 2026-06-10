/**
 * ChangeItem
 * Renders a single detected pricing change record.
 */

const TOOL_COLORS = {
  OpenAI: "text-emerald-400",
  Claude: "text-orange-400",
  Gemini: "text-blue-400",
  Perplexity: "text-purple-400",
  Cursor: "text-cyan-400",
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
  const toolColor = TOOL_COLORS[change.tool_name] || "text-zinc-300";
  // Show the first ~250 chars of the summary
  const preview = (change.summary || "Change detected").slice(0, 250);

  return (
    <div className="border border-zinc-800 rounded bg-zinc-900 p-4 flex flex-col gap-2 hover:border-zinc-700 transition-colors">
      {/* Top row */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="text-zinc-600 text-[11px] font-mono w-5 text-right flex-shrink-0">
            #{index + 1}
          </span>
          <span className={`text-sm font-semibold ${toolColor}`}>
            {change.tool_name}
          </span>
          <span className="text-[10px] bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 px-1.5 py-0.5 rounded font-mono">
            CHANGE
          </span>
        </div>
        <span
          className="text-[10px] text-zinc-500 flex-shrink-0"
          title={formatFull(change.detected_at)}
        >
          {timeAgo(change.detected_at)}
        </span>
      </div>

      {/* Summary preview */}
      <p className="text-[11px] text-zinc-400 font-mono leading-relaxed whitespace-pre-wrap break-words">
        {preview}
        {(change.summary || "").length > 250 ? "…" : ""}
      </p>
    </div>
  );
}
