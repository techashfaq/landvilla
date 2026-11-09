"use client";
import { useState } from "react";
import { PropertyImage } from "./property-image";
export function Gallery({ images, title }: { images: string[]; title: string }) {
  const [selected, setSelected] = useState(0);
  return <section className="gallery" aria-label="Property photographs"><div className="gallery-main"><PropertyImage key={images[selected] || "empty"} src={images[selected]} alt={`${title} — photograph ${selected + 1}`} /></div>{images.length > 1 && <div className="gallery-controls">{images.map((image, index) => <button key={`${image}-${index}`} type="button" className="button secondary" aria-pressed={index === selected} onClick={() => setSelected(index)}>Photo {index + 1}</button>)}</div>}</section>;
}
