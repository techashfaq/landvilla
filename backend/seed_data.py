"""Static reference data for LANDVILLA seed.

IMPORTANT DATA POLICY
- Localities are seeded as `verification_status = "unverified"` with source
  "founder_provided_list". Only an administrator may mark them verified.
- No coordinates, boundaries, postal codes, population or prices are stored
  for localities. latitude/longitude stay null until filled from a verified
  geocoding source by an admin.
- Zone assignments are TENTATIVE (zone_assignment = "tentative") until an
  admin verifies them. Candidates without a confident zone are left zone=None
  and reported as unresolved.
"""

CITY = {
    "slug": "ujjain",
    "name_en": "Ujjain",
    "name_hi": "उज्जैन",
    "state_en": "Madhya Pradesh",
    "state_hi": "मध्य प्रदेश",
    "country": "India",
    "is_active": True,
}

ZONES = [
    {"slug": "central-ujjain", "name_en": "Central Ujjain", "name_hi": "मध्य उज्जैन", "order": 1},
    {"slug": "nanakheda-university-road", "name_en": "Nanakheda & University Road", "name_hi": "नानाखेड़ा और यूनिवर्सिटी रोड", "order": 2},
    {"slug": "mahakal-old-city", "name_en": "Mahakal & Old City", "name_hi": "महाकाल और पुराना शहर", "order": 3},
    {"slug": "indore-road-nagziri", "name_en": "Indore Road & Nagziri", "name_hi": "इंदौर रोड और नागझिरी", "order": 4},
    {"slug": "dewas-road-developing", "name_en": "Dewas Road & Developing Belts", "name_hi": "देवास रोड और विकासशील क्षेत्र", "order": 5},
]

# Raw candidate names exactly as provided by the founder.
LOCALITY_CANDIDATES = [
    "Freeganj", "Madhav Nagar", "Dewas Gate", "Tower Chowk", "Gopal Mandir", "Malipura",
    "Nanakheda", "Rishi Nagar", "Rishi Nagar Extension", "Jawahar Nagar", "University Road",
    "Vikram Nagar", "Sethi Nagar", "Mahakal area", "Jaisinghpura", "Begum Bagh", "Ramghat area",
    "Patni Bazaar", "Indore Road", "Nagziri", "Sanwer Road", "Motibagh Colony", "Pawapuri Colony",
    "Shipra Vihar", "Dewas Road", "Agar Road", "Maksi Road", "Mahananda Nagar", "Kanipura Road",
    "Chandukhedi", "Pandyakhedi", "Vasant Vihar",
    # Common spelling variants seen in listings - must resolve to existing records, not duplicate.
    "Free Ganj", "Nana Kheda", "Mahakal Area", "Rishinagar",
]

