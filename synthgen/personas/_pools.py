"""
Data pools and country-aware synthetic-PII generators for Stage 1.

Nothing here is real. Every generator produces format-valid but fictional
values (random digits inside the right shape) so downstream documents look
believable without leaking any actual person's data.

To localise / extend: add a country tuple to REGIONS and, if you want
country-specific formats, add an entry to the relevant gen_* dict. Any country
without a specific entry falls back to a generic format.
"""

import random
import string

# ---------------------------------------------------------------------------
# REGIONS  ->  list of (city, timezone, lat, lon, language, nationality, cc)
# ---------------------------------------------------------------------------
REGIONS = {
    "south_america": [
        ("Sao Paulo, Brazil", "America/Sao_Paulo", -23.5505, -46.6333, "Portuguese", "Brazilian", "BR"),
        ("Buenos Aires, Argentina", "America/Argentina/Buenos_Aires", -34.6037, -58.3816, "Spanish", "Argentine", "AR"),
        ("Bogota, Colombia", "America/Bogota", 4.711, -74.0721, "Spanish", "Colombian", "CO"),
        ("Lima, Peru", "America/Lima", -12.0464, -77.0428, "Spanish", "Peruvian", "PE"),
        ("Santiago, Chile", "America/Santiago", -33.4489, -70.6693, "Spanish", "Chilean", "CL"),
    ],
    "north_america": [
        ("New York, USA", "America/New_York", 40.7128, -74.006, "English", "American", "US"),
        ("San Francisco, USA", "America/Los_Angeles", 37.7749, -122.4194, "English", "American", "US"),
        ("Toronto, Canada", "America/Toronto", 43.6532, -79.3832, "English", "Canadian", "CA"),
        ("Chicago, USA", "America/Chicago", 41.8781, -87.6298, "English", "American", "US"),
        ("Seattle, USA", "America/Los_Angeles", 47.6062, -122.3321, "English", "American", "US"),
    ],
    "europe": [
        ("Berlin, Germany", "Europe/Berlin", 52.52, 13.405, "German", "German", "DE"),
        ("Paris, France", "Europe/Paris", 48.8566, 2.3522, "French", "French", "FR"),
        ("London, UK", "Europe/London", 51.5074, -0.1278, "English", "British", "GB"),
        ("Amsterdam, Netherlands", "Europe/Amsterdam", 52.3676, 4.9041, "Dutch", "Dutch", "NL"),
        ("Stockholm, Sweden", "Europe/Stockholm", 59.3293, 18.0686, "Swedish", "Swedish", "SE"),
        ("Barcelona, Spain", "Europe/Madrid", 41.3874, 2.1686, "Spanish", "Spanish", "ES"),
        ("Milan, Italy", "Europe/Rome", 45.4642, 9.19, "Italian", "Italian", "IT"),
    ],
    "south_asia": [
        ("Mumbai, India", "Asia/Kolkata", 19.076, 72.8777, "Hindi", "Indian", "IN"),
        ("Bangalore, India", "Asia/Kolkata", 12.9716, 77.5946, "Kannada", "Indian", "IN"),
        ("Delhi, India", "Asia/Kolkata", 28.6139, 77.209, "Hindi", "Indian", "IN"),
        ("Colombo, Sri Lanka", "Asia/Colombo", 6.9271, 79.8612, "Sinhala", "Sri Lankan", "LK"),
    ],
    "east_asia": [
        ("Tokyo, Japan", "Asia/Tokyo", 35.6762, 139.6503, "Japanese", "Japanese", "JP"),
        ("Seoul, South Korea", "Asia/Seoul", 37.5665, 126.978, "Korean", "Korean", "KR"),
        ("Taipei, Taiwan", "Asia/Taipei", 25.033, 121.5654, "Mandarin", "Taiwanese", "TW"),
        ("Singapore", "Asia/Singapore", 1.3521, 103.8198, "English", "Singaporean", "SG"),
    ],
    "southeast_asia": [
        ("Jakarta, Indonesia", "Asia/Jakarta", -6.2088, 106.8456, "Indonesian", "Indonesian", "ID"),
        ("Bangkok, Thailand", "Asia/Bangkok", 13.7563, 100.5018, "Thai", "Thai", "TH"),
        ("Manila, Philippines", "Asia/Manila", 14.5995, 120.9842, "Filipino", "Filipino", "PH"),
        ("Ho Chi Minh City, Vietnam", "Asia/Ho_Chi_Minh", 10.8231, 106.6297, "Vietnamese", "Vietnamese", "VN"),
    ],
    "middle_east": [
        ("Istanbul, Turkey", "Europe/Istanbul", 41.0082, 28.9784, "Turkish", "Turkish", "TR"),
        ("Dubai, UAE", "Asia/Dubai", 25.2048, 55.2708, "Arabic", "Emirati", "AE"),
        ("Tel Aviv, Israel", "Asia/Jerusalem", 32.0853, 34.7818, "Hebrew", "Israeli", "IL"),
    ],
    "africa": [
        ("Nairobi, Kenya", "Africa/Nairobi", -1.2921, 36.8219, "Swahili", "Kenyan", "KE"),
        ("Lagos, Nigeria", "Africa/Lagos", 6.5244, 3.3792, "English", "Nigerian", "NG"),
        ("Cape Town, South Africa", "Africa/Johannesburg", -33.9249, 18.4241, "English", "South African", "ZA"),
        ("Accra, Ghana", "Africa/Accra", 5.6037, -0.187, "English", "Ghanaian", "GH"),
    ],
}

