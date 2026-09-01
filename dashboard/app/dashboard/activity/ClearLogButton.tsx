"use client";

import { useState } from "react";

export default function ClearLogButton({
  clear,
}: {
  clear: () => Promise<{ error?: string }>;
}) {
  const [pending, setPending] = useState(false);

  async function handleClear() {
    if (!window.confirm("Clear all activity? The log will start fresh.")) return;
    setPending(true);
    try {
      const result = await clear();
      if (result?.error) window.alert("Could not clear log: " + result.error);
    } finally {
      setPending(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleClear}
      disabled={pending}
      className="text-rose-600 hover:text-rose-800 text-xs font-medium px-3 py-1.5 rounded-lg hover:bg-rose-50 transition-colors disabled:opacity-50 whitespace-nowrap"
    >
      {pending ? "Clearing..." : "Clear Log"}
    </button>
  );
}
