"use client";
import { useState } from "react";
import { copyPropertyLink } from "@/lib/share-link";
export function ShareProperty() {
  const [message,setMessage] = useState("");
  return <div><button type="button" className="button secondary" onClick={() => { void copyPropertyLink(window.location, navigator.clipboard).then(setMessage); }}>Copy property link</button>{message && <p role="status">{message}</p>}</div>;
}
