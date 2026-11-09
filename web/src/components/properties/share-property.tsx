"use client";
import { useState } from "react";
export function ShareProperty() {
  const [message,setMessage] = useState("");
  return <div><button className="button secondary" onClick={() => { void navigator.clipboard.writeText(window.location.origin + window.location.pathname).then(() => setMessage("Property link copied.")).catch(() => setMessage("Copy the address from your browser to share this property.")); }}>Copy property link</button>{message && <p role="status">{message}</p>}</div>;
}
