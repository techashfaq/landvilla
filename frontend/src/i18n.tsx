import React, { createContext, useCallback, useContext, useEffect, useState } from "react";

import { storage } from "@/src/utils/storage";

export type Lang = "en" | "hi";

const en = {
  appTagline: "Homes, plots & shops across Ujjain",
  searchPlaceholder: "Search locality, e.g. Freeganj",
  buy: "Buy",
  rent: "Rent",
  all: "All",
  filters: "Filters",
  zones: "Areas of Ujjain",
  properties: "properties",
  property: "property",
  featured: "Featured",
  verified: "Verified",
  unverified: "Unverified",
  demo: "DEMO",
  demoBanner: "Fictional demo listing for testing. Not a real property, owner, price or availability.",
  noResults: "No properties found for these filters",
  clearFilters: "Clear Filters",
  retry: "Retry",
  loadError: "Couldn't connect. Check your internet and try again.",
  applyFilters: "Apply Filters",
  reset: "Reset",
  category: "Category",
  propertyType: "Property Type",
  locality: "Locality",
  budget: "Budget",
  bhk: "BHK",
  sortBy: "Sort by",
  newest: "Newest",
  priceLow: "Price: Low to High",
  priceHigh: "Price: High to Low",
  any: "Any",
  beds: "Beds",
  baths: "Baths",
  sqft: "sq.ft",
  amenities: "Amenities",
  location: "Location",
  about: "About this property",
  furnishing: "Furnishing",
  enquireNow: "Enquire Now",
  sendEnquiry: "Send Enquiry",
  yourName: "Your name",
  mobile: "Mobile number",
  message: "Message (optional)",
  iWantTo: "I want to",
  intentInfo: "Get details",
  intentVisit: "Site visit",
  intentCallback: "Callback",
  enquirySent: "Enquiry sent! We'll get back to you soon.",
  nameError: "Please enter your name",
  nameShort: "Name must be at least 2 characters",
  phoneError: "Enter a valid 10-digit mobile number",
  saved: "Saved",
  savedEmpty: "No saved properties yet",
  explore: "Explore Properties",
  enquiries: "Enquiries",
  enquiriesEmpty: "You haven't sent any enquiries yet",
  browseHomes: "Browse Homes",
  profile: "Profile",
  home: "Home",
  language: "Language",
  loginTitle: "Sign in to LANDVILLA",
  loginSub: "Save homes, send enquiries and track responses.",
  continueGoogle: "Continue with Google",
  loginRequired: "Please sign in to continue",
  logout: "Log out",
  guest: "Guest",
  signIn: "Sign in",
  manageLocalities: "Manage Localities",
  adminTools: "Admin tools",
  aboutApp: "About LANDVILLA",
  aboutText: "Ujjain-first property marketplace. Listings marked DEMO are fictional and only for testing.",
  statusNew: "New",
  statusContacted: "Contacted",
  statusClosed: "Closed",
  sentOn: "Sent on",
  notAvailable: "This property is no longer available",
  backHome: "Back to Home",
  perMonth: "/month",
  furnished: "Furnished",
  "semi-furnished": "Semi-furnished",
  unfurnished: "Unfurnished",
  close: "Close",
  results: "Results",
  notVerifiedNote: "Locality details are pending admin verification.",
  cancel: "Cancel",
};