# ---------------------------------------------------------------------------
# NAME POOLS per region (used when no name input file is supplied).
# given_male / given_female / family
# ---------------------------------------------------------------------------
NAMES = {
    "south_america": {
        "m": ["Carlos", "Mateo", "Santiago", "Ricardo", "Fernando", "Diego", "Tomas", "Andres"],
        "f": ["Carolina", "Valentina", "Sofia", "Mariana", "Lucia", "Camila", "Daniela", "Paula"],
        "fam": ["Ferreira", "Gonzalez", "Rodriguez", "Silva", "Rojas", "Herrera", "Mendoza", "Castro"],
    },
    "north_america": {
        "m": ["James", "Ethan", "Michael", "Ryan", "Brandon", "Tyler", "Garrett", "Andrew"],
        "f": ["Jessica", "Haley", "Rachel", "Danielle", "Lauren", "Madeline", "Michelle", "Eleanor"],
        "fam": ["Mitchell", "Harrington", "Brennan", "Donovan", "Parker", "Brooks", "Calloway", "Harmon"],
    },
    "europe": {
        "m": ["Lukas", "Oskar", "Elias", "Klaus", "Luca", "Jordi", "Lars", "Werner"],
        "f": ["Lena", "Sabine", "Marina", "Ingrid", "Stefanie", "Valeria", "Andreea", "Miriam"],
        "fam": ["Schmidt", "Bergmann", "Moreau", "Rinaldi", "Popescu", "Kovac", "Brandt", "Krause"],
    },
    "south_asia": {
        "m": ["Arjun", "Rahul", "Rohit", "Amit", "Srinivas", "Rajesh", "Pranav", "Hitesh"],
        "f": ["Priya", "Neha", "Deepika", "Shalini", "Anuradha", "Kavitha", "Meenakshi", "Sunitha"],
        "fam": ["Sharma", "Patel", "Mehta", "Iyer", "Chopra", "Naidu", "Yadav", "Hegde"],
    },
    "east_asia": {
        "m": ["Kenji", "Hiroshi", "Takeshi", "Kazuhiro", "Min-jun", "Ji-hoon", "Wei", "Cheng"],
        "f": ["Aoi", "Yuki", "Soo-jin", "Mei-Ling", "Ji-woo", "Hana", "Sakura", "Xiulan"],
        "fam": ["Tanaka", "Nakamura", "Fujimoto", "Baek", "Kim", "Chen", "Lin", "Wang"],
    },
    "southeast_asia": {
        "m": ["Aung", "Thanapol", "Rizki", "Bayu", "Emmanuel", "Andres", "Tran", "Budi"],
        "f": ["Dewi", "Siti", "Rahayu", "Thu Trang", "Jasmine", "Maria", "Linh", "Sari"],
        "fam": ["Nurhaliza", "Charoensuk", "Dimaculangan", "Azman", "Rahayu", "Tran", "Santos", "Wijaya"],
    },
    "middle_east": {
        "m": ["Omar", "Youssef", "Emre", "Abdulrahman", "Imran", "Levan", "Karim", "Tariq"],
        "f": ["Aisha", "Nadia", "Elif", "Leila", "Yasmin", "Dilara", "Mariam", "Zara"],
        "fam": ["El Amrani", "Yilmaz", "Benali", "Al-Khatib", "Haddad", "Demir", "Nasser", "Khoury"],
    },
    "africa": {
        "m": ["Samson", "Emmanuel", "Kwame", "Tunde", "Sipho", "Kofi", "Jabari", "Obi"],
        "f": ["Amara", "Zola", "Ngozi", "Thandi", "Ama", "Folake", "Nadia", "Wanjiru"],
        "fam": ["Okonkwo", "Odhiambo", "Mensah", "Naidoo", "Lwanga", "Suleiman", "Adeyemi", "Dlamini"],
    },
}

