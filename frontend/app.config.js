// Keep native release builds from silently targeting local or insecure servers.
module.exports = ({ config }) => {
  const release = ["production", "play-testing", "closed-testing"].includes(process.env.EAS_BUILD_PROFILE);
  if (release) {
    let url;
    try { url = new URL(process.env.EXPO_PUBLIC_BACKEND_URL || ""); } catch { /* rejected below */ }
    if (!url || url.protocol !== "https:" || url.username || url.password || url.search || url.hash ||
        url.hostname === "localhost" || url.hostname.endsWith(".local") || /^[\d.]+$/.test(url.hostname) || url.hostname.includes(":")) {
      throw new Error("Release requires EXPO_PUBLIC_BACKEND_URL with a public HTTPS hostname");
    }
  }
  return { ...config, android: { ...config.android, package: "com.landvilla.app", versionCode: config.android?.versionCode || 1 } };
};
