"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { adminSections } from "@/lib/admin-resources";
export function AdminNav() {
  const path = usePathname();
  const links = [["/admin", "Overview"], ...Object.entries(adminSections).map(([key, value]) => ["/admin/" + key, value.title])];
  return <nav className="stack" style={{ gap: 8 }} aria-label="Admin navigation">{links.map(([href, label]) => <Link key={href} href={href!} aria-current={path === href ? "page" : undefined}>{label}</Link>)}</nav>;
}
