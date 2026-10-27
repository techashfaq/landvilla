import React, { useEffect } from "react";
import { Modal, Platform, View } from "react-native";
import { WebView } from "react-native-webview";
import { useSafeAreaInsets } from "react-native-safe-area-context";

export type RzpOrder = { razorpay_order_id: string; key_id: string; amount: number; currency: string; name: string; description: string; prefill?: { email?: string; name?: string } };
export type RzpSuccess = { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string };

type Props = { order: RzpOrder | null; onSuccess: (r: RzpSuccess) => void; onDismiss: () => void; onFailed: (desc: string) => void };

const BRAND = "#B84A1E"; // Razorpay modal accent (rendered by Razorpay, fixed in both themes)

function options(o: RzpOrder) {
  return { key: o.key_id, amount: o.amount, currency: o.currency, name: o.name, description: o.description, order_id: o.razorpay_order_id, prefill: o.prefill ?? {}, theme: { color: BRAND } };
}

function html(o: RzpOrder) {
  return `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"/></head><body style="background:#fff">
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
<script>
const post = (d) => window.ReactNativeWebView.postMessage(JSON.stringify(d));
const opts = ${JSON.stringify(options(o))};
opts.handler = (r) => post({ type: "success", ...r });
opts.modal = { ondismiss: () => post({ type: "dismiss" }) };
const rz = new Razorpay(opts);
rz.on("payment.failed", (r) => post({ type: "failed", description: (r.error && r.error.description) || "Payment failed" }));
rz.open();
</script></body></html>`;
}

/** Razorpay Checkout: WebView on native (works in Expo Go), checkout.js on web. */
export function RazorpayCheckout({ order, onSuccess, onDismiss, onFailed }: Props) {
  const insets = useSafeAreaInsets();

  useEffect(() => {
    if (Platform.OS !== "web" || !order) return;
    let rz: any;
    const open = () => {
      const R = (window as any).Razorpay;
      rz = new R({ ...options(order), handler: (r: RzpSuccess) => onSuccess(r), modal: { ondismiss: onDismiss } });
      rz.on("payment.failed", (r: any) => onFailed(r?.error?.description || "Payment failed"));
      rz.open();
    };
    if ((window as any).Razorpay) open();
    else {
      const s = document.createElement("script");
      s.src = "https://checkout.razorpay.com/v1/checkout.js";
      s.onload = open;
      s.onerror = () => onFailed("Could not load payment page. Check your internet.");
      document.body.appendChild(s);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [order]);

  if (Platform.OS === "web" || !order) return null;
  return (
    <Modal visible animationType="slide" onRequestClose={onDismiss}>
      <View style={{ flex: 1, paddingTop: insets.top, paddingBottom: insets.bottom, backgroundColor: "#FFFFFF" }}>
        <WebView
          testID="razorpay-webview"
          originWhitelist={["*"]}
          source={{ html: html(order), baseUrl: "https://checkout.razorpay.com" }}
          javaScriptEnabled
          onMessage={(e) => {
            const d = JSON.parse(e.nativeEvent.data);
            if (d.type === "success") onSuccess(d);
            else if (d.type === "failed") onFailed(d.description);
            else onDismiss();
          }}
        />
      </View>
    </Modal>
  );
}
