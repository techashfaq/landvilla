# Android release preparation — 30 November 2026 target

## Build artifacts

Package com.landvilla.app, version name 1.0.0; dynamic config supplies baseline versionCode 1, EAS remote version source increments subsequent store builds. Confirm the initial remote version exceeds every previously uploaded code. Production, play-testing (internal track) and closed-testing profiles produce AABs. Build commands, only after approval: `eas build --platform android --profile play-testing`, then `--profile closed-testing`, then `--profile production`. Builds may incur charges; none were run. Upload to the intended Play track manually; no auto-submit configured.

Set EXPO_PUBLIC_BACKEND_URL in the matching EAS environment to the approved HTTPS hostname. Release config rejects missing/local/insecure URLs. Preserve EAS project ownership and signing keys; Play App Signing and upload key custody require owner setup. react-native-iap is already pinned and native-autolinked; Expo Go cannot test billing. Inspect the signed merged manifest/AAB for Billing permission/library, API target >=36, actual version, debug=false, no cleartext, and 16KB native compatibility. SDK versions were not changed. These checks require a native build and device testing; JavaScript checks alone do not prove them.

Existing icon/adaptive icon and splash assets remain; verify cropping and rights on-device. Custom landvilla scheme is present; verified HTTPS App Links require an approved domain, signing certificate fingerprint and assetlinks.json. No domain was invented.

## Permissions and review access

Existing configuration blocks camera, microphone, broad media/storage and overlay access. Photo selection uses the system picker and document uploads are user initiated. Internet is necessary for listings/auth/uploads; Billing for featured placement. Review the merged manifest for transitive SDK additions, notification permission and any unexpected permissions. Request only permissions actually used and explain them in-context.

Reviewer instructions template: open app; browse Buy/Rent in Ujjain; open a listing; sign in using the dedicated reviewer account; view Saved, Enquiries and My Properties; inspect broker application and purchase history. Supply approved review credentials or reliable OTP access privately in Play Console, never repository files. Use designated review data and a restricted account, never an administrator or bypass token. Account access and legal inventory remain owner-controlled blockers.

## Data Safety inventory for owner review

| Data | Purpose and destination | Release review |
|---|---|---|
| Name, email, phone, Google/user IDs | Authentication/profile in backend/Atlas; Google auth, configured OTP processors | Account management, functionality; describe required vs optional fields |
| Property address/locality, descriptions, photos | Owner publication; Atlas and R2; public approved listing details | User-provided content; distinguish from device location tracking |
| Broker identity/business documents | Private verification via backend/R2 and authorized staff | Sensitive documents; retention and restricted access |
| Enquiry messages/contact consent, saved listings | Messaging and account functionality in Atlas | Sharing with relevant property lister only as authorized |
| Purchase IDs/tokens/status | Google Play verification, backend accounting; Razorpay only configured web flows | Financial/purchase history; app must not collect card credentials |
| IP/rate-limit metadata and audit records | Fraud/security/deletion operations | Confirm retention and processor disclosures |

Inventory is not a submitted declaration. Review every bundled SDK and actual traffic before answering collected/shared/ephemeral/encryption/deletion questions. Service-provider exemptions depend on actual contracts; do not automatically mark all data "not shared". No advertising or analytics claim is made without SDK verification.

Privacy draft already exists at `/api/legal/privacy`; editable legal content requires business/legal approval. Terms at `/api/legal/terms`. Existing in-app Profile → Delete account requires recent authentication. Public request route `/api/legal/delete-account` must be published on the approved HTTPS API domain and entered in Play Console. Do not claim irreversible media erasure: physical R2 purge and backup retention remain unresolved (RELEASE_OPERATIONS.md). Approve the controller identity, support contact, processing purposes, processors, user rights, retention, refund and broker policies before publication.

## Store listing draft and assets

Name: LANDVILLA. Short description: "Find properties in Ujjain, manage listings and connect through enquiries."

Full-description draft: "LANDVILLA helps you explore properties for buying and renting in Ujjain. Browse property details and photos, save properties and send enquiries. Owners can create and manage listings, upload property photos and track enquiries. Brokers can apply for verification and manage their listings after approval. Listing publication is subject to moderation. Featured placement is available only for eligible properties through approved packages."

Publish claims only after corresponding device acceptance. Do not add ratings, inventory counts or guarantees. Capture genuine screenshots with synthetic non-sensitive review data; do not present demo inventory as genuine. Prepare phone screenshots for discovery, details, saved, owner listing and enquiries; portrait 1080x1920 is a useful capture size. Store icon 512x512 and feature graphic 1024x500; no misleading awards/prices. Owner approval and final localized assets pending.

## Play Console gates

- Verify organization/personal account identity, app ownership, signing and production-access eligibility.
- Complete content rating questionnaire accurately for user-generated property content/contact; choose target ages based on owner policy, not assumptions. Confirm report/block moderation and privacy access.
- Create approved one-time featured products, match play_product_id, prices and benefits; configure license testers, Publisher permissions and authenticated Pub/Sub. Validate pending/cancelled/refunded/replayed receipts on a test track. No real purchases during preparation.
- If a personal account created after 13 November 2023 is subject to the current rule, maintain at least 12 opted-in testers continuously for 14 days, then apply for production access. Starting by 16 November only leaves the minimum window to 30 November, with no review buffer; begin earlier and allow for rejection/review delays. Deadline is not guaranteed.
- Run internal device testing first, then required closed testing, pre-launch report, accessibility/offline/auth/upload/payment/deletion acceptance, staged production release only after explicit authorization.

Official references checked 11 November 2026: [testing eligibility](https://support.google.com/googleplay/android-developer/answer/14151465), [target API](https://support.google.com/googleplay/android-developer/answer/11926878), [store assets](https://support.google.com/googleplay/android-developer/answer/9866151), [account deletion](https://support.google.com/googleplay/android-developer/answer/13327111). Recheck Console requirements at submission.
