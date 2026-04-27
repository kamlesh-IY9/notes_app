"""Contacts generator — synthetic saved-contact notes with strict US rules."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from .validator import ValidationResult


EXCLUDED_STATES = {"TX", "IL", "WA", "Texas", "Illinois", "Washington"}
EXCLUDED_TERMS = {
    "texas", "illinois", "washington", "seattle", "austin", "dallas",
    "houston", "san antonio", "fort worth", "chicago", "springfield il",
    "tacoma", "spokane", "redmond", "bellevue",
}
EXCLUDED_AREA_CODES = {
    "206", "253", "360", "425", "509", "564",  # WA
    "210", "214", "254", "281", "325", "346", "361", "409", "430",
    "432", "469", "512", "682", "713", "737", "806", "817", "830",
    "832", "903", "915", "936", "940", "956", "972", "979",  # TX
    "217", "224", "309", "312", "331", "447", "464", "618", "630",
    "708", "730", "773", "779", "815", "847", "872",  # IL
}
SAFE_AREA_CODES = [
    "201", "202", "212", "213", "215", "267", "303", "305", "310",
    "323", "404", "415", "470", "516", "602", "617", "646", "650",
    "702", "704", "720", "754", "801", "805", "818", "901", "919",
    "929", "973",
]
EMAIL_DOMAINS = ["gmail.com", "outlook.com", "icloud.com", "protonmail.com", "yahoo.com"]

FIRST_NAMES = [
    "Marcus", "Sarah", "Leo", "Elena", "Parker", "Logan", "Miles", "Nina",
    "Bella", "Bianca", "Derek", "Fiona", "Griffin", "Avery", "Camila",
    "Jordan", "Maya", "Owen", "Rafael", "Sofia", "Tucker", "Eboni",
    "Noah", "Jasmine", "Caleb", "Mila", "Evan", "Naomi", "Dylan",
    "Kara", "Wesley", "Aaliyah", "Mateo", "Reese", "Andre", "Lucia",
]
LAST_NAMES = [
    "Miller", "Brooks", "Sterling", "Mendez", "Vance", "Carter", "Hayes",
    "Rivera", "Morgan", "Patel", "Bennett", "Coleman", "Price", "Ross",
    "Reed", "Foster", "Diaz", "Hughes", "Murphy", "Sullivan", "Bailey",
]
CITIES = [
    "Portland", "Phoenix", "Boston", "Charlotte", "Nashville", "Sacramento", "Denver", "Miami", 
    "Atlanta", "New York", "Las Vegas", "Philadelphia", "Orlando", "Detroit", "Tampa", 
    "San Jose", "San Diego", "Raleigh", "Omaha", "Memphis", "Louisville", "Baltimore", "Columbus"
]


@dataclass
class ContactCategory:
    id: str
    roles: list[str]
    orgs: list[str]
    details: list[str]
    costs: list[str]
    followups: list[str]


CONTACT_CATEGORIES = [
    ContactCategory(
        "home_services",
        ["Gutter Cleaning", "HVAC Repair", "Plumber", "Electrician", "Handyman", "Pool Maintenance", "Home Security", "Pest Control", "Landscaping"],
        ["ClearFlow Gutters", "BrightHome Repair", "SafeHome Systems", "Sparkle Pools", "Metro Handyman", "Cole Pest Control"],
        ["Clean gutters & downspouts.", "AC repair call for upstairs unit.", "Installation for smart sensors.", "Check leak under kitchen sink."],
        ["Quote: $175", "Est: $150-200", "Total quote: $600", "$85 service call"],
        ["Can come Sat morning if it doesn't rain.", "Ask about weekend availability.", "Needs photos before final quote."],
    ),
    ContactCategory(
        "auto_transport",
        ["Auto Shop", "Mobile Detailing", "Mechanic", "Tire Shop", "Driving Instructor", "Airport Pickup", "Car Inspection"],
        ["Parker's Auto Shop", "Logan Mobile Detailing", "Northside Tires", "City Drive School"],
        ["Oil change & brake check due.", "Ceramic coating next month.", "Needs front tire estimate.", "Pickup from airport arrivals."],
        ["Est: $150-200", "Quote: $300", "$60 lesson", "$45 airport run"],
        ["Dropping off the car Thurs morning.", "Check reviews before booking.", "Ask if they take card."],
    ),
    ContactCategory(
        "pets",
        ["Vet", "Dog Groomer", "Pet Sitter", "Dog Walker", "Dog Trainer", "Shelter Contact", "Fish Tank Cleaning", "Cat Sitting"],
        ["City Shelter", "Happy Paws", "Greenway Vet", "PetSmart", "Clean Tank Co"],
        ["Follow up on adoption application.", "Dog meds refill.", "Fish tank cleaning this weekend.", "Ask about puppy training schedule."],
        ["$35 walk", "$90 grooming", "$120 cleaning", "$45/day"],
        ["Home visit scheduled Fri afternoon.", "Text vaccine records before appt."],
    ),
    ContactCategory(
        "health_dental",
        ["Dentist", "Orthodontist", "Optometrist", "Physical Therapy", "Chiropractor", "Pharmacy Tech", "Dermatologist"],
        ["SmileWorks Dental", "Dr. Sarah Eye Clinic", "Peak PT", "BrightView Ortho"],
        ["Eye exam appt next Tuesday.", "Ask about retainer cost.", "Bring old prescription glasses.", "PT eval for knee pain."],
        ["Copay $40", "Est: $250", "$75 session", "Insurance pending"],
        ["Bring insurance card.", "Confirm paperwork online."],
    ),
    ContactCategory(
        "gym_fitness",
        ["Gym Trainer", "Yoga Coach", "Pilates Instructor", "Boxing Coach", "Swim Instructor", "Running Club Lead"],
        ["FitLab", "Core Pilates", "Blue Lane Swim", "Round 3 Boxing", "Sunday Run Club"],
        ["Free assessment session.", "Send workout plan by Wed.", "Beginner swim lesson times.", "Group run starts near the park."],
        ["$60/session", "$120/month", "$35 class", "First class free"],
        ["Ask about evening slots.", "Need waiver before first session."],
    ),
    ContactCategory(
        "school_college",
        ["Teacher", "Tutor", "College Advisor", "Professor", "School Nurse", "Dorm Office", "Financial Aid Contact"],
        ["Maple Ridge School", "Campus Advising", "Northview Tutoring", "Student Health"],
        ["Math tutoring for finals.", "Financial aid form deadline.", "Dorm maintenance follow-up.", "Ask about parent-teacher conference."],
        ["$40/hr", "No fee", "$25 materials", "Payment through portal"],
        ["Email transcript before meeting.", "Bring student ID."],
    ),
    ContactCategory(
        "sports_games",
        ["Soccer Coach", "Basketball Trainer", "Tennis Instructor", "Golf Coach", "Bowling League Contact", "Pickleball Group"],
        ["Eastside Soccer", "Hoop Lab", "City Bowling", "Weekend Pickleball"],
        ["Practice schedule for next week.", "Score sheet from last game.", "Beginner tennis lesson.", "League fees due soon."],
        ["$55 lesson", "$80 league fee", "$25 court fee", "Cash only"],
        ["Text jersey size.", "Ask if rain cancels.", "Bring water bottle."],
    ),
    ContactCategory(
        "music_dance",
        ["Guitar Tutor", "Piano Teacher", "Music Instructor", "Vocal Coach", "Swing Dance Class", "DJ"],
        ["Leo Guitar Lessons", "Derek Music Studio", "City Swing", "Metro Music"],
        ["Teaches acoustic and electric both.", "Swing beginner class on Wed evenings.", "Send playlist for party."],
        ["$45/session", "$40 lesson", "$15 drop-in", "Deposit $100"],
        ["Buy Level 1 theory book.", "Ask about trial lesson."],
    ),
    ContactCategory(
        "barber_salon",
        ["Barber", "Hairdresser", "Nail Tech", "Tailor", "Dry Cleaner", "Eyebrow Threading"],
        ["Custom Tailoring", "Fresh Cut Barbers", "Nail Loft", "Oak Dry Cleaners"],
        ["Suit alterations for the wedding.", "Fade booking after work.", "Nail repair before Friday.", "Pick up dry cleaning."],
        ["Est cost: $85", "$30 cut", "$55 gel set", "$18 pickup"],
        ["Needs 2 weeks for sleeve adjustments.", "Drop off suit tomorrow after work."],
    ),
    ContactCategory(
        "events_food",
        ["Catering", "Baker", "Photographer", "Florist", "Venue Manager", "Party Rental", "Reservations"],
        ["Bianca Catering", "Sweet Box Bakery", "Oak Hall Events", "Bloom Room"],
        ["Menu for office lunch.", "Cake order for birthday.", "Ask about chair rental.", "Photo shoot location list.", "Reservations for 5."],
        ["$15/person", "Deposit $75", "$300 package", "$100 initial visit"],
        ["Needs final headcount by Wed morning.", "Confirm delivery window.", "Send mood board by Fri."],
    ),
    ContactCategory(
        "retail_errands",
        ["Library Contact", "Bike Shop", "Phone Repair", "Print Shop", "Storage Office", "Appliance Repair"],
        ["Central Library", "Metro Bike Shop", "QuickFix Phones", "PrintWorks", "SafeBox Storage"],
        ["Library books due question.", "Repair cracked phone screen.", "Print flyers for fundraiser.", "Ask about storage unit gate code."],
        ["$90 screen", "$12 print job", "$65 tune-up", "Late fee maybe $5"],
        ["Call before noon.", "Bring receipt.", "Ask if they can finish by Sat."],
    ),
    ContactCategory(
        "personal_direct",
        ["Neighbor", "Coworker", "Mentor", "Classmate", "Club Organizer", "Volunteer Coordinator", "Election Volunteer"],
        ["Book Club", "Volunteer Desk", "Neighborhood Group", "Campus Club"],
        ["Can help with spare key.", "Ask about volunteer shift.", "Send notes from meeting.", "Coordinate carpool."],
        ["No cost", "Coffee owed", "$20 gas money", "Bring snacks"],
        ["Best to text after work.", "Follow up Friday."],
    ),
    ContactCategory(
        "real_estate_insurance",
        ["Real Estate Agent", "Claims Adjuster", "Inspector", "Mortgage Broker", "Title Company", "Insurance Agent"],
        ["Rowan Estate", "City Home Inspections", "Vance Real Estate", "Star Claims"],
        ["Regarding minor kitchen fire claim.", "House inspection on Thursday.", "Send tax docs over.", "Confirm escrow details."],
        ["$450 fee", "Premium went up", "Closing costs", "Appraisal $500"],
        ["Submit pics tonight.", "Waiting on final approval.", "Check the Docusign email."],
    ),
]


def _misspell(name: str) -> str:
    """Randomly introduce a typo into a name."""
    if random.random() > 0.15 or len(name) < 4:
        return name
    idx = random.randint(1, len(name) - 2)
    chars = list(name)
    chars[idx], chars[idx+1] = chars[idx+1], chars[idx]
    return "".join(chars)

def generate_contact_note(used_names: set[str] | None = None) -> dict:
    """Generate one synthetic contacts-mode note and metadata."""
    category = random.choice(CONTACT_CATEGORIES)
    if used_names is None:
        used_names = set()
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    full_name = f"{first} {last}" if random.random() < 0.65 else first
    for _ in range(50):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        full_name = f"{first} {last}" if random.random() < 0.65 else first
        if first.lower() not in used_names and full_name.lower() not in used_names:
            break
            
    full_name_typo = _misspell(full_name)
    role = random.choice(category.roles)
    org = random.choice(category.orgs)
    phone = _phone()
    email = _email(first, last, role)
    city = random.choice(CITIES)

    addr = _address(city)
    info_mode = random.choices(
        ["both", "phone", "email", "phone_addr", "all"], 
        weights=[5, 60, 0, 30, 5], 
        k=1
    )[0]
    def _randomize_dollars(s: str) -> str:
        def repl(m):
            amt = m.group(1)
            r = random.random()
            if r < 0.25: return amt
            elif r < 0.5: return f"{amt} bucks"
            elif r < 0.7: return f"{amt} dollars"
            return m.group(0)
        return re.sub(r"\$(\d+)", repl, s)

    detail = _randomize_dollars(random.choice(category.details))
    cost = _randomize_dollars(random.choice(category.costs))
    followup = random.choice(category.followups)
    
    layout = random.choices(["sentence", "fragmented", "dumping", "sparse"], weights=[30, 25, 25, 20], k=1)[0]
    
    def _get_info_str():
        if info_mode == "phone": return phone
        elif info_mode == "email": return email
        elif info_mode in ("both", "all"): return f"{phone} / {email}"
        return phone

    lines = []
    if layout == "sentence":
        verbs = ["Talked to", "txtd", "called", "Checked with", "hit up", "check with", "call", "Met"]
        verb = random.choice(verbs)
        from_loc = f"from {city}" if random.random() < 0.4 else ""
        intro = f"{verb} {full_name_typo} {role} {from_loc}"
        if random.random() < 0.5:
            intro += f" about {detail.lower()}"
        if random.random() < 0.5:
            intro += f" {_get_info_str()}"
            lines.append(intro.replace("..", ".").replace("  ", " ").strip())
            lines.append(cost)
            if info_mode in ("phone_addr", "all"):
                lines.append(addr)
            if random.random() < 0.5:
                lines.append(followup)
        else:
            lines.append(intro.replace("..", ".").replace("  ", " ").strip())
            if info_mode in ("email", "both", "all"):
                lines.append(email)
            if info_mode in ("phone", "both", "phone_addr", "all"):
                lines.append(phone)
            if info_mode in ("phone_addr", "all"):
                lines.append(addr)
            lines.append(detail)
            
    elif layout == "dumping":
        loc = f"in {city}" if random.random() < 0.4 else ""
        lines.append(f"{full_name_typo} - {detail.lower()} {loc}".replace("  ", " ").strip())
        if info_mode in ("email", "both", "all"):
            lines.append(email)
        if info_mode in ("phone", "both", "phone_addr", "all"):
            lines.append(phone)
        if info_mode in ("phone_addr", "all"):
            lines.append(addr)
        if random.random() < 0.4:
            lines.append(followup)
            
    elif layout == "fragmented":
        loc = f"{city}" if random.random() < 0.3 else ""
        info_str = phone if info_mode in ("phone", "phone_addr", "all", "both") else ""
        lines.append(f"{full_name_typo} {role} {loc} {info_str}".replace("  ", " ").strip())
        lines.append(detail)
        if info_mode in ("email", "both", "all"):
            lines.append(email)
        if info_mode in ("phone_addr", "all"):
            lines.append(addr)
        if random.random() < 0.5:
            lines.append(followup)
            
    else: # sparse
        lines.append(full_name_typo)
        if info_mode in ("email", "both", "all"):
            lines.append(email)
        if info_mode in ("phone", "both", "phone_addr", "all"):
            lines.append(phone)
        if info_mode in ("phone_addr", "all"):
            lines.append(addr)
        lines.append(role)
        lines.append(detail)

    if len(lines) > 2 and random.random() < 0.6:
        intro = lines[0]
        rest = lines[1:]
        random.shuffle(rest)
        lines = [intro] + rest

    note = "\n".join(_light_cleanup(line) for line in lines if line.strip())
    note = note.replace("..", ".").replace(" .", ".")

    return {
        "note": note,
        "contact_name": full_name,
        "contact_first_name": first,
        "category": category.id,
        "role": role,
        "topic_label": role,
    }


def validate_contact_note(note: str) -> ValidationResult:
    """Validate contacts-mode rules."""
    result = ValidationResult()
    lines = [line.strip() for line in note.splitlines() if line.strip()]
    note_lower = note.lower()
    words = note.split()

    result.add_check("line_count", len(lines) >= 1, f"Lines: {len(lines)} (need >= 1)")
    result.add_check("word_count", 4 <= len(words) <= 75, f"Word count: {len(words)} (need 4-75)")
    result.add_check("phone_or_email", bool(_PHONE_RE.search(note) or _EMAIL_RE.search(note)), "Has phone and/or email")
    result.add_check("excluded_geo", not _has_excluded_geo(note), "No TX/IL/WA terms or area codes")
    result.add_check("not_spam", not _looks_spammy(note_lower), "Not ad/spam copy")
    return result


_PHONE_RE = re.compile(r"(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})")
_EMAIL_RE = re.compile(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", re.I)


def _phone() -> str:
    area = random.choice(SAFE_AREA_CODES)
    mid = random.randint(200, 999)
    while mid == 555:
        mid = random.randint(200, 999)
    last = random.randint(1000, 9999)
    
    fmt = random.choices(["digits", "spaces", "parens", "dots", "hyphens"], weights=[30, 20, 20, 20, 10], k=1)[0]
    if fmt == "digits":
        return f"{area}{mid}{last}"
    elif fmt == "spaces":
        return f"{area} {mid} {last}"
    elif fmt == "parens":
        sep = " " if random.random() < 0.5 else ""
        return f"({area}) {mid}{sep}{last}"
    elif fmt == "dots":
        return f"{area}.{mid}.{last}"
    else:
        return f"{area}-{mid}-{last}"


def _email(first: str, last: str, role: str) -> str:
    token = re.sub(r"[^a-z]", "", role.lower().split()[0])[:14] or "contact"
    patterns = [
        f"{first.lower()}.{last.lower()}",
        f"{first[0].lower()}{last.lower()}",
        f"{first.lower()}.{token}",
        f"{first.lower()}{random.randint(2, 89)}",
    ]
    return f"{random.choice(patterns)}@{random.choice(EMAIL_DOMAINS)}"


def _address(city: str) -> str:
    streets = ["Main St", "Oak Ave", "Maple Lane", "Pine Road", "Cedar Blvd", "Elm St", "Washington St", "Park Ave", "Lincoln Blvd", "Cherry Ln"]
    num = random.randint(10, 9999)
    street = f"{num} {random.choice(streets)}"
    return f"{street}, {city}" if random.random() < 0.3 else street


def _availability_line() -> str:
    return random.choice([
        "Available Sat morning @ 10.",
        "Usually free on Wed evenings.",
        "Can come by Thursday after work.",
        "Call after 3 PM.",
        "Next opening is Fri afternoon.",
        "Text first, doesn't always pick up.",
    ])


def _reminder_line(category_id: str) -> str:
    by_category = {
        "health_dental": ["Remember to bring insurance card.", "Bring old paperwork and ID."],
        "school_college": ["Add this to school folder.", "Save for next parent meeting."],
        "pets": ["Send vaccine record before visit.", "Ask about weekend boarding."],
        "auto_transport": ["Leave keys in drop box.", "Ask for receipt after pickup."],
    }
    default = [
        "Need to confirm by Wed.",
        "Save number in case I need it later.",
        "Ask for final estimate before booking.",
        "Follow up tomorrow morning.",
    ]
    return random.choice(by_category.get(category_id, default))


def _light_cleanup(line: str) -> str:
    if line.endswith('.') and random.random() < 0.6:
        line = line[:-1]
        
    if line and (line[0].isalpha() and random.random() < 0.7):
        line = line[0].lower() + line[1:]
        
    for char in [",", "/", "\\"]:
        if random.random() < 0.4:
            line = line.replace(char, " ")
        
    if random.random() < 0.25:
        replacements = {
            "Tomorrow": random.choice(["tmrw", "tmmrw", "2moro"]),
            "tomorrow": random.choice(["tmrw", "tmmrw", "2moro"]),
            "Appointment": "Appt",
            "appointment": "appt",
            "Estimated": "Est",
            "estimate": "est",
            "Saturday": "Sat",
            "Wednesday": "Wed",
            "Thursday": "Thurs",
            "Friday": "Fri",
        }
        for old, new in replacements.items():
            line = line.replace(old, new)
    return line


def _has_specific_name(first_line: str) -> bool:
    if not first_line:
        return False
    first_token = re.split(r"[\s(-]", first_line.strip())[0]
    return first_token in FIRST_NAMES and not first_line.lower().startswith(("general ", "front desk", "main office"))


def _not_generic_business(lines: list[str]) -> bool:
    if not lines:
        return False
    first = lines[0].lower()
    generic_only = ["front desk", "main office", "general manager", "customer service", "reception"]
    return not any(term in first for term in generic_only)


def _has_excluded_geo(note: str) -> bool:
    lower = note.lower()
    if any(term in lower for term in EXCLUDED_TERMS):
        return True
    for match in _PHONE_RE.finditer(note):
        digits = re.sub(r"\D", "", match.group(0))
        if digits[:3] in EXCLUDED_AREA_CODES:
            return True
    return False


def _too_many_typos(note: str) -> bool:
    typoish = ["gonnabe", "tomorrowis", "withall", "nred", "stsrts", "cske"]
    return sum(note.lower().count(t) for t in typoish) > 0


def _looks_spammy(note_lower: str) -> bool:
    spam_terms = ["limited time", "buy now", "click here", "free!!!", "guaranteed results"]
    return any(term in note_lower for term in spam_terms)
