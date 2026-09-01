"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/dashboard", label: "Appointments", icon: "\uD83D\uDCCB" },
  { href: "/dashboard/services", label: "Services", icon: "\u2728" },
  { href: "/dashboard/staff", label: "Staff", icon: "\uD83D\uDC65" },
  { href: "/dashboard/hours", label: "Hours", icon: "\uD83D\uDD52" },
  { href: "/dashboard/activity", label: "Activity", icon: "\u26A1" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex gap-1 overflow-x-auto">
          {links.map((l) => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`flex items-center gap-1.5 px-4 py-3.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  active
                    ? "border-indigo-600 text-indigo-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                <span>{l.icon}</span>
                {l.label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
