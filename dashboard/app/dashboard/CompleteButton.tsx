"use client";

import { useState } from "react";

export default function CompleteButton({
  complete,
}: {
  complete: () => Promise<{ error?: string }>;
}) {
  const [pending, setPending] = useState(false);

  async function handleClick() {
    if (!window.confirm("Mark this appointment as completed?")) return;
    setPending(true);
    try {
      const result = await complete();
      if (result?.error) {
        window.alert("Could not complete appointment: " + result.error);
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={pending}
      className="text-emerald-600 hover:text-emerald-800 text-xs font-medium px-3 py-1.5 rounded-lg hover:bg-emerald-50 transition-colors disabled:opacity-50 whitespace-nowrap"
    >
      {pending ? "Completing..." : "Mark Complete"}
    </button>
  );
}
