import { createSupabaseServerClient } from "@/lib/supabaseServer";
import { revalidatePath } from "next/cache";
import Nav from "@/app/components/Nav";
import CompleteButton from "./CompleteButton";

// Always fetch fresh data - no ISR caching
export const revalidate = 0;

interface AppointmentRow {
  id: number;
  start_time: string;
  end_time: string;
  status: string;
  reminder_sent: boolean | null;
  customer_name_snapshot: string | null;
  customers: { name: string; phone: string } | null;
  services: { name: string } | null;
  staff: { name: string } | null;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

function statusConfig(status: string) {
  switch (status) {
    case "confirmed":
      return { bg: "bg-blue-100", text: "text-blue-700", dot: "bg-blue-500", icon: "\u2713" };
    case "completed":
      return { bg: "bg-emerald-100", text: "text-emerald-700", dot: "bg-emerald-500", icon: "\u2713" };
    case "cancelled":
      return { bg: "bg-rose-100", text: "text-rose-700", dot: "bg-rose-500", icon: "\u2717" };
    case "pending":
      return { bg: "bg-amber-100", text: "text-amber-700", dot: "bg-amber-500", icon: "\u25CF" };
    default:
      return { bg: "bg-gray-100", text: "text-gray-700", dot: "bg-gray-500", icon: "\u25CF" };
  }
}

// Mark an appointment as completed. Guarded by status='confirmed' so a
// stale page can never complete a cancelled/completed appointment.
async function completeAppointment(id: number): Promise<{ error?: string }> {
  "use server";
  const supabase = createSupabaseServerClient();
  const { error } = await supabase
    .from("appointments")
    .update({ status: "completed" })
    .eq("id", id)
    .eq("status", "confirmed");
  if (error) return { error: error.message };
  revalidatePath("/dashboard");
  return {};
}

export default async function DashboardPage() {
  const supabase = createSupabaseServerClient();

  const { data, error } = await supabase
    .from("appointments")
    .select(
      `id, start_time, end_time, status, reminder_sent, customer_name_snapshot, customers:customer_id ( name, phone ), services:service_id ( name ), staff:staff_id ( name )`
    )
    .order("start_time", { ascending: false });

  if (error) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gradient-to-br from-rose-50 to-orange-50">
        <div className="bg-white p-8 rounded-2xl shadow-lg max-w-md text-center border border-rose-100">
          <div className="text-4xl mb-3">&#9888;</div>
          <h1 className="text-xl font-bold text-rose-600 mb-2">
            Error loading appointments
          </h1>
          <p className="text-gray-500 text-sm">{error.message}</p>
        </div>
      </main>
    );
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const appointments = ((data as any) ?? []) as AppointmentRow[];

  // Stats
  const total = appointments.length;
  const confirmed = appointments.filter((a) => a.status === "confirmed").length;
  const pending = appointments.filter((a) => a.status === "pending").length;
  const completed = appointments.filter((a) => a.status === "completed").length;
  const cancelled = appointments.filter((a) => a.status === "cancelled").length;

  // Reminders due in the next 60 minutes (confirmed, not yet sent, start_time within window)
  const now = Date.now();
  const windowEnd = now + 60 * 60 * 1000;
  const dueSoon = appointments.filter((a) => {
    if (a.status !== "confirmed" || a.reminder_sent) return false;
    const t = new Date(a.start_time).getTime();
    return t >= now && t <= windowEnd;
  });

  const stats = [
    { label: "Total", value: total, gradient: "from-violet-500 to-purple-600", icon: "\uD83D\uDCCB" },
    { label: "Confirmed", value: confirmed, gradient: "from-blue-500 to-cyan-500", icon: "\u2705" },
    { label: "Pending", value: pending, gradient: "from-amber-400 to-orange-500", icon: "\u23F3" },
    { label: "Completed", value: completed, gradient: "from-emerald-500 to-teal-500", icon: "\u2705" },
    { label: "Cancelled", value: cancelled, gradient: "from-rose-500 to-pink-500", icon: "\u274C" },
  ];

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <Nav />
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500 text-white">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center gap-3 mb-1">
            <span className="text-3xl">&#9986;</span>
            <h1 className="text-3xl font-bold tracking-tight">
              Salon Dashboard
            </h1>
          </div>
          <p className="text-white/70 text-sm ml-12">
            Manage and track all your appointments in one place
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 -mt-4">
        {/* Reminders due banner */}
        {dueSoon.length > 0 && (
          <div className="mb-4 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-2xl shadow-sm px-6 py-4 flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center text-amber-600 text-xl shrink-0">
              &#9200;
            </div>
            <div>
              <p className="font-bold text-amber-800">
                Reminders due in next hour:{" "}
                <span className="text-amber-600">{dueSoon.length}</span>
              </p>
              <p className="text-xs text-amber-600/70 mt-0.5">
                {dueSoon
                  .map(
                    (a) =>
                      `${a.customer_name_snapshot ?? a.customers?.name ?? "Customer"} @ ${formatTime(a.start_time)}`
                  )
                  .join(" \u00B7 ")}
              </p>
            </div>
          </div>
        )}

