"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { FilePlus2, LayoutGrid, Search } from "lucide-react";

const userLinks = [
  { label: "Submit Claim", href: "/claims/new", icon: FilePlus2 },
  { label: "Dashboard", href: "/dashboard", icon: LayoutGrid },
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
    <header className="fixed top-0 left-0 right-0 z-50 h-[60px] bg-plum-dark/90 backdrop-blur-md border-b border-white/[0.06] flex items-center px-7 gap-7">
      {/* Logo */}
      <Link href="/" className="relative shrink-0 mr-2">
        <span className="text-[20px] font-bold tracking-tight text-coral">plum</span>
        <span className="absolute -right-2.5 top-1.5 h-1 w-1 rounded-full bg-coral" />
      </Link>

      {/* User nav */}
      <nav className="flex items-center gap-1">
        {userLinks.map((link) => {
          const Icon = link.icon;
          const active = isActive(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`relative flex items-center gap-2 px-3.5 py-2 rounded-[9px] text-sm transition-colors duration-200 ${
                active ? "text-white font-medium" : "text-white/50 hover:bg-white/[0.04] hover:text-white/85"
              }`}
            >
              {active && (
                <motion.span
                  layoutId="nav-active"
                  className="absolute inset-0 -z-10 rounded-[9px] bg-white/[0.09]"
                  transition={{ type: "spring", stiffness: 380, damping: 32 }}
                />
              )}
              <Icon size={14} strokeWidth={1.8} />
              {link.label}
            </Link>
          );
        })}
      </nav>

      {/* Separator */}
      <div className="h-[22px] w-px bg-white/[0.09] mx-1" />

      {/* Admin nav */}
      <nav className="flex items-center gap-1">
        <span className="text-[9.5px] font-semibold uppercase tracking-[0.15em] text-white/25 mr-2">
          Admin
        </span>
        {adminLinks.map((link) => {
          const active = isActive(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`relative px-3.5 py-2 rounded-[9px] text-sm transition-colors duration-200 ${
                active ? "text-white font-medium" : "text-white/50 hover:bg-white/[0.04] hover:text-white/85"
              }`}
            >
              {active && (
                <motion.span
                  layoutId="nav-active"
                  className="absolute inset-0 -z-10 rounded-[9px] bg-white/[0.09]"
                  transition={{ type: "spring", stiffness: 380, damping: 32 }}
                />
              )}
              {link.label}
            </Link>
          );
        })}
      </nav>

      {/* Right cluster */}
      <div className="ml-auto flex items-center gap-3.5">
        <Search size={17} strokeWidth={1.8} className="text-white/40" />
        <div className="flex h-[30px] w-[30px] items-center justify-center rounded-full bg-gradient-to-br from-verdict-violet to-coral text-xs font-semibold text-white">
          SJ
        </div>
      </div>
    </header>
  );
}