# Canonical locality definitions. zone=None => unresolved zone (admin must assign).
LOCALITIES = [
    # Central Ujjain
    {"slug": "freeganj", "name_en": "Freeganj", "name_hi": "फ्रीगंज", "zone": "central-ujjain", "aliases": ["Free Ganj", "Freegunj"]},
    {"slug": "madhav-nagar", "name_en": "Madhav Nagar", "name_hi": "माधव नगर", "zone": "central-ujjain", "aliases": ["Madhavnagar"]},
    {"slug": "dewas-gate", "name_en": "Dewas Gate", "name_hi": "देवास गेट", "zone": "central-ujjain", "aliases": []},
    {"slug": "tower-chowk", "name_en": "Tower Chowk", "name_hi": "टॉवर चौक", "zone": "central-ujjain", "aliases": ["Tower Chauk"]},
    {"slug": "malipura", "name_en": "Malipura", "name_hi": "मालीपुरा", "zone": "central-ujjain", "aliases": []},
    {"slug": "sethi-nagar", "name_en": "Sethi Nagar", "name_hi": "सेठी नगर", "zone": "central-ujjain", "aliases": ["Sethinagar"]},
    # Nanakheda & University Road
    {"slug": "nanakheda", "name_en": "Nanakheda", "name_hi": "नानाखेड़ा", "zone": "nanakheda-university-road", "aliases": ["Nana Kheda", "Nanakhera"]},
    {"slug": "rishi-nagar", "name_en": "Rishi Nagar", "name_hi": "ऋषि नगर", "zone": "nanakheda-university-road", "aliases": ["Rishinagar"]},
    {"slug": "rishi-nagar-extension", "name_en": "Rishi Nagar Extension", "name_hi": "ऋषि नगर एक्सटेंशन", "zone": "nanakheda-university-road", "aliases": ["Rishi Nagar Ext"], "parent": "rishi-nagar"},
    {"slug": "university-road", "name_en": "University Road", "name_hi": "यूनिवर्सिटी रोड", "zone": "nanakheda-university-road", "aliases": ["Univ Road"]},
    {"slug": "mahananda-nagar", "name_en": "Mahananda Nagar", "name_hi": "महानंदा नगर", "zone": "nanakheda-university-road", "aliases": []},
    {"slug": "jawahar-nagar", "name_en": "Jawahar Nagar", "name_hi": "जवाहर नगर", "zone": None, "aliases": []},
    {"slug": "vikram-nagar", "name_en": "Vikram Nagar", "name_hi": "विक्रम नगर", "zone": None, "aliases": []},
    # Mahakal & Old City
    {"slug": "mahakal-area", "name_en": "Mahakal Area", "name_hi": "महाकाल क्षेत्र", "zone": "mahakal-old-city", "aliases": ["Mahakal", "Mahakaleshwar Area"]},
    {"slug": "gopal-mandir", "name_en": "Gopal Mandir", "name_hi": "गोपाल मंदिर", "zone": "mahakal-old-city", "aliases": []},
    {"slug": "jaisinghpura", "name_en": "Jaisinghpura", "name_hi": "जयसिंहपुरा", "zone": "mahakal-old-city", "aliases": ["Jaisingpura"]},
    {"slug": "begum-bagh", "name_en": "Begum Bagh", "name_hi": "बेगम बाग", "zone": "mahakal-old-city", "aliases": ["Begumbagh"]},
    {"slug": "ramghat-area", "name_en": "Ramghat Area", "name_hi": "रामघाट क्षेत्र", "zone": "mahakal-old-city", "aliases": ["Ramghat", "Ram Ghat"]},
    {"slug": "patni-bazaar", "name_en": "Patni Bazaar", "name_hi": "पटनी बाज़ार", "zone": "mahakal-old-city", "aliases": ["Patni Bazar"]},
    # Indore Road & Nagziri
    {"slug": "indore-road", "name_en": "Indore Road", "name_hi": "इंदौर रोड", "zone": "indore-road-nagziri", "aliases": []},
    {"slug": "nagziri", "name_en": "Nagziri", "name_hi": "नागझिरी", "zone": "indore-road-nagziri", "aliases": ["Nagjhiri"]},
    {"slug": "sanwer-road", "name_en": "Sanwer Road", "name_hi": "सांवेर रोड", "zone": "indore-road-nagziri", "aliases": []},
    {"slug": "shipra-vihar", "name_en": "Shipra Vihar", "name_hi": "शिप्रा विहार", "zone": None, "aliases": ["Kshipra Vihar"]},
    {"slug": "motibagh-colony", "name_en": "Motibagh Colony", "name_hi": "मोतीबाग कॉलोनी", "zone": None, "aliases": ["Moti Bagh Colony"]},
    {"slug": "pawapuri-colony", "name_en": "Pawapuri Colony", "name_hi": "पावापुरी कॉलोनी", "zone": None, "aliases": []},
    # Dewas Road & developing belts
    {"slug": "dewas-road", "name_en": "Dewas Road", "name_hi": "देवास रोड", "zone": "dewas-road-developing", "aliases": []},
    {"slug": "agar-road", "name_en": "Agar Road", "name_hi": "आगर रोड", "zone": "dewas-road-developing", "aliases": []},
    {"slug": "maksi-road", "name_en": "Maksi Road", "name_hi": "मक्सी रोड", "zone": "dewas-road-developing", "aliases": []},
    {"slug": "kanipura-road", "name_en": "Kanipura Road", "name_hi": "कानीपुरा रोड", "zone": "dewas-road-developing", "aliases": []},
    {"slug": "chandukhedi", "name_en": "Chandukhedi", "name_hi": "चंदूखेड़ी", "zone": "dewas-road-developing", "aliases": ["Chandu Khedi"]},
    {"slug": "pandyakhedi", "name_en": "Pandyakhedi", "name_hi": "पंड्याखेड़ी", "zone": "dewas-road-developing", "aliases": ["Pandya Khedi"]},
    {"slug": "vasant-vihar", "name_en": "Vasant Vihar", "name_hi": "वसंत विहार", "zone": None, "aliases": []},
]

