import { Platform } from "react-native";
import Constants from "expo-constants";

export class NativeGoogleError extends Error {}

/** Android Credential Manager only. Load on demand so Expo Go can still use email login. */
export async function requestNativeGoogleToken(): Promise<string | null> {
  if (Platform.OS !== "android") throw new NativeGoogleError("Independent Google sign-in is currently configured for Android only. Use email sign-in.");
  if (Constants.appOwnership === "expo") throw new NativeGoogleError("Google sign-in requires the LANDVILLA Android development build, not Expo Go.");
  const webClientId = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID?.trim();
  if (!webClientId || !/^[\w-]+\.apps\.googleusercontent\.com$/.test(webClientId)) {
    throw new NativeGoogleError("Google sign-in is not configured in this build. Use email sign-in.");
  }
  let sdk: typeof import("react-native-nitro-google-signin");
  try { sdk = await import("react-native-nitro-google-signin"); }
  catch { throw new NativeGoogleError("Rebuild and install the LANDVILLA development client to enable Google sign-in."); }
  sdk.GoogleOneTapSignIn.configure({ webClientId, offlineAccess: false, autoSelectOnSignIn: false });
  await sdk.GoogleOneTapSignIn.checkPlayServices();
  // Explicit account chooser on every button press; never silently reauthenticate after logout.
  const response = await sdk.GoogleOneTapSignIn.presentExplicitSignIn();
  if (sdk.isCancelledResponse(response)) return null;
  if (!sdk.isSuccessResponse(response) || !response.data.idToken?.trim()) {
    throw new NativeGoogleError("Google did not return an identity token. Please try again.");
  }
  return response.data.idToken;
}

export function nativeGoogleError(error: unknown): string {
  if (error instanceof NativeGoogleError) return error.message;
  const e = error as { code?: string; status?: number } | null;
  if (e?.code === "SIGN_IN_CANCELLED") return "Google sign-in was cancelled.";
  if (e?.code === "DEVELOPER_ERROR") return "Google Android OAuth configuration is incomplete. Check the package, signing SHA-1 and Web client ID.";
  if (e?.code === "PLAY_SERVICES_NOT_AVAILABLE") return "Google Play Services is unavailable or needs an update.";
  if (e?.status === 409) return "Sign in with your existing method and link Google from your account on the web.";
  if (e?.status === 401 || e?.status === 403) return "Google sign-in was rejected. Check your account or use email sign-in.";
  if (e?.status === 429) return "Too many sign-in attempts. Please wait and retry.";
  if (e?.status === 503) return "Sign-in is temporarily unavailable. Please try again later.";
  return "Unable to sign in with Google. Check your connection and development-build configuration, then retry.";
}
