import Link from "next/link";
import { HomeDiscovery } from "@/components/properties/home-discovery";
export const dynamic = "force-dynamic";

export default function Home() {
  return <main id="main">
    <section className="hero container" aria-labelledby="hero-title">
      <div className="hero-copy"><span className="eyebrow"><span className="dot" /> ROOTED IN UJJAIN</span><h1 id="hero-title">Your next chapter.<br /><em>A place to belong.</em></h1><p className="hero-description">A thoughtful way to discover real estate, connect with people and find your place in the city.</p><div className="hero-actions"><Link className="button" href="/properties">Discover properties <span aria-hidden="true">↗</span></Link><a className="text-link" href="#approach">Explore our approach <span aria-hidden="true">↓</span></a></div><p className="launch-note">Explore Ujjain listings. Fictional demonstrations are explicitly labelled.</p></div>
      <div className="architectural-art" role="img" aria-label="Original abstract architectural illustration in warm terracotta and sandstone. Not a property listing."><div className="art-sun" /><div className="art-building back"><i /><i /><i /></div><div className="art-building front"><div className="art-arch" /><div className="art-window" /></div><div className="art-ground" /><span className="art-caption">UJJAIN / MADHYA PRADESH<br /><small>An original LANDVILLA illustration</small></span></div>
    </section>
    <HomeDiscovery />
    <section className="container section" id="approach"><div className="section-heading"><div><span className="eyebrow">THE LANDVILLA APPROACH</span><h2>Clarity at every step.</h2></div><p>Real estate is personal.<br />The experience should feel that way.</p></div><div className="principles"><article><span className="step">01 / DISCOVER</span><h3>Start with the place.</h3><p>Search by locality, property type and budget to focus on what matters to you.</p></article><article><span className="step">02 / UNDERSTAND</span><h3>Details before decisions.</h3><p>Clear information, honest status labels and careful review. Moderation never replaces independent legal due diligence.</p></article><article><span className="step">03 / CONNECT</span><h3>People, with privacy.</h3><p>Account access uses LANDVILLA’s existing secure backend. Enquiries and property submissions will follow in later phases.</p></article></div></section>
    <section className="container invitation"><div><span className="eyebrow">MAKE YOURSELF AT HOME</span><h2>A shared place for<br />your property journey.</h2><p>Buyer, owner or broker — start with your LANDVILLA account.</p></div><Link href="/login" className="button light">Access your account <span aria-hidden="true">↗</span></Link></section>
  </main>;
}