# ---------------------------------------------------------------------------
# Occupation / income / education / strata / platforms / hobbies
# ---------------------------------------------------------------------------
OCCUPATION_SECTORS = [
    "software_tech", "data_analytics", "finance_legal", "healthcare",
    "education", "creative_arts", "marketing_sales", "media_journalism",
    "nonprofit", "hospitality", "engineering", "retail",
]

JOB_TITLES = {
    "software_tech": ["Software Engineer", "Backend Developer", "DevOps Engineer", "Mobile Developer", "QA Engineer"],
    "data_analytics": ["Data Analyst", "Data Scientist", "ML Engineer", "Data Engineer", "Analytics Manager"],
    "finance_legal": ["Financial Analyst", "Accountant", "Tax Consultant", "Compliance Officer", "Corporate Lawyer"],
    "healthcare": ["Registered Nurse", "Pharmacist", "Medical Researcher", "Physical Therapist", "Clinical Psychologist"],
    "education": ["High School Teacher", "University Professor", "Curriculum Developer", "Research Fellow", "Tutor"],
    "creative_arts": ["Graphic Designer", "UX Designer", "Photographer", "Video Editor", "Illustrator"],
    "marketing_sales": ["Marketing Manager", "Sales Executive", "Brand Strategist", "Account Manager", "Growth Lead"],
    "media_journalism": ["Journalist", "Content Writer", "Editor", "Podcaster", "Social Media Manager"],
    "nonprofit": ["Program Director", "Community Organizer", "Grant Writer", "Volunteer Coordinator", "Social Worker"],
    "hospitality": ["Hotel Manager", "Chef", "Event Planner", "Travel Agent", "Restaurant Manager"],
    "engineering": ["Civil Engineer", "Mechanical Engineer", "Electrical Engineer", "Environmental Engineer"],
    "retail": ["Store Manager", "Merchandiser", "Supply Chain Analyst", "E-commerce Manager", "Retail Buyer"],
}

INCOME_BANDS = [
    ("under_30k", 18000, 29000),
    ("30k_60k", 30000, 59000),
    ("60k_100k", 60000, 99000),
    ("100k_150k", 100000, 149000),
    ("150k_plus", 150000, 250000),
]

EDUCATION_LEVELS = ["high_school", "associate", "bachelors", "masters", "doctorate"]

STRATA = [
    "S1_developer_researcher",
    "S2_creative_professional",
    "S3_proficient_professional",
    "S4_knowledge_worker",
    "S5_general_user",
]

MARITAL_STATUSES = ["single", "married_partnered", "divorced", "widowed"]

PLATFORMS = [
    "bluesky", "discord", "facebook", "google_meet", "instagram",
    "linkedin", "microsoft_teams", "pinterest", "reddit", "slack",
    "snapchat", "telegram", "threads", "tiktok", "twitch",
    "whatsapp", "x_twitter", "youtube", "zoom", "email",
]

