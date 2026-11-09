import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { Redirect, useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { Button, ScreenHeader } from "@/src/components/ui";
import { IndependentGoogle } from "@/src/components/IndependentGoogle";
import { fonts, makeStyles } from "@/src/theme";

type Profile = { first_name: string; last_name: string; email: string; mobile: string; email_verified: boolean; mobile_verified: boolean; preferred_location: string; account_role: string; account_status: string; profile_complete: boolean };
export default function Account() {
  const { user, loading } = useAuth();
  if (loading) return <ActivityIndicator />;
  if (!user) return <Redirect href="/login" />;
  return <AccountForm key={user.user_id} />;
}
function AccountForm() {
  const active = useRef(true);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  const styles = useStyles(); const router = useRouter(); const insets = useSafeAreaInsets();
  const { user, loading, refreshUser } = useAuth();
  const profile = useQuery({ queryKey: ["profile", user?.user_id], queryFn: () => api<Profile>("/me/profile"), enabled: !!user });
  const [editedFirst, setFirst] = useState<string | null>(null); const [editedLast, setLast] = useState<string | null>(null); const [editedLocation, setLocation] = useState<string | null>(null);
  const first = editedFirst ?? profile.data?.first_name ?? "";
  const last = editedLast ?? profile.data?.last_name ?? "";
  const location = editedLocation ?? profile.data?.preferred_location ?? "";
  const [contact, setContact] = useState(""); const [challenge, setChallenge] = useState(""); const [code, setCode] = useState("");
  const [wait, setWait] = useState(0); const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [message, setMessage] = useState("");
  useEffect(() => { const timer = setInterval(() => setWait(v => Math.max(0, v - 1)), 1000); return () => clearInterval(timer); }, []);
  const run = async (fn: () => Promise<void>) => { setBusy(true); setError(""); setMessage(""); try { await fn(); } catch (e: any) { setError(e.message); } finally { setBusy(false); } };
  if (loading) return <ActivityIndicator />;
  if (!user) return <Redirect href="/login" />;
  return <View style={styles.screen}><ScreenHeader title="Edit profile" topInset={insets.top} onBack={() => router.back()} />
    <KeyboardAwareScrollView contentContainerStyle={styles.body}>
      {profile.isPending ? <ActivityIndicator /> : profile.isError ? <Button label="Retry loading profile" onPress={() => profile.refetch()} /> : <>
        <Text style={styles.text}>{profile.data?.email} — {profile.data?.email_verified ? "Verified" : "Not verified"}</Text>
        <Text style={styles.text}>{profile.data?.mobile || "No mobile"} — {profile.data?.mobile_verified ? "Verified" : "Not verified"}</Text>
        <Text style={styles.text}>Account: {profile.data?.account_role || "buyer"} · {profile.data?.account_status || "active"}</Text>
        <Text style={styles.text}>{profile.data?.profile_complete ? "Profile complete" : "Complete your name and verify both contacts"}</Text>
        <TextInput style={styles.input} accessibilityLabel="First name" placeholder="First name" value={first} onChangeText={setFirst} maxLength={60} />
        <TextInput style={styles.input} accessibilityLabel="Last name" placeholder="Last name" value={last} onChangeText={setLast} maxLength={60} />
        <TextInput style={styles.input} accessibilityLabel="Preferred location" placeholder="Preferred location" value={location} onChangeText={setLocation} maxLength={120} />
        <Button label="Save profile" disabled={busy || !first.trim() || !last.trim()} onPress={() => run(async () => { await api("/me/profile", { method: "PATCH", body: { first_name: first.trim(), last_name: last.trim(), preferred_location: location.trim() } }); if (!active.current) return; await profile.refetch(); await refreshUser(); if (active.current) setMessage("Profile saved"); })} />
        <Text style={styles.text}>Verify or change email / mobile. Your existing contact stays unchanged until verification succeeds.</Text>
        <IndependentGoogle link />
        <TextInput style={styles.input} accessibilityLabel="New email or international mobile" placeholder="Email or +91 mobile" value={contact} editable={!challenge} onChangeText={setContact} autoCapitalize="none" />
        <Button label={wait ? `Resend in ${wait}s` : "Send contact verification"} disabled={busy || wait > 0 || !contact.trim()} onPress={() => run(async () => { const result = await api("/auth/otp/request", { method: "POST", body: { identifier: contact.trim(), purpose: "contact" } }); if (!active.current) return; setChallenge(result.challenge_id); setWait(result.resend_after); setCode(""); })} />
        {!!challenge && <>
          <TextInput style={styles.input} accessibilityLabel="Verification code" placeholder="6-digit code" value={code} onChangeText={setCode} keyboardType="number-pad" maxLength={6} />
          <Button label="Verify contact" disabled={busy || !/^\d{6}$/.test(code)} onPress={() => run(async () => { await api("/auth/otp/verify", { method: "POST", body: { challenge_id: challenge, code } }); if (!active.current) return; setChallenge(""); await profile.refetch(); await refreshUser(); setMessage("Contact verified"); })} />
          <Button label="Change contact" variant="outline" disabled={busy} onPress={() => setChallenge("")} />
        </>}
      </>}
      {!!message && <Text style={styles.text}>{message}</Text>}
      {!!error && <Text style={styles.error} accessibilityRole="alert">{error}</Text>}
    </KeyboardAwareScrollView></View>;
}
const useStyles = makeStyles(c => ({ screen: { flex: 1, backgroundColor: c.surface }, body: { padding: 24, gap: 16 }, text: { color: c.onSurface, fontFamily: fonts.text }, input: { borderWidth: 1, borderColor: c.border, borderRadius: 12, padding: 14, color: c.onSurface }, error: { color: c.error } }));
