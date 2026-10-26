"""Decide whether a job is an internship / new-grad role, and whether it's in the US."""
import re

INTERN_RE = re.compile(
    r"\bintern(s|ship|ships)?\b|\bco-?op\b|\bworking student\b|\bstudent\b|\bapprentice(ship)?\b"
    r"|\bsummer 20\d\d\b|\bfall 20\d\d\b|\bspring 20\d\d\b",
    re.I,
)

NEW_GRAD_RE = re.compile(
    r"\bgrads?\b|\bgraduate\b|new[\s-]?grad"
    r"|entry[\s-]?level|early[\s-]?career|\bNCG\b|\bRCG\b|\bcampus\b|rotational|\buniversity\b"
    r"|\bassociate (engineer|scientist|designer)\b"
    r"|\b(engineer|scientist|designer|technician|analyst|developer)\s*(I|1)\b",
    re.I,
)

# Titles that are clearly not student/entry roles even if a keyword matches.
EXCLUDE_RE = re.compile(
    r"\b(senior|sr\.?|staff|principal|manager|director|head of|vp|vice president|architect|fellow"
    r"|distinguished|recruiter|recruiting|program manager)\b",
    re.I,
)


# Business roles are dropped unless the title is also technical ("Sales Engineer Intern" stays).
NON_TECH_RE = re.compile(
    r"\b(accounting|accountant|finance|financial|tax|legal|paralegal|counsel|human resources|HR|payroll"
    r"|talent|marketing|sales|communications|public relations|procurement|purchasing|trade compliance"
    r"|administrative|admin|office|receptionist|treasury|audit|investor relations|real estate|facilities)\b",
    re.I,
)
TECH_RE = re.compile(r"engineer|engineering|scientist|technician|developer|design|hardware|software|silicon"
                     r"|firmware|data|research|physics|chemist|process|device|test|validation|verification",
                     re.I)


def classify(title, hint=None):
    """Return "Internship", "New Grad", or None.

    `hint` lets a source pass its own label (e.g. a board that tags jobs as internships).
    """
    if EXCLUDE_RE.search(title):
        return None
    if NON_TECH_RE.search(title) and not TECH_RE.search(title):
        return None
    if hint == "Internship" or INTERN_RE.search(title):
        return "Internship"
    if hint == "New Grad" or NEW_GRAD_RE.search(title):
        return "New Grad"
    return None


US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
]
US_RE = re.compile(
    r"united states|\b(?-i:USA|US)\b|\bU\.S\.|" + "|".join(rf"\b{s}\b" for s in US_STATES), re.I
)