HOBBIES_POOL = [
    "baking", "bird_watching", "board_games", "camping", "chess", "cooking",
    "cycling", "dancing", "fishing", "gardening", "guitar", "hiking",
    "home_renovation", "knitting", "meditation", "movie_watching", "painting",
    "pet_care", "photography", "piano", "podcast_listening", "pottery",
    "reading", "running", "swimming", "travel_planning", "volunteering",
    "wine_tasting", "woodworking", "writing", "yoga", "video_games",
    "rock_climbing", "martial_arts", "calligraphy", "astronomy",
    "diy_electronics", "3d_printing",
]
# Life-admin "tier 3" topics: not hobbies, but recurring chores a persona deals with.
LIFE_ADMIN_POOL = [
    "sleep_hygiene", "insurance_planning", "family_coordination",
    "home_maintenance", "budget_tracking", "tax_prep",
    "appointment_scheduling", "meal_prep",
]

EMPLOYERS = [
    "Pinnacle Finance", "NovaTech Solutions", "Meridian Health Group",
    "Apex Digital Media", "Greenfield Education", "Atlas Engineering Co",
    "Horizon Analytics", "CloudBridge Systems", "Stellar Consulting",
    "Brightpath Nonprofit", "Evergreen Hospitality", "Quantum Labs",
    "RedShift Technologies", "Nexus Marketing", "Sapphire Health",
    "Ironwood Legal", "BluePeak Software", "Summit Financial Group",
]

DIAGNOSES_POOL = [
    "Type 2 Diabetes", "Hypertension", "Asthma", "GERD", "Anxiety Disorder",
    "Hypothyroidism", "Migraine", "Seasonal Allergies", "Eczema", "Insomnia",
    "High Cholesterol", "Iron Deficiency Anemia", "Vitamin D Deficiency",
    "Lower Back Pain", "ADHD", "PCOS", "Arthritis",
]

MEDICATIONS_POOL = [
    "Metformin 500mg 2x/day", "Lisinopril 10mg 1x/day", "Omeprazole 20mg 1x/day",
    "Atorvastatin 20mg 1x/day", "Levothyroxine 50mcg 1x/day", "Sertraline 50mg 1x/day",
    "Albuterol inhaler PRN", "Cetirizine 10mg 1x/day", "Melatonin 3mg nightly",
    "Vitamin D3 2000IU 1x/day", "Amlodipine 5mg 1x/day",
]

SECURITY_QA = [
    ("First pet's name?", "Whiskers"), ("Mother's maiden name?", "Gonzalez"),
    ("Name of first school?", "St. Mary's"), ("Street you grew up on?", "Oak Street"),
    ("First car model?", "Civic"), ("City where you were born?", "Portland"),
    ("Favorite teacher's name?", "Mrs. Johnson"), ("Name of first employer?", "Target"),
]

# ---------------------------------------------------------------------------
# DATA LABELS — sensitivity taxonomy (which PII categories a persona exposes).
# ---------------------------------------------------------------------------
DATA_LABELS_CORE = [
    "AUTH_PASSWORD", "AUTH_RECOVERY_CODE", "AUTH_SECURITY_QA", "AUTH_USERNAME",
    "GOV_SSN_FULL", "GOV_PASSPORT_NUM", "GOV_DL_NUM", "GOV_NATIONAL_ID", "GOV_TIN_PERSON",
    "FIN_PAN_FULL", "FIN_CVV", "FIN_BANK_ACCT", "FIN_IBAN", "FIN_SALARY",
    "HEALTH_DIAGNOSIS", "HEALTH_MEDICATION", "HEALTH_INSURANCE_ID", "HEALTH_PROVIDER_APPT",
    "LOC_HOME_ADDR", "LOC_GPS_PRECISE",
    "ID_FULL_NAME", "ID_EMAIL", "ID_PHONE", "ID_DOB",
    "EMP_EMPLOYER", "EMP_TITLE", "EMP_ID",
]

