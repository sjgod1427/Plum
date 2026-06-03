"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const userLinks = [
  { label: "Submit Claim", href: "/claims/new" },
  { label: "Dashboard", href: "/dashboard" },
];

const adminLinks = [
  { label: "Appeals", href: "/admin/appeals" },
  { label: "Policy", href: "/admin/policy" },
  { label: "Metrics", href: "/admin/metrics" },
];

export default function Navbar() {
  const path = usePathname();

  const isActive = (href: string) =>
    path === href || (href !== "/" && path.startsWith(href));

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-14 bg-plum-900 border-b border-plum-700 flex items-center px-6 gap-6">
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2 shrink-0 mr-2">
        <span className="text-lg">🫐</span>
        <span className="text-white font-bold text-base tracking-tight">Plum</span>
        <span className="text-plum-400 text-xs font-normal hidden sm:inline">Claims</span>
      </Link>

      {/* User nav */}
      <nav className="flex items-center gap-1">
        {userLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              isActive(link.href)
                ? "bg-plum-600 text-white"
                : "text-plum-200 hover:bg-plum-800 hover:text-white"
            }`}
          >
            {link.label}
          </Link>
        ))}
      </nav>

      {/* Separator */}
      <div className="h-5 w-px bg-plum-700 mx-1" />

      {/* Admin nav */}
      <nav className="flex items-center gap-1">
        <span className="text-plum-500 text-xs font-semibold uppercase tracking-wider mr-1">
          Admin
        </span>
        {adminLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              isActive(link.href)
                ? "bg-indigo-600 text-white"
                : "text-plum-300 hover:bg-plum-800 hover:text-white"
            }`}
          >
            {link.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
