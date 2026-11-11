import React, { useEffect, useRef, useState } from "react";
import { AppState, Platform, Text, View } from "react-native";
import Constants from "expo-constants";
import * as Crypto from "expo-crypto";
import type { Purchase } from "react-native-iap";
import { useQueryClient } from "@tanstack/react-query";
import { api, getApiSessionVersion } from "@/src/api";
import { useAuth } from "@/src/auth";
import { Button } from "@/src/components/ui";
type SDK = typeof import("react-native-iap");
export function PlayBillingPanel({ productId, planId, propertyId }: { productId?: string; planId?: string; propertyId?: string }) {
  const { user } = useAuth(); const userId = user?.user_id; const qc = useQueryClient();
  const sdk = useRef<SDK | null>(null); const restoreRef = useRef<(() => Promise<void>) | null>(null); const attempt = useRef(Crypto.randomUUID());
  const [price, setPrice] = useState(""); const [busy, setBusy] = useState(false); const [message, setMessage] = useState(""); const [ready, setReady] = useState(false);
  useEffect(() => {
    if (Platform.OS !== "android" || !userId) return;
    if (Constants.appOwnership === "expo") return;
    let disposed = false; let cleanup = () => {}; const version = getApiSessionVersion(); const inFlight = new Set<string>();
    const current = () => !disposed && version === getApiSessionVersion();
    async function receive(purchase: Purchase) {
      const token = purchase.purchaseToken;
      if (!current() || !token || inFlight.has(token)) return;
      inFlight.add(token);
      try {
        const result = await api<{ status: string }>("/payments/play/verify", { method: "POST", body: { purchase_token: token } });
        if (!current()) return;
        if (result.status === "paid") {
          await sdk.current!.finishTransaction({ purchase, isConsumable: true });
          if (current()) { setMessage("Google Play payment verified and featured placement activated."); attempt.current = Crypto.randomUUID(); await qc.invalidateQueries(); }
        } else setMessage("Google Play payment is pending. Check history before trying again.");
      } catch (error) { if (current()) setMessage(error instanceof Error ? error.message : "Verification unavailable. Restore purchases to retry."); }
      finally { inFlight.delete(token); if (current()) setBusy(false); }
    }
    void (async () => {
      try {
        const billing = await import("react-native-iap"); if (!current()) return;
        sdk.current = billing; await billing.initConnection();
        if (!current()) { await billing.endConnection(); return; }
        const updates = billing.purchaseUpdatedListener(p => { void receive(p); });
        const errors = billing.purchaseErrorListener(error => { if (current()) { setBusy(false); setMessage(error.code === billing.ErrorCode.UserCancelled ? "Checkout cancelled. No entitlement was activated by the app." : "Google Play could not complete checkout. Check history or restore purchases."); } });
        const restore = async () => { try { for (const purchase of await billing.getAvailablePurchases()) await receive(purchase); } catch { if (current()) setMessage("Could not restore purchases. Please retry."); } };
        restoreRef.current = restore;
        const foreground = AppState.addEventListener("change", state => { if (state === "active") void restore(); });
        cleanup = () => { updates.remove(); errors.remove(); foreground.remove(); void billing.endConnection(); };
        if (productId) { const products = await billing.fetchProducts({ skus: [productId], type: "in-app" }); if (current()) setPrice(products?.find(p => p.id === productId)?.displayPrice ?? ""); }
        if (current()) setReady(true); await restore();
      } catch { if (current()) setMessage("Google Play Billing is unavailable. Install the updated Play test-track build with a licensed tester account."); }
    })();
    return () => { disposed = true; cleanup(); sdk.current = null; restoreRef.current = null; };
  }, [productId, userId, qc]);
  async function purchase() {
    if (!sdk.current || busy || !planId || !propertyId || !productId) return;
    setBusy(true); setMessage(""); const version = getApiSessionVersion();
    try {
      const intent = await api<{ product_id: string; account_id: string; profile_id: string }>("/payments/play/intent", { method: "POST", body: { plan_id: planId, property_id: propertyId, idempotency_key: attempt.current } });
      if (version !== getApiSessionVersion() || intent.product_id !== productId) throw new Error("Account or package changed. Refresh before purchasing.");
      await sdk.current.requestPurchase({ type: "in-app", request: { google: { skus: [productId], obfuscatedAccountId: intent.account_id, obfuscatedProfileId: intent.profile_id } } });
    } catch (error) { setBusy(false); setMessage(error instanceof Error ? error.message : "Checkout could not start."); }
  }
  if (Platform.OS !== "android") return null;
  if (Constants.appOwnership === "expo") return <Text>Play Billing requires a LANDVILLA build installed through a Play test track.</Text>;
  return <View style={{ gap: 12 }}>{productId && <Button label={price ? `Buy with Google Play · ${price}` : "Package price unavailable from Google Play"} disabled={!ready || !price || busy} loading={busy} onPress={purchase} />}
    <Button label="Restore / check Google Play purchases" variant="outline" disabled={!ready || busy} onPress={() => { void restoreRef.current?.(); }} />
    {!!message && <Text accessibilityLiveRegion="polite">{message}</Text>}
  </View>;
}
