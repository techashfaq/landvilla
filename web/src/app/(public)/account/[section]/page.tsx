import { notFound } from "next/navigation";
import { AccountPanel } from "@/components/account/account-panel";
export default async function Page({ params }: { params: Promise<{ section: string }> }) { const { section } = await params; if (section !== "saved" && section !== "enquiries" && section !== "listings" && section !== "leads" && section !== "broker") notFound(); return <AccountPanel key={section} kind={section} />; }
