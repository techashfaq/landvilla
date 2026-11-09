import type { Metadata } from "next";
import { SessionProvider } from "@/components/session-provider";
import "./globals.css";
import { canonicalOrigin } from "@/lib/seo";

export const metadata: Metadata = {
  title: { default: "LANDVILLA — A place to belong", template: "%s | LANDVILLA" },
  description: "Discover properties in Ujjain with LANDVILLA. Real estate journeys rooted in Madhya Pradesh.",
  metadataBase: canonicalOrigin(process.env) ? new URL(canonicalOrigin(process.env)!) : null,
  robots: { index: false, follow: false },
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><a className="skip-link" href="#main">Skip to content</a><SessionProvider>{children}</SessionProvider></body></html>;
}
