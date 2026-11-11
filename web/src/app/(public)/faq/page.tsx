import { publishedContent } from "@/lib/published-content";
export const metadata = { title: "Frequently asked questions" };
export const dynamic = "force-dynamic";
export default async function Page() {
  const items = await publishedContent("faq");
  return <main id="main" className="container section stack legal"><h1>Frequently asked questions</h1>{items.length ? items.map(item => <section key={item.id}><h2>{item.title}</h2><p style={{ whiteSpace: "pre-wrap" }}>{item.body}</p></section>) : <p>Approved frequently asked questions are not available yet. Please check again later.</p>}</main>;
}
