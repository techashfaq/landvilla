import { readConfig } from "@/lib/config";
import { forward } from "@/lib/proxy";
import { ingressIdentity } from "@/lib/ingress-identity";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
async function handle(request: Request) {
  try {
    const config = readConfig(process.env);
    const identity = config.production ? ingressIdentity(request, process.env) : undefined;
    return await forward(request, config, fetch, identity);
  }
  catch { return Response.json({ detail: "Web API configuration is unavailable." }, { status: 503, headers: { "Cache-Control": "no-store" } }); }
}
export { handle as GET, handle as POST, handle as PUT, handle as PATCH, handle as DELETE, handle as OPTIONS };
