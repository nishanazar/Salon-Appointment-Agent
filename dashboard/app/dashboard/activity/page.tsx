import { readFile, writeFile } from "fs/promises";
import path from "path";
import { revalidatePath } from "next/cache";
import Link from "next/link";
import Nav from "@/app/components/Nav";
import ClearLogButton from "./ClearLogButton";
import AutoRefresh from "./AutoRefresh";

// Always fetch fresh data - no ISR caching
export const revalidate = 0;

const LINES_SHOWN = 20;

interface LogEntry {
  timestamp: string;
  event: "CALL" | "OK" | "FAIL" | "CRASH";
  tool: string;
  detail: string;
}

// Log format: 2026-09-01 10:47:47,265 | INFO | OK   tool_name | payload
const LINE_RE =
  /^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ \| \w+ \| (CALL|OK|FAIL|CRASH)\s+(\w+)\s*\| (.*)$/;

function parseLine(line: string): LogEntry | null {
  const m = line.match(LINE_RE);
  if (!m) return null;
  return {
    timestamp: m[1],
    event: m[2] as LogEntry["event"],
    tool: m[3],
    detail: summarize(m[2], m[4] ?? ""),
  };
}

// Turn the raw payload into a short human-readable summary (never raw JSON).
function summarize(event: string, payload: string): string {
  if (event === "CRASH") return payload; // "ExceptionType: message" is already readable

  const raw = event === "CALL" ? payload.replace(/^params=/, "") : payload;
  let obj: Record<string, unknown> | null = null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      obj = parsed as Record<string, unknown>;
    }
  } catch {
    // payload is not JSON — fall through
  }

  if (event === "CALL") {
    if (!obj) return "";
    const parts = Object.entries(obj).map(([k, v]) => `${k}: ${String(v)}`);
    return parts.length > 0 ? parts.join(" \u00B7 ") : "no parameters";
  }

  if (obj) {
    if (typeof obj.message === "string" && obj.message.trim()) return obj.message;
    const list = obj.appointments ?? obj.services ?? obj.available_slots;
    if (Array.isArray(list)) {
      return `${list.length} result${list.length === 1 ? "" : "s"} returned`;
    }
    if (obj.id !== undefined && obj.status !== undefined) {
      return `Appointment #${obj.id} \u2014 ${obj.status}`;
    }
    if (event === "FAIL" && typeof obj.error === "string" && obj.error) {
      return obj.error;
    }
  }
  return "";
}

function eventConfig(event: string) {
  switch (event) {
    case "OK":
      return {
        icon: "\u2713",
        iconCls: "bg-emerald-100 text-emerald-600",
        label: "Success",
        badge: "bg-emerald-100 text-emerald-700",
      };
    case "FAIL":
    case "CRASH":
      return {
        icon: "\u2717",
        iconCls: "bg-rose-100 text-rose-600",
        label: "Error",
        badge: "bg-rose-100 text-rose-700",
      };
    case "CALL":
      return {
        icon: "\u25B6",
        iconCls: "bg-indigo-100 text-indigo-600",
        label: "Called",
        badge: "bg-indigo-100 text-indigo-700",
      };
    default:
      return {
        icon: "\u2022",
        iconCls: "bg-gray-100 text-gray-600",
        label: "Log",
        badge: "bg-gray-100 text-gray-700",
      };
  }
}

function formatTimestamp(ts: string): { date: string; time: string } {
  const d = new Date(ts.replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return { date: ts, time: "" };
  return {
    date: d.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }),
    time: d.toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    }),
  };
}

