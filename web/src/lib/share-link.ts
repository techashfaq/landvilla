/** Copy only the public page path; never include query strings or fragments. */
export async function copyPropertyLink(location: Pick<Location, "origin" | "pathname">, clipboard?: Pick<Clipboard, "writeText">): Promise<string> {
  const fallback = "Copy the address from your browser to share this property.";
  if (!clipboard || typeof clipboard.writeText !== "function") return fallback;
  try {
    await clipboard.writeText(location.origin + location.pathname);
    return "Property link copied.";
  } catch { return fallback; }
}
