const { withAndroidManifest } = require("expo/config-plugins");
module.exports = function withAndroidGoogle(config) {
  // Android Credential Manager autolinks; explicit webClientId needs no Firebase Gradle plugin.
  // Upstream plugin without Firebase modifies iOS only and requires an iOS OAuth ID.
  return withAndroidManifest(config, (mod) => {
    const app = mod.modResults.manifest.application[0];
    // Private LAN HTTP is permitted only for an explicitly selected development build.
    app.$["android:usesCleartextTraffic"] = process.env.EAS_BUILD_PROFILE === "development" ? "true" : "false";
    return mod;
  });
};