NON_US_RE = re.compile(
    r"china|\bindia\b|taiwan|japan|korea|germany|france|israel|singapore|malaysia|vietnam|philippines"
    r"|canada|mexico|united kingdom|\bUK\b|england|scotland|wales|ireland|netherlands|belgium|italy"
    r"|armenia|ukraine|greece|bulgaria|slovakia|slovenia|croatia|estonia|latvia|lithuania|luxembourg"
    r"|morocco|tunisia|south africa|nigeria|kenya|saudi|emirates|\bUAE\b|qatar|jordan|pakistan"
    r"|bangladesh|sri lanka|cambodia|chile|colombia|peru|uruguay|kazakhstan|georgia \(country\)"
    r"|spain|portugal|poland|romania|czech|austria|switzerland|sweden|finland|denmark|norway|hungary"
    r"|serbia|turkey|egypt|brazil|costa rica|thailand|indonesia|australia|new zealand|argentina"
    r"|bangalore|bengaluru|hyderabad|noida|pune|chennai|ahmedabad|shanghai|beijing|shenzhen|xi'?an"
    r"|wuhan|hsinchu|taipei|tainan|tokyo|osaka|seoul|munich|dresden|penang|kuala lumpur|toronto"
    r"|ottawa|markham|vancouver|montreal|haifa|tel aviv|petah tikva|herzliya|cork|limerick|dublin"
    r"|eindhoven|veldhoven|ho chi minh|da nang|hanoi|manila|cebu|guadalajara|hong kong|grenoble"
    r"|sophia antipolis|cambridge, uk|bristol|edinburgh|krakow|bucharest|cairo|ontario|quebec"
    r"|british columbia|alberta"
    # cities that show up without a country
    r"|toulouse|melaka|villach|caen|samut prakan|batu kawan|nijmegen|gratkorn|belo horizonte|hamburg"
    r"|tianjin|bangkok|valbonne|yokkaichi|kulim|petah|seongnam|rehovot|klagenfurt|graz|saclay|yokneam"
    r"|bundang|hal kirkop|glasgow|chongqing|hefei|ipoh|kanagawa|milan|adliswil|warstein|deutschland"
    r"|kitakami|kaohsiung|padua|padova|hemel hempstead|brno|langen|frankfurt|kamimashiki|chitose"
    r"|london|linkou|budapest|catania|dong nai|viet nam|wuxi|taoyuan|istanbul|türkiye|münchen|mexicali"
    r"|shenzen|sibiu|suzhou|madrid|sofia|leuven|hoofddorp|dalian|leixlip|alzenau|treviso|taichung"
    r"|guangzhou|yixing|hangzhou|chengdu|hiroshima|kumamoto|nagoya|kyoto|regensburg|erlangen|stuttgart"
    r"|berlin|paris|crolles|rousset|agrate|barcelona|bucheon|hwaseong|pyeongtaek|cheongju|icheon|yongin"
    r"|\bmch\b",
    re.I,
)


STATE_CODES = set(
    "AL AK AZ AR CA CO CT FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY "
    "NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split()
)
# "Yerevan, AM" / "Kanagawa, JP": a trailing 2-letter code that isn't a US state is a country.
# Also matches "Mexicali, BCN, MX, 21259" (country code, then a postal code).
TRAILING_CODE_RE = re.compile(r",\s*([A-Z]{2})(?:,\s*[\w-]+)?\s*$")
# "Hiroshima,JPN", "KaohsiungTWN (+3 more)": 3-letter country codes.
ISO3_RE = re.compile(r"(JPN|CHN|TWN|KOR|ISR|MYS|SGP|DEU|ITA|IRL|NLD|FRA|IND|CRI|PHL|VNM|THA|GBR|AUT|CHE|MEX|CAN|BEL|POL|ROU|CZE|HUN|ESP|PRT|SWE|FIN|DNK|NOR|BRA|AUS)\b")
# "MY-Batu Kawan", "SGP - Woodlands", "CH - Adliswil", "SG"
COUNTRY_PREFIX_RE = re.compile(r"^(MY|MYS|SG|SGP|KR|TW|CH|JP|CN|IN|DE|IL|PH|VN|TH|FR|IT|UK|GB|IE|NL|AT)(\s*-|\s*$)")


def is_us(location):
    """True if the location looks like the US (or is unknown, e.g. "Remote" or "3 Locations")."""
    loc = location or ""
    if US_RE.search(loc):
        return True
    if NON_US_RE.search(loc):
        return False
    if ISO3_RE.search(loc) or COUNTRY_PREFIX_RE.search(loc):
        return False
    m = TRAILING_CODE_RE.search(loc)
    if m and m.group(1) not in STATE_CODES:
        return False
    return True  # e.g. "Austin, TX", "Remote", "3 Locations": keep it


COMPANY_SUFFIXES = {"inc", "incorporated", "corporation", "corp", "co", "ltd", "llc", "plc", "the",
                    "technology", "technologies", "company", "group", "holdings", "nv", "ag", "sa"}


def company_key(name):
    """'Micron Technology, Inc.' -> 'micron' so the same company matches across sites."""
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower()).split()
    return " ".join(w for w in words if w not in COMPANY_SUFFIXES)