CATEGORIES = [
    {"slug": "buy", "name_en": "Buy", "name_hi": "खरीदें", "kind": "purpose", "icon": "home-outline", "order": 1},
    {"slug": "rent", "name_en": "Rent", "name_hi": "किराया", "kind": "purpose", "icon": "key-outline", "order": 2},
    {"slug": "residential", "name_en": "Residential", "name_hi": "आवासीय", "kind": "segment", "icon": "bed-outline", "order": 3},
    {"slug": "commercial", "name_en": "Commercial", "name_hi": "व्यावसायिक", "kind": "segment", "icon": "storefront-outline", "order": 4},
    {"slug": "plot-land", "name_en": "Plot/Land", "name_hi": "प्लॉट/ज़मीन", "kind": "segment", "icon": "map-outline", "order": 5},
    {"slug": "new-projects", "name_en": "New Projects", "name_hi": "नए प्रोजेक्ट", "kind": "segment", "icon": "business-outline", "order": 6},
]

PROPERTY_TYPES = [
    {"slug": "apartment", "name_en": "Apartment", "name_hi": "अपार्टमेंट", "segment": "residential", "has_bhk": True},
    {"slug": "independent-house", "name_en": "Independent House", "name_hi": "स्वतंत्र मकान", "segment": "residential", "has_bhk": True},
    {"slug": "villa", "name_en": "Villa", "name_hi": "विला", "segment": "residential", "has_bhk": True},
    {"slug": "builder-floor", "name_en": "Builder Floor", "name_hi": "बिल्डर फ्लोर", "segment": "residential", "has_bhk": True},
    {"slug": "pg-hostel", "name_en": "PG / Hostel", "name_hi": "पीजी / हॉस्टल", "segment": "residential", "has_bhk": False},
    {"slug": "residential-plot", "name_en": "Residential Plot", "name_hi": "आवासीय प्लॉट", "segment": "plot-land", "has_bhk": False},
    {"slug": "agricultural-land", "name_en": "Agricultural Land", "name_hi": "कृषि भूमि", "segment": "plot-land", "has_bhk": False},
    {"slug": "shop", "name_en": "Shop", "name_hi": "दुकान", "segment": "commercial", "has_bhk": False},
    {"slug": "office", "name_en": "Office Space", "name_hi": "ऑफिस स्पेस", "segment": "commercial", "has_bhk": False},
    {"slug": "warehouse", "name_en": "Warehouse / Godown", "name_hi": "गोदाम", "segment": "commercial", "has_bhk": False},
]

AMENITIES = [
    {"slug": "parking", "name_en": "Parking", "name_hi": "पार्किंग", "icon": "car-outline"},
    {"slug": "power-backup", "name_en": "Power Backup", "name_hi": "पावर बैकअप", "icon": "flash-outline"},
    {"slug": "lift", "name_en": "Lift", "name_hi": "लिफ्ट", "icon": "swap-vertical-outline"},
    {"slug": "security", "name_en": "24x7 Security", "name_hi": "24x7 सुरक्षा", "icon": "shield-checkmark-outline"},
    {"slug": "water-supply", "name_en": "Water Supply", "name_hi": "पानी की सुविधा", "icon": "water-outline"},
    {"slug": "garden", "name_en": "Garden", "name_hi": "बगीचा", "icon": "leaf-outline"},
    {"slug": "gym", "name_en": "Gym", "name_hi": "जिम", "icon": "barbell-outline"},
    {"slug": "cctv", "name_en": "CCTV", "name_hi": "सीसीटीवी", "icon": "videocam-outline"},
    {"slug": "gated-community", "name_en": "Gated Community", "name_hi": "गेटेड सोसाइटी", "icon": "lock-closed-outline"},
    {"slug": "temple-nearby", "name_en": "Temple Nearby", "name_hi": "पास में मंदिर", "icon": "flower-outline"},
    {"slug": "school-nearby", "name_en": "School Nearby", "name_hi": "पास में स्कूल", "icon": "school-outline"},
    {"slug": "corner-plot", "name_en": "Corner Plot", "name_hi": "कॉर्नर प्लॉट", "icon": "grid-outline"},
]

