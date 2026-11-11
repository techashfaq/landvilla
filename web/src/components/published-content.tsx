import Link from "next/link";
import { publishedContent } from "@/lib/published-content";
export async function PublishedContent({ kind }: { kind: "home-banner" | "faq" | "support" }) {
  const items = await publishedContent(kind);
  if (!items.length) return null;
  return <section className="container section stack" aria-label={kind === "home-banner" ? "Marketplace announcements" : kind === "faq" ? "Published FAQs" : "Support information"}>{items.map(item => <article className="panel stack" key={item.id}><h2>{item.title}</h2><p style={{ whiteSpace: "pre-wrap" }}>{item.body}</p>{item.link && <Link href={item.link}>Learn more</Link>}</article>)}</section>;
}
