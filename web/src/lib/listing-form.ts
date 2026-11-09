export function listingInput(form: FormData, photoIds: string[]) {
  const str = (key: string) => String(form.get(key) || "").trim();
  const numeric = (key: string, min: number, max: number, optional = false) => {
    const raw = str(key); if (optional && !raw) return null;
    const value = Number(raw); if (!raw || !Number.isInteger(value) || value < min || value > max) throw new Error(`Check ${key.replaceAll("_", " ")}.`); return value;
  };
  if (str("title_en").length < 5 || str("title_en").length > 100 || str("description_en").length < 20 || str("description_en").length > 2000) throw new Error("Enter a title of 5–100 characters and description of 20–2000 characters.");
  if (!photoIds.length || photoIds.length > 10 || photoIds.some(id => !/^[a-zA-Z0-9_-]{1,100}$/.test(id))) throw new Error("Upload between 1 and 10 photographs.");
  if (form.get("declaration") !== "on") throw new Error("Confirm your authority to submit this property.");
  if (!["owner", "broker"].includes(str("posted_as")) || !["buy", "rent"].includes(str("purpose"))) throw new Error("Choose a listing role and purpose.");
  // Explicit request allowlist: ownership, moderation and publication are backend decisions.
  return { title_en: str("title_en"), description_en: str("description_en"), purpose: str("purpose"), posted_as: str("posted_as"), segment: str("segment"), type: str("type"), locality_id: str("locality_id"), price: numeric("price", 1000, 10_000_000_000), area_sqft: numeric("area_sqft", 50, 10_000_000), bhk: numeric("bhk", 1, 20, true), bathrooms: numeric("bathrooms", 0, 20, true), furnishing: str("furnishing") || null, amenities: form.getAll("amenities").map(String), photo_ids: [...new Set(photoIds)], owner_declaration_accepted: true, currency: "INR", city: "Ujjain", state: "Madhya Pradesh", address: str("address"), postal_code: str("postal_code") || null };
}
