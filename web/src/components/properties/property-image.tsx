"use client";
import { useState } from "react";
export function PropertyImage({ src, alt }: { src?: string; alt: string }) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) return <div className="image-empty" role="img" aria-label="Property photograph unavailable">Photograph unavailable</div>;
  // Direct, unoptimized image: authenticated/private media must never enter a public optimizer.
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={alt} loading="lazy" decoding="async" referrerPolicy="no-referrer" onError={() => setFailed(true)} />;
}
