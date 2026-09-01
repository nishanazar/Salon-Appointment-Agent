import { createSupabaseServerClient } from "@/lib/supabaseServer";
import { revalidatePath } from "next/cache";
import Nav from "@/app/components/Nav";
import { HoursEditor } from "./HoursEditor";

export const revalidate = 0;

async function saveHours(formData: FormData) {
  "use server";
  const dayOfWeek = parseInt(formData.get("day_of_week") as string);
  const openTime = formData.get("start_time") as string;
  const closeTime = formData.get("end_time") as string;

  if (isNaN(dayOfWeek) || dayOfWeek < 0 || dayOfWeek > 6)
    throw new Error("Invalid day");
  if (!openTime || !closeTime)
    throw new Error("Both open and close times are required");

  const supabase = createSupabaseServerClient();

  const { data: existing } = await supabase
    .from("working_hours")
    .select("id")
    .eq("day_of_week", dayOfWeek)
    .maybeSingle();

  if (!existing) {
    const { error } = await supabase.from("working_hours").insert({
      day_of_week: dayOfWeek,
      start_time: openTime,
      end_time: closeTime,
    });
    if (error) throw new Error(error.message);
  } else {
    const { error } = await supabase
      .from("working_hours")
      .update({ start_time: openTime, end_time: closeTime })
      .eq("id", existing.id);
    if (error) throw new Error(error.message);
  }

  revalidatePath("/dashboard/hours");
  return {};
}

async function deleteHours(id: string) {
  "use server";
  const supabase = createSupabaseServerClient();
  const { error } = await supabase
    .from("working_hours")
    .delete()
    .eq("id", id);
  if (error) throw new Error(error.message);
  revalidatePath("/dashboard/hours");
}

const DAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

export default async function HoursPage() {
  const supabase = createSupabaseServerClient();
  const { data } = await supabase
    .from("working_hours")
    .select("*")
    .order("day_of_week");

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const hours = (data ?? []) as any[];
  const hoursMap = new Map<number, (typeof hours)[0]>();
  hours.forEach((h) => hoursMap.set(h.day_of_week, h));

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <Nav />
      <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500 text-white">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center gap-3 mb-1">
            <span className="text-3xl">&#128338;</span>
            <h1 className="text-3xl font-bold tracking-tight">Working Hours</h1>
          </div>
          <p className="text-white/70 text-sm ml-12">
            Set opening and closing times for each day
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {DAYS.map((day, index) => {
            const h = hoursMap.get(index);
            return (
              <div
                key={day}
                className="bg-white rounded-2xl shadow-md p-6 border border-gray-100"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-bold text-gray-800">{day}</h3>
                  {h ? (
                    <span className="bg-emerald-100 text-emerald-700 text-xs font-semibold px-2.5 py-1 rounded-full">
                      {h.start_time?.slice(0, 5)} – {h.end_time?.slice(0, 5)}
                    </span>
                  ) : (
                    <span className="bg-rose-100 text-rose-600 text-xs font-semibold px-2.5 py-1 rounded-full">
                      Closed
                    </span>
                  )}
                </div>

                <HoursEditor
                  action={async (formData: FormData) => {
                    "use server";
                    formData.set("day_of_week", String(index));
                    return saveHours(formData);
                  }}
                  initialOpen={h?.start_time?.slice(0, 5)}
                  initialClose={h?.end_time?.slice(0, 5)}
                  showInitially={!!h}
                />

                {h && (
                  <form action={deleteHours.bind(null, h.id)} className="mt-3">
                    <input type="hidden" name="day_of_week" value={index} />
                    <button
                      type="submit"
                      className="text-rose-500 hover:text-rose-700 text-xs font-medium"
                    >
                      Remove hours
                    </button>
                  </form>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </main>
  );
}
