import Link from "next/link";
import { AccountGate } from "@/components/account/account-gate";
export const metadata = { title: "Your account", robots: { index: false, follow: false } };
export default function Layout({ children }: { children: React.ReactNode }) { return <main id="main" className="container section stack"><nav className="account-nav" aria-label="Account"><Link href="/account">Profile</Link><Link href="/account/saved">Saved</Link><Link href="/account/enquiries">Enquiries</Link><Link href="/account/listings">My properties</Link><Link href="/account/leads">Leads</Link><Link href="/account/broker">Broker status</Link><Link href="/login">Session & sign out</Link></nav><AccountGate>{children}</AccountGate></main>; }
