import { revalidatePath } from "next/cache";
import Link from "next/link";
import Nav from "@/app/components/Nav";
import ClearLogButton from "./ClearLogButton";
import AutoRefresh from "./AutoRefresh";
import { createSupabaseServerClient } from "@/lib/supabaseServer";

// Always fetch fresh data - no ISR caching
export const revalidate = 0;

// Tool activity is stored in the Supabase tool_call_logs table (the MCP
// server writes it alongside its local file log), so the local and the
// Vercel-deployed dashboard read exactly the same data.
const CALLS_SHOWN = 20; // "All" view
const FETCH_LIMIT = 1000; // newest rows pulled for today-filtering

// created_at is stored UTC; render in the salon owner's timezone so the
// local and Vercel dashboards are identical regardless of server timezone.
const TIMEZONE = "Asia/Karachi";

interface ToolCallRow {
  id: string;
  tool_name: string;
  status: string;
  params: Record<string, unknown> | null;
  result: unknown;
  created_at: string;
}

async function fetchToolCalls(): Promise<{
  rows: ToolCallRow[];
  error: string | null;
}> {
  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("tool_call_logs")
    .select("id, tool_name, status, params, result, created_at")
    .order("created_at", { ascending: false })
    .limit(FETCH_LIMIT);
  if (error) return { rows: [], error: error.message };
  return { rows: (data ?? []) as ToolCallRow[], error: null };
}

// Calendar date (YYYY-MM-DD) of an instant in the dashboard timezone.
function zonedDateKey(value: Date | string): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(value));
}

function formatTimestamp(ts: string): { date: string; time: string } {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return { date: ts, time: "" };
  return {
    date: d.toLocaleDateString("en-IN", {
      timeZone: TIMEZONE,
      day: "2-digit",
      month: "short",
      year: "numeric",
    }),
    time: d.toLocaleTimeString("en-IN", {
      timeZone: TIMEZONE,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    }),
  };
}

// Short human-readable summary of a tool result (never raw JSON).
function resultSummary(result: unknown): string {
  if (result === null || result === undefined) return "";
  if (Array.isArray(result)) {
    return `${result.length} result${result.length === 1 ? "" : "s"} returned`;
  }
  if (typeof result === "object") {
    const obj = result as Record<string, unknown>;
    if (typeof obj.message === "string" && obj.message.trim()) {
      return obj.message;
    }
    const list = obj.appointments ?? obj.services ?? obj.available_slots ?? obj.pending_reminders;
    if (Array.isArray(list)) {
      return `${list.length} result${list.length === 1 ? "" : "s"} returned`;
    }
    if (obj.id !== undefined && obj.status !== undefined) {
      return `Appointment #${obj.id} \u2014 ${obj.status}`;
    }
    if (obj.id !== undefined && obj.reminder_sent !== undefined) {
      return `Reminder sent \u2014 appointment #${obj.id}`;
    }
    if (typeof obj.error === "string" && obj.error) return obj.error;
    return "";
  }
  return String(result);
}

function paramsSummary(params: Record<string, unknown> | null): string {
  if (!params) return "";
  const parts = Object.entries(params).map(([k, v]) => `${k}: ${String(v)}`);
  return parts.length > 0 ? parts.join(" \u00B7 ") : "";
}

function statusConfig(status: string) {
  if (status === "OK") {
    return {
      icon: "\u2713",
      iconCls: "bg-emerald-100 text-emerald-600",
      label: "Success",
      badge: "bg-emerald-100 text-emerald-700",
    };
  }
  return {
    icon: "\u2717",
    iconCls: "bg-rose-100 text-rose-600",
    label: "Error",
    badge: "bg-rose-100 text-rose-700",
  };
}

// Deletes today's rows (dashboard timezone) from tool_call_logs so the
// activity list starts fresh. This permanently deletes the rows from the
// database — the local logs/tool-calls.log file is NOT touched.
async function clearLog(): Promise<{ error?: string }> {
  "use server";
  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("tool_call_logs")
    .select("id, created_at")
    .order("created_at", { ascending: false })
    .limit(FETCH_LIMIT);
  if (error) return { error: error.message };

  const todayKey = zonedDateKey(new Date());
  const ids = (data ?? [])
    .filter((row) => zonedDateKey(row.created_at) === todayKey)
    .map((row) => row.id);
  if (ids.length === 0) return {};

  const { error: deleteError } = await supabase
    .from("tool_call_logs")
    .delete()
    .in("id", ids);
  if (deleteError) return { error: deleteError.message };

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

  const { rows, error: dbError } = await fetchToolCalls();
  const todayKey = zonedDateKey(new Date());

  // "Today" shows every call from the current date; "All" falls back to
  // the last N calls so the list stays bounded.
  const entries = showAll
    ? rows.slice(0, CALLS_SHOWN)
    : rows.filter((row) => zonedDateKey(row.created_at) === todayKey);

  const { date: todayDisplay } = formatTimestamp(new Date().toISOString());

  const successCount = entries.filter((e) => e.status === "OK").length;
  const errorCount = entries.filter((e) => e.status !== "OK").length;
  const callCount = entries.length;

  const chips = [
    { label: "Success", count: successCount, badge: "bg-emerald-100 text-emerald-700", dot: "bg-emerald-500" },
    { label: "Errors", count: errorCount, badge: "bg-rose-100 text-rose-700", dot: "bg-rose-500" },
    { label: "Calls", count: callCount, badge: "bg-indigo-100 text-indigo-700", dot: "bg-indigo-500" },
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
                  ? `Last ${CALLS_SHOWN} calls, newest first`
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
                  {dbError
                    ? "Could not load activity"
                    : showAll
                      ? "No activity yet"
                      : "No activity yet today"}
                </p>
                <p className="text-gray-300 text-xs mt-1">
                  {dbError
                    ? dbError
                    : showAll
                      ? "Tool calls will appear here once the MCP server is used"
                      : "New tool calls will appear here as the booking agent is used"}
                </p>
              </div>
            ) : (
              entries.map((entry) => {
                const cfg = statusConfig(entry.status);
                const { date, time } = formatTimestamp(entry.created_at);
                const summary = resultSummary(entry.result);
                const calledWith = paramsSummary(entry.params);
                return (
                  <div
                    key={entry.id}
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
                          {entry.tool_name}
                        </span>
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${cfg.badge}`}
                        >
                          {cfg.label}
                        </span>
                      </div>
                      {summary && (
                        <p className="text-xs text-gray-500 mt-1.5 break-words">{summary}</p>
                      )}
                      {calledWith && (
                        <p className="text-xs text-gray-400 mt-1 break-words">{calledWith}</p>
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
