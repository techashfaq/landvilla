import React, { useEffect, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { normalizeIdentifier, registrationValid, validIdentifier } from "@/src/otp-form";
import { Button, Checkbox, ScreenHeader } from "@/src/components/ui";
import { fonts, makeStyles } from "@/src/theme";

export default function Verification() {
  const styles = useStyles();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { acceptSession } = useAuth();
  const [register, setRegister] = useState(false);
  const [identifier, setIdentifier] = useState("");
  const [first, setFirst] = useState("");
  const [last, setLast] = useState("");
  const [mobile, setMobile] = useState("+91");
  const [role, setRole] = useState("buyer");
  const [terms, setTerms] = useState(false);
  const [privacy, setPrivacy] = useState(false);
  const [challenge, setChallenge] = useState("");
  const [code, setCode] = useState("");
  const [wait, setWait] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { const timer = setInterval(() => setWait(v => Math.max(0, v - 1)), 1000); return () => clearInterval(timer); }, []);
  const send = async () => {
    setError("");
    if (register && !registrationValid(first, last, identifier, mobile, role, terms, privacy)) {
      setError("Complete your name, email, international mobile number and both consent choices."); return;
    }
    if (!validIdentifier(identifier)) { setError("Enter your verified email or international mobile number."); return; }
    setBusy(true);
    try {
      const result = await api<{ challenge_id: string; resend_after: number }>("/auth/otp/request", { method: "POST", body: {
        identifier: normalizeIdentifier(identifier), purpose: register ? "register" : "login",
        ...(register ? { registration: { first_name: first.trim(), last_name: last.trim(), email: normalizeIdentifier(identifier), mobile: normalizeIdentifier(mobile),
          account_role: role, accept_terms: terms, accept_privacy: privacy } } : {}) } });
      setChallenge(result.challenge_id); setWait(result.resend_after); setCode("");
    } catch (e: any) { setError(e.message); } finally { setBusy(false); }
  };
  const verify = async () => {
    setBusy(true); setError("");
    try {
      const result = await api("/auth/otp/verify", { method: "POST", body: { challenge_id: challenge, code } });
      await acceptSession(result); router.replace("/");
    } catch (e: any) { setError(e.message); } finally { setBusy(false); }
  };
  return <View style={styles.screen}><ScreenHeader title={register ? "Create account" : "Sign in with a code"} topInset={insets.top} onBack={() => router.back()} />
    <KeyboardAwareScrollView contentContainerStyle={styles.body}>
      <Text style={styles.heading}>LANDVILLA</Text>
      {!challenge ? <>
        <TextInput style={styles.input} accessibilityLabel={register ? "Email" : "Email or international mobile"} placeholder={register ? "Email" : "Email or +91 mobile number"} value={identifier} onChangeText={setIdentifier} autoCapitalize="none" keyboardType="email-address" />
        {register && <>
          <TextInput style={styles.input} accessibilityLabel="First name" placeholder="First name" value={first} onChangeText={setFirst} maxLength={60} />
          <TextInput style={styles.input} accessibilityLabel="Last name" placeholder="Last name" value={last} onChangeText={setLast} maxLength={60} />
          <TextInput style={styles.input} accessibilityLabel="Mobile with country code" placeholder="Mobile with country code" value={mobile} onChangeText={setMobile} keyboardType="phone-pad" />
          <Text style={styles.text}>I am a:</Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12 }}>{["buyer", "owner", "broker", "builder"].map(r => <Pressable key={r} accessibilityRole="radio" accessibilityState={{ checked: role === r }} onPress={() => setRole(r)}><Text style={styles.text}>{role === r ? "● " : "○ "}{r}</Text></Pressable>)}</View>
          <Checkbox checked={terms} onToggle={() => setTerms(!terms)} label="I accept the Terms" />
          <Checkbox checked={privacy} onToggle={() => setPrivacy(!privacy)} label="I accept the Privacy Policy" />
          <Text style={styles.text} onPress={() => router.push("/legal/terms")}>Read Terms</Text>
          <Text style={styles.text} onPress={() => router.push("/legal/privacy")}>Read Privacy Policy</Text>
          <Text style={styles.text}>Email verification activates your account. Verify your mobile in Edit profile before using it to sign in. Broker posting still requires approval.</Text>
        </>}
        <Button label="Send verification code" onPress={send} loading={busy} />
        <Button label={register ? "Already registered? Sign in" : "Create an account"} variant="outline" onPress={() => { setRegister(!register); setError(""); }} disabled={busy} />
      </> : <>
        <Text style={styles.text}>If eligible, a code was sent to {identifier}. It expires in five minutes.</Text>
        <TextInput style={styles.input} accessibilityLabel="Six digit verification code" placeholder="6-digit code" value={code} onChangeText={setCode} keyboardType="number-pad" maxLength={6} autoComplete="one-time-code" />
        <Button label="Verify and continue" onPress={verify} loading={busy} disabled={!/^\d{6}$/.test(code)} />
        <Button label={wait ? `Resend in ${wait}s` : "Resend code"} onPress={send} disabled={wait > 0 || busy} variant="outline" />
        <Button label="Change details" onPress={() => setChallenge("")} disabled={busy} variant="outline" />
      </>}
      {!!error && <Text style={styles.error} accessibilityRole="alert">{error}</Text>}
    </KeyboardAwareScrollView></View>;
}
const useStyles = makeStyles(c => ({ screen: { flex: 1, backgroundColor: c.surface }, body: { padding: 24, gap: 16 }, heading: { fontFamily: fonts.display, fontSize: 26, color: c.brandPrimary }, text: { color: c.onSurface, fontFamily: fonts.text }, input: { borderWidth: 1, borderColor: c.border, borderRadius: 12, padding: 14, color: c.onSurface, fontFamily: fonts.text }, error: { color: c.error } }));