LISTING_STATUSES = [
    {"slug": "draft", "name_en": "Draft", "name_hi": "ड्राफ्ट"},
    {"slug": "pending_review", "name_en": "Pending Review", "name_hi": "समीक्षा लंबित"},
    {"slug": "active", "name_en": "Active", "name_hi": "सक्रिय"},
    {"slug": "rejected", "name_en": "Rejected", "name_hi": "अस्वीकृत"},
    {"slug": "expired", "name_en": "Expired", "name_hi": "समाप्त"},
    {"slug": "sold_rented", "name_en": "Sold / Rented", "name_hi": "बिक/किराए पर गया"},
]

VERIFICATION_STATUSES = [
    {"slug": "unverified", "name_en": "Unverified", "name_hi": "असत्यापित"},
    {"slug": "pending", "name_en": "Verification Pending", "name_hi": "सत्यापन लंबित"},
    {"slug": "verified", "name_en": "Verified", "name_hi": "सत्यापित"},
    {"slug": "rejected", "name_en": "Verification Rejected", "name_hi": "सत्यापन अस्वीकृत"},
]

IMG_VILLA_1 = "https://images.unsplash.com/photo-1628012209120-d9db7abf7eab?crop=entropy&cs=srgb&fm=jpg&q=70&w=1200"
IMG_VILLA_2 = "https://images.unsplash.com/photo-1722421492323-eaf9c401befe?crop=entropy&cs=srgb&fm=jpg&q=70&w=1200"
IMG_PLOT = "https://images.unsplash.com/photo-1495107334309-fcf20504a5ab?crop=entropy&cs=srgb&fm=jpg&q=70&w=1200"
IMG_INTERIOR = "https://images.unsplash.com/photo-1564078516393-cf04bd966897?crop=entropy&cs=srgb&fm=jpg&q=70&w=1200"
IMG_APT = "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?crop=entropy&cs=srgb&fm=jpg&q=70&w=1200"
IMG_SHOP = "https://images.unsplash.com/photo-1604719312566-8912e9227c6a?crop=entropy&cs=srgb&fm=jpg&q=70&w=1200"
IMG_OFFICE = "https://images.unsplash.com/photo-1497366216548-37526070297c?crop=entropy&cs=srgb&fm=jpg&q=70&w=1200"