// Local calendar date (YYYY-MM-DD) for "today" filtering. Log timestamps
// are local time, written by the Python server on this same machine.
function todayLocalDate(): string {
  const now = new Date();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${m}-${d}`;
}

// Log lives next to the MCP server, one level above the dashboard folder.
function logPaths(): string[] {
  return [
    path.join(process.cwd(), "logs", "tool-calls.log"),
    path.join(process.cwd(), "..", "logs", "tool-calls.log"),
  ];
}

async function readLogLines(): Promise<{
  lines: string[];
  notFound: boolean;
  logPath: string | null;
}> {
  for (const p of logPaths()) {
    try {
      const content = await readFile(p, "utf-8");
      const lines = content.split(/\r?\n/).filter((l) => l.trim() !== "");
      return { lines, notFound: false, logPath: p };
    } catch {
      // try next candidate path
    }
  }
  return { lines: [], notFound: true, logPath: null };
}

// Empties the log file so activity starts fresh. The file is truncated
// (not deleted) because Windows locks the file while the MCP server has
// it open — the server keeps appending new entries after it is cleared.
async function clearLog(): Promise<{ error?: string }> {
  "use server";
  const { logPath } = await readLogLines();
  if (!logPath) return {}; // nothing to clear

  try {
    await writeFile(logPath, "");
  } catch (e) {
    return { error: e instanceof Error ? e.message : String(e) };
  }
  revalidatePath("/dashboard/activity");
  return {};
}

export default async function ActivityPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;
  const showAll = params.range === "all"; // default view: today only

  const { lines, notFound } = await readLogLines();
  const parsed = lines
    .map(parseLine)
    .filter((e): e is LogEntry => e !== null);

  // "Today" shows every entry from the current date; "All" falls back to
  // the last N log lines so the list stays bounded.
  const entries = (
    showAll
      ? parsed.slice(-LINES_SHOWN)
      : parsed.filter((e) => e.timestamp.slice(0, 10) === todayLocalDate())
  ).reverse(); // newest first

  const { date: todayDisplay } = formatTimestamp(`${todayLocalDate()} 00:00:00`);

  const successCount = entries.filter((e) => e.event === "OK").length;
  const errorCount = entries.filter(
    (e) => e.event === "FAIL" || e.event === "CRASH"
  ).length;
  const callCount = entries.filter((e) => e.event === "CALL").length;

  const chips = [
    { label: "Success", count: successCount, badge: "bg-emerald-100 text-emerald-700", dot: "bg-emerald-500" },
    { label: "Errors", count: errorCount, badge: "bg-rose-100 text-rose-700", dot: "bg-rose-500" },
    { label: "Called", count: callCount, badge: "bg-indigo-100 text-indigo-700", dot: "bg-indigo-500" },
  ];

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <AutoRefresh />
      <Nav />
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500 text-white">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center gap-3 mb-1">
            <span className="text-3xl">&#9889;</span>
            <h1 className="text-3xl font-bold tracking-tight">Activity</h1>
          </div>
          <p className="text-white/70 text-sm ml-12">
            Recent MCP tool calls from your booking agent
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Activity List */}
        <div className="bg-white rounded-2xl shadow-md overflow-hidden border border-gray-100">
          <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-gray-800">Recent Tool Calls</h2>
              <p className="text-xs text-gray-400 mt-0.5">
                {showAll
                  ? `Last ${LINES_SHOWN} log lines, newest first`
                  : `Today \u00B7 ${todayDisplay} \u00B7 newest first`}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center rounded-full bg-gray-100 p-0.5 shrink-0">
                <Link
                  href="/dashboard/activity"
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    !showAll
                      ? "bg-white shadow-sm text-indigo-600"
                      : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  Today
                </Link>
                <Link
                  href="/dashboard/activity?range=all"
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    showAll
                      ? "bg-white shadow-sm text-indigo-600"
                      : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  All
                </Link>
              </div>
              <div className="flex gap-2">
                {chips.map((c) => (
                  <span
                    key={c.label}
                    className={`${c.badge} text-xs font-medium px-2.5 py-1 rounded-full hidden sm:inline-flex items-center gap-1.5`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`}></span>
                    {c.label} ({c.count})
                  </span>
                ))}
              </div>
              {entries.length > 0 && <ClearLogButton clear={clearLog} />}
            </div>
          </div>

          <div className="divide-y divide-gray-50">
            {entries.length === 0 ? (
              <div className="px-6 py-16 text-center">
                <div className="text-4xl mb-3">&#128220;</div>
                <p className="text-gray-400 font-medium">
                  {notFound
                    ? "Log file not found"
                    : showAll
                      ? "No activity yet"
                      : "No activity yet today"}
                </p>
                <p className="text-gray-300 text-xs mt-1">
                  {notFound
                    ? "Expected logs/tool-calls.log in the project root"
                    : showAll
                      ? "Tool calls will appear here once the MCP server is used"
                      : "New tool calls will appear here as the booking agent is used"}
                </p>
              </div>
            ) : (
              entries.map((entry, i) => {
                const cfg = eventConfig(entry.event);
                const { date, time } = formatTimestamp(entry.timestamp);
                return (
                  <div
                    key={`${entry.timestamp}-${i}`}
                    className="flex items-start gap-4 px-6 py-4 hover:bg-indigo-50/40 transition-colors"
                  >
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-sm font-bold ${cfg.iconCls}`}
                    >
                      {cfg.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-sm font-semibold text-gray-800">
                          {entry.tool}
                        </span>
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${cfg.badge}`}
                        >
                          {cfg.label}
                        </span>
                      </div>
                      {entry.detail && (
                        <p className="text-xs text-gray-500 mt-1.5 break-words">
                          {entry.detail}
                        </p>
                      )}
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-xs font-medium text-gray-500">{time}</div>
                      <div className="text-xs text-gray-400 mt-0.5">{date}</div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
