import { health } from "@/lib/health";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET() { return health(process.env); }