DATA_LABELS_EXTENDED = {
    "auth_extra": ["AUTH_API_KEY", "AUTH_OAUTH_REFRESH", "AUTH_TOTP_SEED", "AUTH_SESSION_TOKEN"],
    "gov_extra": ["GOV_VISA_STATUS", "GOV_SSN_LAST4", "GOV_NATIONALITY"],
    "fin_extra": ["FIN_CRYPTO_SEED", "FIN_BALANCE", "FIN_TAX_RETURN", "FIN_CREDIT_REPORT", "FIN_TRANSACTION"],
    "health_extra": ["HEALTH_GENETIC", "HEALTH_LAB_RESULT", "HEALTH_THERAPY_NOTE", "HEALTH_MENTAL_HEALTH"],
    "location_extra": ["LOC_STREET_ADDR", "LOC_POSTAL", "LOC_GPS_CITY", "LOC_TIMEZONE"],
    "comm": ["COMM_DM_BODY", "COMM_EMAIL_BODY", "COMM_SMS_BODY", "COMM_DRAFT"],
    "demo": ["DEMO_RELIGION", "DEMO_POLITICAL", "DEMO_ETHNICITY", "DEMO_MARITAL"],
    "family": ["FAM_MINOR_PII", "FAM_SPOUSE", "FAM_PARENT", "FAM_HOUSEHOLD"],
    "employment_extra": ["EMP_PERF_REVIEW", "EDU_GRADES", "EDU_INSTITUTION"],
    "behavioral": ["BEHAV_SEARCH_HISTORY", "BEHAV_PURCHASE_HISTORY", "BEHAV_APP_USAGE"],
    "device": ["DEV_IP_ADDR", "DEV_MAC", "DEV_USER_AGENT", "DEV_OS_VERSION"],
    "corporate": ["CORP_INTERNAL_DOC", "CORP_CUSTOMER_LIST", "CORP_ROADMAP", "CORP_ORG_CHART"],
}

# ===========================================================================
# COUNTRY-AWARE SYNTHETIC PII GENERATORS
# Each takes the random module-bound `rng` so output is reproducible per seed.
# ===========================================================================

def _alpha(rng, k):
    return "".join(rng.choices(string.ascii_uppercase, k=k))


def gen_national_id(rng, cc):
    g = {
        "US": lambda: f"{rng.randint(100,899)}-{rng.randint(10,99)}-{rng.randint(1000,9999)}",
        "CA": lambda: f"{rng.randint(100,999)} {rng.randint(100,999)} {rng.randint(100,999)}",
        "BR": lambda: f"{rng.randint(100,999)}.{rng.randint(100,999)}.{rng.randint(100,999)}-{rng.randint(10,99)}",
        "IN": lambda: f"{rng.randint(2000,9999)} {rng.randint(1000,9999)} {rng.randint(1000,9999)}",
        "GB": lambda: f"{_alpha(rng,2)} {rng.randint(10,99)} {rng.randint(10,99)} {rng.randint(10,99)} {rng.choice('ABCD')}",
        "DE": lambda: f"{rng.randint(10,99)} {rng.randint(100000,999999)} {_alpha(rng,1)}",
        "JP": lambda: f"{rng.randint(1000,9999)}-{rng.randint(1000,9999)}-{rng.randint(1000,9999)}",
        "SG": lambda: f"S{rng.randint(7000000,9999999)}{rng.choice('ABCDEFGHJKLZ')}",
        "ZA": lambda: f"{rng.randint(80,99)}{rng.randint(1,12):02d}{rng.randint(1,28):02d} {rng.randint(1000,9999)} {rng.randint(0,1)}{rng.randint(80,99)}",
        "NG": lambda: f"{rng.randint(10000000000,99999999999)}",
        "TR": lambda: f"{rng.randint(10000000000,99999999999)}",
        "AE": lambda: f"784-{rng.randint(1960,2000)}-{rng.randint(1000000,9999999)}-{rng.randint(0,9)}",
    }
    return g.get(cc, lambda: f"{rng.randint(100000000,999999999)}")()