const hi: typeof en = {
  appTagline: "उज्जैन भर में घर, प्लॉट और दुकानें",
  searchPlaceholder: "इलाका खोजें, जैसे फ्रीगंज",
  buy: "खरीदें",
  rent: "किराया",
  all: "सभी",
  filters: "फ़िल्टर",
  zones: "उज्जैन के क्षेत्र",
  properties: "प्रॉपर्टी",
  property: "प्रॉपर्टी",
  featured: "विशेष",
  verified: "सत्यापित",
  unverified: "असत्यापित",
  demo: "डेमो",
  demoBanner: "परीक्षण के लिए काल्पनिक डेमो लिस्टिंग। यह वास्तविक संपत्ति, मालिक, कीमत या उपलब्धता नहीं है।",
  noResults: "इन फ़िल्टर के लिए कोई प्रॉपर्टी नहीं मिली",
  clearFilters: "फ़िल्टर हटाएं",
  retry: "फिर कोशिश करें",
  loadError: "कनेक्ट नहीं हो सका। इंटरनेट जांचें और फिर कोशिश करें।",
  applyFilters: "फ़िल्टर लागू करें",
  reset: "रीसेट",
  category: "श्रेणी",
  propertyType: "प्रॉपर्टी प्रकार",
  locality: "इलाका",
  budget: "बजट",
  bhk: "BHK",
  sortBy: "क्रम",
  newest: "नवीनतम",
  priceLow: "कीमत: कम से ज़्यादा",
  priceHigh: "कीमत: ज़्यादा से कम",
  any: "कोई भी",
  beds: "बेड",
  baths: "बाथ",
  sqft: "वर्ग फुट",
  amenities: "सुविधाएं",
  location: "स्थान",
  about: "इस प्रॉपर्टी के बारे में",
  furnishing: "फर्निशिंग",
  enquireNow: "पूछताछ करें",
  sendEnquiry: "पूछताछ भेजें",
  yourName: "आपका नाम",
  mobile: "मोबाइल नंबर",
  message: "संदेश (वैकल्पिक)",
  iWantTo: "मैं चाहता/चाहती हूँ",
  intentInfo: "जानकारी",
  intentVisit: "साइट विज़िट",
  intentCallback: "कॉलबैक",
  enquirySent: "पूछताछ भेज दी गई! हम जल्द संपर्क करेंगे।",
  nameError: "कृपया अपना नाम लिखें",
  nameShort: "नाम कम से कम 2 अक्षर का होना चाहिए",
  phoneError: "सही 10 अंकों का मोबाइल नंबर लिखें",
  saved: "सेव्ड",
  savedEmpty: "अभी कोई प्रॉपर्टी सेव नहीं की",
  explore: "प्रॉपर्टी देखें",
  enquiries: "पूछताछ",
  enquiriesEmpty: "आपने अभी तक कोई पूछताछ नहीं भेजी",
  browseHomes: "घर देखें",
  profile: "प्रोफ़ाइल",
  home: "होम",
  language: "भाषा",
  loginTitle: "LANDVILLA में साइन इन करें",
  loginSub: "घर सेव करें, पूछताछ भेजें और जवाब ट्रैक करें।",
  continueGoogle: "Google से जारी रखें",
  loginRequired: "जारी रखने के लिए साइन इन करें",
  logout: "लॉग आउट",
  guest: "अतिथि",
  signIn: "साइन इन",
  manageLocalities: "इलाके प्रबंधित करें",
  adminTools: "एडमिन टूल्स",
  aboutApp: "LANDVILLA के बारे में",
  aboutText: "उज्जैन से शुरू प्रॉपर्टी मार्केटप्लेस। डेमो चिह्नित लिस्टिंग काल्पनिक हैं और केवल परीक्षण के लिए हैं।",
  statusNew: "नई",
  statusContacted: "संपर्क किया",
  statusClosed: "बंद",
  sentOn: "भेजी गई",
  notAvailable: "यह प्रॉपर्टी अब उपलब्ध नहीं है",
  backHome: "होम पर जाएं",
  perMonth: "/माह",
  furnished: "फर्निश्ड",
  "semi-furnished": "सेमी-फर्निश्ड",
  unfurnished: "अनफर्निश्ड",
  close: "बंद करें",
  results: "परिणाम",
  notVerifiedNote: "इलाके की जानकारी एडमिन सत्यापन के लिए लंबित है।",
  cancel: "रद्द करें",
};

export type TKey = keyof typeof en;

type Ctx = {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (k: TKey) => string;
  pick: (obj: any, field: string) => string;
};

const LangContext = createContext<Ctx>({} as Ctx);
const KEY = "landvilla_lang";

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    storage.getItem<string>(KEY, "en").then((v) => setLangState(v === "hi" ? "hi" : "en"));
  }, []);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    storage.setItem(KEY, l);
  }, []);

  const t = useCallback((k: TKey) => (lang === "hi" ? hi : en)[k] ?? String(k), [lang]);
  const pick = useCallback(
    (obj: any, field: string) => (obj ? obj[`${field}_${lang}`] || obj[`${field}_en`] || "" : ""),
    [lang],
  );

  return <LangContext.Provider value={{ lang, setLang, t, pick }}>{children}</LangContext.Provider>;
}

export const useLang = () => useContext(LangContext);
