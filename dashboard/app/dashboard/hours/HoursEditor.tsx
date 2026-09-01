"use client";

import { useState } from "react";

export function HoursEditor({
  action,
  initialOpen,
  initialClose,
  showInitially,
}: {
  action: (formData: FormData) => Promise<{ error?: string }>;
  initialOpen?: string;
  initialClose?: string;
  showInitially?: boolean;
}) {
  const [showForm, setShowForm] = useState(showInitially ?? false);
  const [pending, startTransition] = useState(false);

  function handleSubmit(formData: FormData) {
    startTransition(true);
    action(formData).then(() => startTransition(false));
  }

  if (!showForm) {
    return (
      <button
        onClick={() => setShowForm(true)}
        className="text-indigo-600 hover:text-indigo-800 text-sm font-medium px-4 py-2 rounded-lg hover:bg-indigo-50 transition-colors"
      >
        + Add hours
      </button>
    );
  }

  return (
    <form action={handleSubmit} className="flex items-end gap-3">
      <div>
        <label className="block text-xs text-gray-500 mb-1">Open</label>
        <input
          name="start_time"
          type="time"
          required
          defaultValue={initialOpen ?? "11:00"}
          className="px-3 py-2 rounded-lg border border-gray-200 text-sm focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400 outline-none"
        />
      </div>
      <div>
        <label className="block text-xs text-gray-500 mb-1">Close</label>
        <input
          name="end_time"
          type="time"
          required
          defaultValue={initialClose ?? "20:00"}
          className="px-3 py-2 rounded-lg border border-gray-200 text-sm focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400 outline-none"
        />
      </div>
      <button
        type="submit"
        disabled={pending}
        className="px-5 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-medium text-sm hover:shadow-lg transition-shadow disabled:opacity-50"
      >
        {pending ? "Saving..." : initialOpen ? "Update" : "Save"}
      </button>
    </form>
  );
}