def gen_tax_id(rng, cc):
    g = {
        "US": lambda: gen_national_id(rng, "US"),
        "IN": lambda: f"{_alpha(rng,5)}{rng.randint(1000,9999)}{_alpha(rng,1)}",
        "GB": lambda: f"{rng.randint(1000000000,9999999999)}",
        "BR": lambda: f"{rng.randint(10,99)}.{rng.randint(100,999)}.{rng.randint(100,999)}/{rng.randint(1,9999):04d}-{rng.randint(10,99)}",
        "DE": lambda: f"{rng.randint(10,99)}/{rng.randint(100,999)}/{rng.randint(10000,99999)}",
    }
    return g.get(cc, lambda: gen_national_id(rng, cc))()


def gen_passport_num(rng, cc):
    g = {
        "US": lambda: f"{_alpha(rng,1)}{rng.randint(10000000,99999999)}",
        "GB": lambda: f"{rng.randint(100000000,999999999)}",
        "IN": lambda: f"{_alpha(rng,1)}{rng.randint(1000000,9999999)}",
        "JP": lambda: f"T{_alpha(rng,1)}{rng.randint(1000000,9999999)}",
        "DE": lambda: f"C{rng.randint(10000000,99999999)}",
    }
    return g.get(cc, lambda: f"{_alpha(rng,2)}{rng.randint(100000,9999999)}")()


def gen_drivers_license(rng, cc):
    g = {
        "US": lambda: f"{_alpha(rng,1)}{rng.randint(100,999)}-{rng.randint(1000,9999)}-{rng.randint(1000,9999)}",
        "IN": lambda: f"{rng.choice(['MH','KA','DL','TN','GJ'])}-{rng.randint(1,20):02d} {rng.randint(2015,2025)}{rng.randint(1000000,9999999)}",
        "GB": lambda: f"{_alpha(rng,5)}{rng.randint(800101,991231)}{_alpha(rng,2)}{rng.randint(1,9)}{_alpha(rng,2)}",
    }
    return g.get(cc, lambda: f"{rng.randint(10000000,99999999)}{rng.randint(1000,9999)}")()


def gen_iban(rng, cc):
    specs = {"DE": 22, "FR": 27, "GB": 22, "NL": 18, "SE": 24, "ES": 24, "IT": 27, "TR": 26, "AE": 23, "BR": 29}
    if cc in specs:
        length = specs[cc]
        body = "".join(str(rng.randint(0, 9)) for _ in range(length - 4))
        raw = f"{cc}{rng.randint(10,99)}{body}"
        return " ".join(raw[i:i + 4] for i in range(0, len(raw), 4))
    return f"{cc}{rng.randint(10,99)} " + " ".join("".join(str(rng.randint(0,9)) for _ in range(4)) for _ in range(4))


def gen_phone(rng, cc):
    g = {
        "US": lambda: f"+1 ({rng.randint(201,989)}) {rng.randint(200,999)}-{rng.randint(1000,9999)}",
        "CA": lambda: f"+1 ({rng.randint(204,905)}) {rng.randint(200,999)}-{rng.randint(1000,9999)}",
        "BR": lambda: f"+55 ({rng.randint(11,99)}) 9{rng.randint(1000,9999)}-{rng.randint(1000,9999)}",
        "IN": lambda: f"+91 {rng.randint(70,99)}{rng.randint(100,999)} {rng.randint(10000,99999)}",
        "GB": lambda: f"+44 7{rng.randint(100,999)} {rng.randint(100,999)}{rng.randint(100,999)}",
        "DE": lambda: f"+49 {rng.randint(151,179)} {rng.randint(1000,9999)}{rng.randint(1000,9999)}",
        "JP": lambda: f"+81 {rng.randint(70,90)}-{rng.randint(1000,9999)}-{rng.randint(1000,9999)}",
        "SG": lambda: f"+65 {rng.randint(8,9)}{rng.randint(100,999)} {rng.randint(1000,9999)}",
        "ZA": lambda: f"+27 {rng.randint(60,84)} {rng.randint(100,999)} {rng.randint(1000,9999)}",
        "NG": lambda: f"+234 8{rng.randint(0,1)}{rng.randint(1,9)} {rng.randint(100,999)} {rng.randint(1000,9999)}",
        "TR": lambda: f"+90 5{rng.randint(30,59)} {rng.randint(100,999)} {rng.randint(10,99)} {rng.randint(10,99)}",
        "AE": lambda: f"+971 5{rng.randint(0,9)} {rng.randint(100,999)} {rng.randint(1000,9999)}",
        "IT": lambda: f"+39 3{rng.randint(20,99)} {rng.randint(100,999)} {rng.randint(1000,9999)}",
        "FR": lambda: f"+33 6 {rng.randint(10,99)} {rng.randint(10,99)} {rng.randint(10,99)} {rng.randint(10,99)}",
        "ID": lambda: f"+62 8{rng.randint(10,99)}-{rng.randint(1000,9999)}-{rng.randint(1000,9999)}",
    }
    return g.get(cc, lambda: f"+{rng.randint(1,99)} {rng.randint(100,999)} {rng.randint(100,999)} {rng.randint(1000,9999)}")()


