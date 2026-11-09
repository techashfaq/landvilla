// Web uses IndependentGoogle.web.tsx and its browser-bound GIS nonce, never a native module.
export async function requestNativeGoogleToken(): Promise<string | null> { return null; }
export function nativeGoogleError(): string { return "Use the Google button on this page."; }
