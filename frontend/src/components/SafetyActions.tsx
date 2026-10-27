import { useState } from "react";
import { View } from "react-native";

import { api } from "@/src/api";
import { ReportSheet } from "@/src/components/ReportSheet";
import { useToast } from "@/src/components/Toast";
import { Button } from "@/src/components/ui";
import { useLang } from "@/src/i18n";

/** Report + Block actions for an enquiry conversation (used by buyer and lister). */
export function SafetyActions({ enquiryId, initialBlocked = false, onChanged }: { enquiryId: string; initialBlocked?: boolean; onChanged?: () => void }) {
  const { tx } = useLang();
  const toast = useToast();
  const [report, setReport] = useState(false);
  const [blocked, setBlocked] = useState(initialBlocked);
  const [confirmBlock, setConfirmBlock] = useState(false);
  const toggleBlock = async () => {
    if (!blocked && !confirmBlock) {
      setConfirmBlock(true);
      return;
    }
    setConfirmBlock(false);
    try {
      await api(`/enquiries/${enquiryId}/block`, { method: blocked ? "DELETE" : "POST" });
      setBlocked(!blocked);
      onChanged?.();
      toast.show(blocked ? tx("User unblocked", "उपयोगकर्ता अनब्लॉक") : tx("User blocked. They can't message or enquire with you.", "उपयोगकर्ता ब्लॉक। वे आपको संदेश या पूछताछ नहीं भेज सकते।"), "success");
    } catch (e: any) {
      toast.show(e.message, "error");
    }
  };
  return (
    <View style={{ flexDirection: "row", gap: 8 }}>
      <Button label={tx("Report", "रिपोर्ट")} variant="outline" icon="flag-outline" onPress={() => setReport(true)} testID="safety-report-btn" style={{ flex: 1 }} />
      <Button label={blocked ? tx("Unblock", "अनब्लॉक") : confirmBlock ? tx("Tap to confirm", "पुष्टि हेतु टैप करें") : tx("Block", "ब्लॉक")} variant="outline" icon="ban-outline" onPress={toggleBlock} testID="safety-block-btn" style={{ flex: 1 }} />
      <ReportSheet visible={report} onClose={() => setReport(false)} path={`/enquiries/${enquiryId}/report-user`} title={tx("Report this user", "इस उपयोगकर्ता की रिपोर्ट करें")} />
    </View>
  );
}