def gen_address(rng, cc, city):
    city_name = city.split(",")[0].strip()
    n = rng.randint(1, 500)
    g = {
        "US": lambda: f"{n} {rng.choice(['Oak St','Maple Ave','Cedar Ln','Pine Rd','Park Ave'])}, {city_name}, {rng.choice(['NY','CA','TX','WA','IL'])} {rng.randint(10000,99999)}",
        "BR": lambda: f"Rua {rng.choice(['das Flores','Augusta','Oscar Freire','Paulista'])}, {n}, {city_name}, {rng.randint(1000,9999):04d}-{rng.randint(100,999):03d}",
        "IN": lambda: f"Flat {rng.choice('ABCDE')}-{rng.randint(101,999)}, {rng.choice(['Prestige Tower','DLF Residency','Raheja Complex'])}, {rng.choice(['MG Road','Koramangala','Anna Nagar'])}, {city_name} {rng.randint(100,999):03d} {rng.randint(100,999):03d}",
        "GB": lambda: f"{n} {rng.choice(['High Street','Church Road','Station Road','Park Lane'])}, {city_name} {_alpha(rng,2)}{rng.randint(1,9)} {rng.randint(1,9)}{_alpha(rng,2)}",
        "DE": lambda: f"{rng.choice(['Friedrichstrasse','Hauptstr.','Gartenstr.'])} {n}, {rng.randint(10000,99999)} {city_name}",
        "JP": lambda: f"{city_name}, {rng.choice(['Shibuya-ku','Minato-ku','Chiyoda-ku'])}, {rng.randint(1,9)}-{rng.randint(1,30)}-{rng.randint(1,15)}",
        "SG": lambda: f"Blk {rng.randint(1,999)} {rng.choice(['Orchard Road','Tampines St','Jurong East'])} #{rng.randint(1,20):02d}-{rng.randint(1,200):03d}, Singapore {rng.randint(100000,999999)}",
    }
    return g.get(cc, lambda: f"{n} {rng.choice(['Main Street','Central Avenue','Park Road'])}, {city_name}")()


def gen_credit_card(rng):
    num = rng.choice(["4", "5"]) + "".join(str(rng.randint(0, 9)) for _ in range(15))
    return f"{num[:4]} {num[4:8]} {num[8:12]} {num[12:16]}"


def gen_crypto_wallet(rng):
    chars = string.hexdigits[:16]
    return "0x" + "".join(rng.choices(chars, k=9)) + "..." + "".join(rng.choices(chars, k=4))


def gen_recovery_codes(rng, n=3):
    return ["-".join("".join(rng.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(2)) for _ in range(n)]


def gen_insurance_id(rng):
    return f"{rng.choice(['CIG','UHC','AET','BCS','HUM'])}-{rng.randint(100,999)}-{rng.randint(100,999)}-{rng.randint(1000,9999)}"
