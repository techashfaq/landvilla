import type { Metadata } from "next";
import { AuthPanel } from "@/components/auth-panel";
export const metadata: Metadata = { title: "Account access" };
export default function LoginPage() {
  return <main id="main" className="container auth-layout"><section><span className="eyebrow">YOUR LANDVILLA ACCOUNT</span><h1>Good to<br /><em>have you here.</em></h1><p>Sign in with your verified contact details or Google. Your account stays with the existing LANDVILLA service.</p><div className="auth-aside"><strong>One account. One trusted connection.</strong><p>Secure browser cookies keep your session out of JavaScript-readable token storage.</p></div></section><AuthPanel /></main>;
}
