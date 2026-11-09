import { readConfig } from "@/lib/config";
import { forward } from "@/lib/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
async function handle(request: Request) {
  try { return await forward(request, readConfig(process.env)); }
  catch { return Response.json({ detail: "Web API configuration is unavailable." }, { status: 503, headers: { "Cache-Control": "no-store" } }); }
}
export { handle as GET, handle as POST, handle as PUT, handle as PATCH, handle as DELETE, handle as OPTIONS };