# FICTIONAL demo listings. Prices are illustrative placeholders, NOT market data.
DEMO_LISTINGS = [
    {"demo_key": "demo-001", "title_en": "2 BHK Apartment (Demo)", "title_hi": "2 BHK अपार्टमेंट (डेमो)", "purpose": "buy", "segment": "residential", "type": "apartment", "locality": "nanakheda", "price": 3200000, "bhk": 2, "bathrooms": 2, "area_sqft": 1050, "furnishing": "semi-furnished", "amenities": ["parking", "lift", "power-backup", "security"], "images": [IMG_APT, IMG_INTERIOR]},
    {"demo_key": "demo-002", "title_en": "3 BHK Independent House (Demo)", "title_hi": "3 BHK स्वतंत्र मकान (डेमो)", "purpose": "buy", "segment": "residential", "type": "independent-house", "locality": "rishi-nagar", "price": 6800000, "bhk": 3, "bathrooms": 3, "area_sqft": 1800, "furnishing": "unfurnished", "amenities": ["parking", "water-supply", "garden", "school-nearby"], "images": [IMG_VILLA_2, IMG_INTERIOR]},
    {"demo_key": "demo-003", "title_en": "4 BHK Villa (Demo)", "title_hi": "4 BHK विला (डेमो)", "purpose": "buy", "segment": "residential", "type": "villa", "locality": "university-road", "price": 14500000, "bhk": 4, "bathrooms": 4, "area_sqft": 3200, "furnishing": "furnished", "amenities": ["parking", "garden", "gym", "security", "cctv", "gated-community"], "images": [IMG_VILLA_1, IMG_INTERIOR, IMG_VILLA_2]},
    {"demo_key": "demo-004", "title_en": "1 BHK Flat for Rent (Demo)", "title_hi": "1 BHK फ्लैट किराए पर (डेमो)", "purpose": "rent", "segment": "residential", "type": "apartment", "locality": "freeganj", "price": 8000, "bhk": 1, "bathrooms": 1, "area_sqft": 550, "furnishing": "semi-furnished", "amenities": ["water-supply", "power-backup"], "images": [IMG_INTERIOR, IMG_APT]},
    {"demo_key": "demo-005", "title_en": "2 BHK Builder Floor for Rent (Demo)", "title_hi": "2 BHK बिल्डर फ्लोर किराए पर (डेमो)", "purpose": "rent", "segment": "residential", "type": "builder-floor", "locality": "madhav-nagar", "price": 14000, "bhk": 2, "bathrooms": 2, "area_sqft": 950, "furnishing": "furnished", "amenities": ["parking", "security", "water-supply"], "images": [IMG_APT, IMG_INTERIOR]},
    {"demo_key": "demo-006", "title_en": "Residential Plot (Demo)", "title_hi": "आवासीय प्लॉट (डेमो)", "purpose": "buy", "segment": "plot-land", "type": "residential-plot", "locality": "dewas-road", "price": 2400000, "bhk": None, "bathrooms": None, "area_sqft": 1500, "furnishing": None, "amenities": ["corner-plot", "gated-community"], "images": [IMG_PLOT]},
    {"demo_key": "demo-007", "title_en": "Plot near Developing Belt (Demo)", "title_hi": "विकासशील क्षेत्र में प्लॉट (डेमो)", "purpose": "buy", "segment": "plot-land", "type": "residential-plot", "locality": "agar-road", "price": 1500000, "bhk": None, "bathrooms": None, "area_sqft": 1200, "furnishing": None, "amenities": ["water-supply"], "images": [IMG_PLOT]},
    {"demo_key": "demo-008", "title_en": "Shop near Temple Route (Demo)", "title_hi": "मंदिर मार्ग के पास दुकान (डेमो)", "purpose": "rent", "segment": "commercial", "type": "shop", "locality": "mahakal-area", "price": 25000, "bhk": None, "bathrooms": None, "area_sqft": 300, "furnishing": "unfurnished", "amenities": ["cctv", "temple-nearby"], "images": [IMG_SHOP]},
    {"demo_key": "demo-009", "title_en": "Office Space (Demo)", "title_hi": "ऑफिस स्पेस (डेमो)", "purpose": "rent", "segment": "commercial", "type": "office", "locality": "tower-chowk", "price": 35000, "bhk": None, "bathrooms": 1, "area_sqft": 800, "furnishing": "furnished", "amenities": ["lift", "power-backup", "parking", "cctv"], "images": [IMG_OFFICE]},
    {"demo_key": "demo-010", "title_en": "3 BHK Apartment (Demo)", "title_hi": "3 BHK अपार्टमेंट (डेमो)", "purpose": "buy", "segment": "new-projects", "type": "apartment", "locality": "indore-road", "price": 5400000, "bhk": 3, "bathrooms": 2, "area_sqft": 1450, "furnishing": "unfurnished", "amenities": ["lift", "gym", "parking", "security", "power-backup"], "images": [IMG_APT, IMG_INTERIOR]},
    {"demo_key": "demo-011", "title_en": "2 BHK House for Rent (Demo)", "title_hi": "2 BHK मकान किराए पर (डेमो)", "purpose": "rent", "segment": "residential", "type": "independent-house", "locality": "nagziri", "price": 11000, "bhk": 2, "bathrooms": 1, "area_sqft": 900, "furnishing": "unfurnished", "amenities": ["parking", "water-supply"], "images": [IMG_VILLA_2]},
    {"demo_key": "demo-012", "title_en": "Old City House (Demo)", "title_hi": "पुराने शहर में मकान (डेमो)", "purpose": "buy", "segment": "residential", "type": "independent-house", "locality": "gopal-mandir", "price": 4200000, "bhk": 2, "bathrooms": 2, "area_sqft": 1100, "furnishing": "unfurnished", "amenities": ["temple-nearby", "water-supply"], "images": [IMG_VILLA_1]},
    {"demo_key": "demo-013", "title_en": "Student PG (Demo)", "title_hi": "छात्र पीजी (डेमो)", "purpose": "rent", "segment": "residential", "type": "pg-hostel", "locality": "university-road", "price": 5000, "bhk": None, "bathrooms": 1, "area_sqft": 200, "furnishing": "furnished", "amenities": ["water-supply", "power-backup", "cctv"], "images": [IMG_INTERIOR]},
    {"demo_key": "demo-014", "title_en": "3 BHK Villa in Project (Demo)", "title_hi": "प्रोजेक्ट में 3 BHK विला (डेमो)", "purpose": "buy", "segment": "new-projects", "type": "villa", "locality": "maksi-road", "price": 7900000, "bhk": 3, "bathrooms": 3, "area_sqft": 2100, "furnishing": "semi-furnished", "amenities": ["gated-community", "garden", "security", "parking"], "images": [IMG_VILLA_1, IMG_VILLA_2]},
    {"demo_key": "demo-015", "title_en": "Warehouse (Demo)", "title_hi": "गोदाम (डेमो)", "purpose": "rent", "segment": "commercial", "type": "warehouse", "locality": "sanwer-road", "price": 45000, "bhk": None, "bathrooms": None, "area_sqft": 5000, "furnishing": None, "amenities": ["parking", "security"], "images": [IMG_PLOT]},
    {"demo_key": "demo-016", "title_en": "2 BHK Apartment (Demo)", "title_hi": "2 BHK अपार्टमेंट (डेमो)", "purpose": "buy", "segment": "residential", "type": "apartment", "locality": "rishi-nagar-extension", "price": 3600000, "bhk": 2, "bathrooms": 2, "area_sqft": 1150, "furnishing": "semi-furnished", "amenities": ["lift", "parking", "power-backup"], "images": [IMG_APT]},
    {"demo_key": "demo-017", "title_en": "Agricultural Land (Demo)", "title_hi": "कृषि भूमि (डेमो)", "purpose": "buy", "segment": "plot-land", "type": "agricultural-land", "locality": "pandyakhedi", "price": 9500000, "bhk": None, "bathrooms": None, "area_sqft": 43560, "furnishing": None, "amenities": ["water-supply"], "images": [IMG_PLOT]},
    {"demo_key": "demo-019", "title_en": "2 BHK Flat in Central Area (Demo)", "title_hi": "मध्य क्षेत्र में 2 BHK फ्लैट (डेमो)", "purpose": "buy", "segment": "residential", "type": "apartment", "locality": "sethi-nagar", "price": 3900000, "bhk": 2, "bathrooms": 2, "area_sqft": 1000, "furnishing": "semi-furnished", "amenities": ["lift", "parking", "security"], "images": [IMG_APT, IMG_INTERIOR]},
    {"demo_key": "demo-020", "title_en": "Shop for Sale (Demo)", "title_hi": "दुकान बिक्री हेतु (डेमो)", "purpose": "buy", "segment": "commercial", "type": "shop", "locality": "freeganj", "price": 4500000, "bhk": None, "bathrooms": None, "area_sqft": 250, "furnishing": "unfurnished", "amenities": ["cctv", "parking"], "images": [IMG_SHOP]},
    {"demo_key": "demo-018", "title_en": "1 BHK Near Ramghat (Demo)", "title_hi": "रामघाट के पास 1 BHK (डेमो)", "purpose": "rent", "segment": "residential", "type": "apartment", "locality": "ramghat-area", "price": 7000, "bhk": 1, "bathrooms": 1, "area_sqft": 500, "furnishing": "unfurnished", "amenities": ["temple-nearby"], "images": [IMG_INTERIOR]},
]
