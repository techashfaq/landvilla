export const mediaTypes = ["image/jpeg", "image/png", "image/webp", "application/pdf"];
export function mediaRoute(method: string, path: string) { return (method === "POST" && path === "/api/uploads") || (method === "GET" && /^\/api\/files\/[a-zA-Z0-9_-]{1,100}$/.test(path)); }
export async function limitedBody(request: Request, max: number) {
  if (Number(request.headers.get("content-length") || 0) > max) throw new Error("Request too large.");
  const chunks: Uint8Array[] = []; let length = 0; const reader = request.body?.getReader();
  if (reader) while (true) { const chunk = await reader.read(); if (chunk.done) break; length += chunk.value.length; if (length > max) { await reader.cancel(); throw new Error("Request too large."); } chunks.push(chunk.value); }
  const bytes = new Uint8Array(length); let offset = 0; for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; } return bytes;
}
export async function validateUpload(form: FormData) {
  if ([...form.keys()].some(key => !["file", "kind"].includes(key)) || form.getAll("file").length !== 1 || form.getAll("kind").length !== 1) throw new Error("Choose one file and an upload kind.");
  const file = form.get("file"), kind = form.get("kind");
  if (!(file instanceof File) || !["property_photo", "broker_doc"].includes(String(kind))) throw new Error("Invalid upload.");
  const max = kind === "property_photo" ? 8 : 10;
  const type = file.type.toLowerCase();
  if (!file.size || file.size > max * 1024 * 1024 || !mediaTypes.includes(type) || (kind === "property_photo" && type === "application/pdf")) throw new Error(`Choose a supported file up to ${max} MB.`);
  const extensions: Record<string, RegExp> = { "image/jpeg": /\.jpe?g$/i, "image/png": /\.png$/i, "image/webp": /\.webp$/i, "application/pdf": /\.pdf$/i };
  if (!extensions[type]?.test(file.name)) throw new Error("File extension does not match its type.");
  const bytes = new Uint8Array(await file.slice(0, 12).arrayBuffer()); const ascii = new TextDecoder().decode(bytes);
  const valid = type === "image/jpeg" ? bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255 : type === "image/png" ? [137,80,78,71,13,10,26,10].every((b,i) => bytes[i] === b) : type === "image/webp" ? ascii.startsWith("RIFF") && ascii.slice(8,12) === "WEBP" : ascii.startsWith("%PDF-");
  if (!valid) throw new Error("File contents do not match the selected type.");
  return form;
}
