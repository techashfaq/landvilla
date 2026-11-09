import { notFound } from "next/navigation";
import { Conversation } from "@/components/account/conversation";
export default async function Page({ params }: { params: Promise<{ section: string; id: string }> }) { const { section, id } = await params; if (!["enquiries", "leads"].includes(section) || !/^[a-zA-Z0-9_-]{1,100}$/.test(id)) notFound(); return <Conversation id={id} owner={section === "leads"} />; }
