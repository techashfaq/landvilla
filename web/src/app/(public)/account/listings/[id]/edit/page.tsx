import { notFound } from "next/navigation";
import { ListingForm } from "@/components/account/listing-form";
export default async function Page({ params }: { params: Promise<{ id: string }> }) { const { id } = await params; if (!/^[a-zA-Z0-9_-]{1,100}$/.test(id)) notFound(); return <ListingForm id={id} />; }
