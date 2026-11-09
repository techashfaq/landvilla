import Link from "next/link";

export function Brand() {
  return <Link className="brand" href="/" aria-label="LANDVILLA home"><span className="brand-mark" aria-hidden="true">L<span>V</span></span><span>LANDVILLA<small>A place to belong.</small></span></Link>;
}
export function SiteHeader() {
  return <header className="site-header"><div className="container header-inner"><Brand /><nav aria-label="Main navigation"><Link href="/buy">Buy</Link><Link href="/rent">Rent</Link><Link href="/properties">Discover Ujjain</Link><Link className="nav-account" href="/account">Account <span aria-hidden="true">↗</span></Link></nav></div></header>;
}
