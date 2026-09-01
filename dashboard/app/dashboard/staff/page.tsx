import { createSupabaseServerClient } from "@/lib/supabaseServer";
import { revalidatePath } from "next/cache";
import Nav from "@/app/components/Nav";

export const revalidate = 0;

async function addStaff(formData: FormData) {
  "use server";
  const name = (formData.get("name") as string)?.trim();
  if (!name) throw new Error("Staff name is required");

  const supabase = createSupabaseServerClient();
  const { error } = await supabase
    .from("staff")
    .insert({ name, active: true });
  if (error) throw new Error(error.message);
  revalidatePath("/dashboard/staff");
}

async function deactivateStaff(id: string) {
  "use server";
  const supabase = createSupabaseServerClient();
  const { error } = await supabase
    .from("staff")
    .update({ active: false })
    .eq("id", id);
  if (error) throw new Error(error.message);
  revalidatePath("/dashboard/staff");
}

async function activateStaff(id: string) {
  "use server";
  const supabase = createSupabaseServerClient();
  const { error } = await supabase
    .from("staff")
    .update({ active: true })
    .eq("id", id);
  if (error) throw new Error(error.message);
  revalidatePath("/dashboard/staff");
}

export default async function StaffPage() {
  const supabase = createSupabaseServerClient();
  const { data } = await supabase
    .from("staff")
    .select("*")
    .order("name");

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const staffList = (data ?? []) as any[];

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <Nav />
      <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500 text-white">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center gap-3 mb-1">
            <span className="text-3xl">&#128101;</span>
            <h1 className="text-3xl font-bold tracking-tight">Staff</h1>
          </div>
          <p className="text-white/70 text-sm ml-12">
            Manage your salon staff members
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Add Staff Form */}
        <div className="bg-white rounded-2xl shadow-md p-6 border border-gray-100">
          <h2 className="text-lg font-bold text-gray-800 mb-4">
            Add New Staff Member
          </h2>
          <form action={addStaff} className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-600 mb-1">
                Name
              </label>
              <input
                name="name"
                required
                placeholder="e.g. Ayesha"
                className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400 outline-none text-sm"
              />
            </div>
            <button
              type="submit"
              className="px-6 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl font-medium text-sm hover:shadow-lg transition-shadow"
            >
              + Add Staff
            </button>
          </form>
        </div>

        {/* Staff List */}
        <div className="bg-white rounded-2xl shadow-md overflow-hidden border border-gray-100">
          <div className="px-6 py-5 border-b border-gray-100">
            <h2 className="text-lg font-bold text-gray-800">All Staff</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              {staffList.length} member{staffList.length !== 1 && "s"}
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gradient-to-r from-gray-50 to-slate-50">
                  <th className="px-6 py-4 text-left font-semibold text-gray-500 uppercase text-xs tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-4 text-left font-semibold text-gray-500 uppercase text-xs tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-4 text-right font-semibold text-gray-500 uppercase text-xs tracking-wider">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {staffList.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-6 py-16 text-center">
                      <div className="text-4xl mb-3">&#128101;</div>
                      <p className="text-gray-400 font-medium">
                        No staff members yet
                      </p>
                      <p className="text-gray-300 text-xs mt-1">
                        Add your first staff member above
                      </p>
                    </td>
                  </tr>
                ) : (
                  staffList.map(
                    (s: { id: string; name: string; active: boolean }) => (
                      <tr
                        key={s.id}
                        className="hover:bg-indigo-50/40 transition-colors"
                      >
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-white text-xs font-bold shrink-0">
                              {s.name.charAt(0).toUpperCase()}
                            </div>
                            <span className="font-medium text-gray-800">
                              {s.name}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${
                              s.active
                                ? "bg-emerald-100 text-emerald-700"
                                : "bg-gray-100 text-gray-500"
                            }`}
                          >
                            {s.active ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          {s.active ? (
                            <form action={deactivateStaff.bind(null, s.id)}>
                              <button
                                type="submit"
                                className="text-rose-600 hover:text-rose-800 text-xs font-medium px-3 py-1.5 rounded-lg hover:bg-rose-50 transition-colors"
                              >
                                Deactivate
                              </button>
                            </form>
                          ) : (
                            <form action={activateStaff.bind(null, s.id)}>
                              <button
                                type="submit"
                                className="text-emerald-600 hover:text-emerald-800 text-xs font-medium px-3 py-1.5 rounded-lg hover:bg-emerald-50 transition-colors"
                              >
                                Activate
                              </button>
                            </form>
                          )}
                        </td>
                      </tr>
                    )
                  )
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>
  );
}