        {/* Stat Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
          {stats.map((s) => (
            <div
              key={s.label}
              className="bg-white rounded-2xl shadow-md hover:shadow-lg transition-shadow p-5 border border-white"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-lg">{s.icon}</span>
                <span
                  className={`text-xs font-semibold px-2.5 py-1 rounded-full bg-gradient-to-r ${s.gradient} text-white`}
                >
                  {s.label}
                </span>
              </div>
              <p className="text-2xl font-bold text-gray-800">{s.value}</p>
            </div>
          ))}
        </div>

        {/* Table */}
        <div className="bg-white rounded-2xl shadow-md overflow-hidden border border-gray-100 mb-10">
          <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-gray-800">
                All Appointments
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Latest appointments first
              </p>
            </div>
            <div className="flex gap-2">
              {["confirmed", "pending", "completed", "cancelled"].map((s) => {
                const cfg = statusConfig(s);
                const count = appointments.filter((a) => a.status === s).length;
                return (
                  <span
                    key={s}
                    className={`${cfg.bg} ${cfg.text} text-xs font-medium px-2.5 py-1 rounded-full capitalize hidden sm:inline-flex items-center gap-1.5`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`}></span>
                    {s} ({count})
                  </span>
                );
              })}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gradient-to-r from-gray-50 to-slate-50">
                  <th className="px-6 py-4 text-left font-semibold text-gray-500 uppercase text-xs tracking-wider">
                    Time
                  </th>
                  <th className="px-6 py-4 text-left font-semibold text-gray-500 uppercase text-xs tracking-wider">
                    Customer
                  </th>
                  <th className="px-6 py-4 text-left font-semibold text-gray-500 uppercase text-xs tracking-wider">
                    Phone
                  </th>
                  <th className="px-6 py-4 text-left font-semibold text-gray-500 uppercase text-xs tracking-wider">
                    Service
                  </th>
                  <th className="px-6 py-4 text-left font-semibold text-gray-500 uppercase text-xs tracking-wider">
                    Staff
                  </th>
                  <th className="px-6 py-4 text-left font-semibold text-gray-500 uppercase text-xs tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left font-semibold text-gray-500 uppercase text-xs tracking-wider">
                    Reminder
                  </th>
                  <th className="px-6 py-4 text-right font-semibold text-gray-500 uppercase text-xs tracking-wider">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {appointments.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-6 py-16 text-center">
                      <div className="text-4xl mb-3">&#128197;</div>
                      <p className="text-gray-400 font-medium">
                        No appointments yet
                      </p>
                      <p className="text-gray-300 text-xs mt-1">
                        Appointments will appear here once created
                      </p>
                    </td>
                  </tr>
                ) : (
                  appointments.map((apt) => {
                    const cfg = statusConfig(apt.status);
                    return (
                      <tr
                        key={apt.id}
                        className="hover:bg-indigo-50/40 transition-colors"
                      >
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="font-medium text-gray-800">
                            {formatTime(apt.start_time)}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-white text-xs font-bold shrink-0">
                              {(apt.customer_name_snapshot ?? apt.customers?.name ?? "?").charAt(0).toUpperCase()}
                            </div>
                            <span className="font-medium text-gray-800">
                              {apt.customer_name_snapshot ?? apt.customers?.name ?? "-"}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-gray-500 font-mono text-xs">
                          {apt.customers?.phone ?? "-"}
                        </td>
                        <td className="px-6 py-4">
                          <span className="font-medium text-gray-700">
                            {apt.services?.name ?? "-"}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-gray-600">
                          {apt.staff?.name ?? "-"}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`}></span>
                            <span className="capitalize">{apt.status}</span>
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          {(() => {
                            if (apt.status === "cancelled" || apt.status === "completed") {
                              return <span className="text-gray-300 text-xs">&mdash;</span>;
                            }
                            if (apt.reminder_sent) {
                              return (
                                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700">
                                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                                  &#10003; Sent
                                </span>
                              );
                            }
                            const t = new Date(apt.start_time).getTime();
                            if (t >= now && t <= windowEnd && apt.status === "confirmed") {
                              return (
                                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-700">
                                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
                                  &#9200; Due Soon
                                </span>
                              );
                            }
                            return (
                              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-500">
                                <span className="w-1.5 h-1.5 rounded-full bg-gray-400"></span>
                                Not yet
                              </span>
                            );
                          })()}
                        </td>
                        <td className="px-6 py-4 text-right">
                          {apt.status === "confirmed" && (
                            <CompleteButton
                              complete={completeAppointment.bind(null, apt.id)}
                            />
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>
  );
}
