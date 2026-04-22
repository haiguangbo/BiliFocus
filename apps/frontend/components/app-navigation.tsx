"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { BookMarked, Compass, Settings2 } from "lucide-react";

const NAV_ITEMS = [
  {
    href: "/",
    label: "内容探索",
    icon: Compass,
  },
  {
    href: "/library",
    label: "本地片库",
    icon: BookMarked,
  },
  {
    href: "/settings",
    label: "偏好设置",
    icon: Settings2,
  },
];

export function AppNavigation() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-wrap gap-2">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            className={`inline-flex items-center gap-2 rounded-full border px-4 py-2.5 text-sm font-medium transition ${
              active
                ? "border-blue-200 bg-blue-50 text-blue-700 shadow-sm"
                : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-900"
            }`}
            href={item.href}
          >
            <Icon className="h-4 w-4" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
