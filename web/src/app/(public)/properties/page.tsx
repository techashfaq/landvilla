import { Discovery, type SearchParams } from "@/components/properties/discovery";
export const dynamic = "force-dynamic";
export const metadata = { title: "Properties in Ujjain" };
export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) { return <Discovery params={await searchParams} />; }
