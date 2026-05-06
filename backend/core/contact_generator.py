"""Contacts generator — synthetic saved-contact notes (US and India modes)."""

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
    # Male
    "Marcus", "Leo", "Parker", "Logan", "Miles", "Derek", "Griffin", "Jordan",
    "Owen", "Tucker", "Noah", "Caleb", "Evan", "Wesley", "Andre", "Xavier",
    "Darius", "Malik", "Isaiah", "Santiago", "Diego", "Miguel", "Alejandro",
    "Hiroshi", "Kenji", "Arjun", "Vikram", "Liam", "Oliver", "Elijah", "James",
    "William", "Benjamin", "Lucas", "Henry", "Theodore", "Jack", "Levi",
    "Alexander", "Jackson", "Daniel", "Michael", "Mason", "Sebastian", "Ethan",
    "Samuel", "Jacob", "Asher", "Aiden", "John", "Joseph", "Wyatt", "David",
    "Luke", "Julian", "Hudson", "Grayson", "Matthew", "Ezra", "Gabriel",
    "Carter", "Isaac", "Jayden", "Luca", "Anthony", "Lincoln", "Thomas",
    "Maverick", "Elias", "Josiah", "Charles", "Christopher", "Ezekiel",
    "Jaxon", "Nathan", "Andrew", "Joshua", "Vincent", "Adrian",
    "Cameron", "Nolan", "Waylon", "Brooks", "Cooper", "Christian", "Hunter",
    "Khalil", "Jamal", "Terrence", "Marquis", "DeShawn", "Tyrone", "Dante",
    "Lamar", "Jalen", "Tariq", "Keon", "Omari", "Rashad", "Devonte",
    "Nasir", "Amari", "Zion", "King", "Ace", "Major", "Trevon", "Quincy",
    "Booker", "Donovan", "Jermaine", "Carlos", "Luis", "Andres", "Emilio",
    "Rafael", "Manuel", "Eduardo", "Javier", "Oscar", "Fernando", "Ricardo",
    "Antonio", "Sergio", "Pablo", "Cesar", "Hector", "Marco", "Rodrigo",
    "Enrique", "Arturo", "Ivan", "Ramon", "Julian", "Cristian", "Joaquin",
    "Cruz", "Esteban", "Gerardo", "Tomas", "Damian", "Pedro", "Felipe",
    "Wei", "Ravi", "Min", "Jun", "Hao", "Daichi", "Yuki", "Sanjay",
    "Raj", "Dev", "Nikhil", "Aarav", "Rohan", "Akira", "Tao", "Jin",
    "Cormac", "Stellan", "Henrik", "Alistair", "Bastian", "Leif", "Alden",
    "Idris", "Talon", "Crispin", "Theron", "Warrick", "Broderick", "Caspian",
    "Gareth", "Hadley", "Ingram", "Lowell", "Merrick", "Niall", "Pierce",
    "Quinlan", "Vance", "Weldon", "Yates", "Zeb", "Gage", "Otto", "Holt",
    "Calder", "Sterling", "Dex", "Fen", "Soren", "Bodie", "Beckett", "Crew",
    "Kaiden", "Jameson", "Tate", "Holden", "Knox", "Atticus", "Sullivan",
    "Walker", "Greyson", "Shepherd", "Archer", "Bowen", "Jasper", "Ridge",
    "Otis", "Forrest", "Grant", "Emmett", "Bryson", "Ryder", "Brandon",
    "Blake", "Kevin", "Tyler", "Aaron", "Max", "Tristan", "Jonah", "Dean",
    "Kyle", "Cole", "Axel", "Finn", "Jace", "Reid", "Brody", "Beau",
    "Patrick", "Chase", "Sawyer", "Braxton", "Gavin", "Leonardo", "Roman",
    "Jason", "Colton", "Landon", "Dominic", "Eli", "Carson", "Declan",
    "Easton", "Zachary", "Kai", "Bentley", "Emrys", "Lysander", "Rafferty",
    # Female
    "Sarah", "Nina", "Bella", "Bianca", "Fiona", "Avery", "Camila",
    "Maya", "Sofia", "Eboni", "Jasmine", "Mila", "Naomi", "Kara",
    "Aaliyah", "Reese", "Lucia", "Amara", "Imani", "Zuri", "Valentina",
    "Priya", "Ananya", "Mei", "Olivia", "Emma", "Charlotte", "Amelia",
    "Sophia", "Mia", "Isabella", "Ava", "Evelyn", "Luna", "Harper",
    "Scarlett", "Elizabeth", "Eleanor", "Emily", "Chloe", "Violet",
    "Penelope", "Gianna", "Aria", "Abigail", "Audrey", "Alice", "Hazel",
    "Grace", "Nora", "Lily", "Layla", "Zoe", "Deja", "Aniya", "Aliyah",
    "Janiyah", "Skyla", "Armani", "Kaia", "Zariah", "Brielle", "Kamila",
    "Laila", "Nalani", "Sariah", "Amira", "Kennedi", "Skai", "Tatum",
    "Zhuri", "Kailani", "Milan", "Lyric", "Kaliyah", "Journee", "Trinity",
    "Janelle", "Saniyah", "Talia", "Sofia", "Isabella", "Camila", "Mariana",
    "Daniela", "Natalia", "Alejandra", "Victoria", "Ximena", "Ana", "Maria",
    "Carolina", "Adriana", "Juliana", "Catalina", "Fernanda", "Paloma",
    "Marisol", "Esperanza", "Carmen", "Rosa", "Selena", "Alondra", "Dulce",
    "Esmeralda", "Yesenia", "Renata", "Soledad", "Lola", "Beatriz", "Itzel",
    "Mireya", "Liliana", "Magdalena", "Yolanda", "Pilar", "Estrella", "Lupita",
    "Sakura", "Aiko", "Yuna", "Hana", "Suki", "Lin", "Jade", "Jasmine",
    "Mina", "Anh", "Mai", "Thi", "Rina", "Sora", "Nari", "Meera", "Shreya",
    "Divya", "Kavya", "Deepa", "Priti", "Nadia", "Simone", "Celeste",
    "Daphne", "Ingrid", "Margot", "Vivienne", "Petra", "Delia", "Betsy",
    "Greta", "Roslyn", "Willa", "Thea", "Imelda", "Odessa", "Yara", "Zola",
    "Nyla", "Camille", "Odette", "Blythe", "Lena", "Miriam", "Callista",
    "Becca", "Shira", "Tove", "Sable", "Alana", "Daria", "Coral", "Sylvie",
    "Linnea", "Maren", "Veda", "Astrid", "Fern", "Tamsin", "Bridget",
    "Colleen", "Shannon", "Kathleen", "Moira", "Siobhan", "Deirdre",
    # Neutral / unisex
    "Kai", "River", "Phoenix", "Avery", "Riley", "Jordan", "Morgan",
    "Reese", "Finley", "Emery", "Rowan", "Hayden", "Blake", "Charlie",
    "Drew", "Jamie", "Taylor", "Alex", "Ari", "Ellis", "Remy", "Sol",
    "Wren", "Dakota", "Eden", "Harper", "Lane", "Rory", "Sky", "Cameron",
    "Casey", "Quinn", "Sage", "Lennox", "Indie", "Soren", "Briar", "Ace",
    "Lex", "Bodhi", "Orion", "Nico", "Jude", "Atlas", "Kingston", "Maddox",
    "Theo", "Cyrus", "Cassian", "Onyx", "Ronan",
]
LAST_NAMES = [
    "Miller", "Brooks", "Sterling", "Mendez", "Vance", "Carter", "Hayes",
    "Rivera", "Morgan", "Patel", "Bennett", "Coleman", "Price", "Ross",
    "Reed", "Foster", "Diaz", "Hughes", "Murphy", "Sullivan", "Bailey",
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Rodriguez",
    "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
    "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Campbell", "Mitchell",
    "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Parker", "Cruz",
    "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Cook",
    "Rogers", "Gutierrez", "Ortiz", "Cooper", "Peterson",
    "Bryant", "Russell", "Griffin", "Diaz", "Hayes", "Myers", "Ford",
    "Hamilton", "Graham", "Sullivan", "Wallace", "Woods", "Cole", "West",
    "Jordan", "Owens", "Reynolds", "Fisher", "Ellis", "Harrison", "Gibson",
    "McDonald", "Cruz", "Marshall", "Ortega", "Ramos", "Guerrero", "Munoz",
    "Medina", "Vargas", "Castillo", "Romero", "Chavez", "Aguilar", "Salazar",
    "Huang", "Chen", "Pham", "Tran", "Nguyen", "Kim", "Park", "Choi",
    "Singh", "Kumar", "Sharma", "Gupta", "Kapoor", "Mehta", "Shah", "Bose",
    "Thornton", "Blackwood", "Weston", "Harmon", "Dalton", "Frost", "Keller",
    "Garrett", "Barton", "Haynes", "Knox", "Malone", "Randall", "Stanton",
    "Whitfield", "Holloway", "Barker", "Byrd", "Chandler", "Eaton", "Holt",
]
CITIES = [
    "Portland", "Phoenix", "Boston", "Charlotte", "Nashville", "Sacramento",
    "Denver", "Miami", "Atlanta", "New York", "Las Vegas", "Philadelphia",
    "Orlando", "Detroit", "Tampa", "San Jose", "San Diego", "Raleigh",
    "Omaha", "Memphis", "Louisville", "Baltimore", "Columbus", "Indianapolis",
    "Jacksonville", "San Francisco", "Salt Lake City", "Kansas City",
    "Milwaukee", "Minneapolis", "St. Louis", "Boise", "Albuquerque",
    "Tucson", "Colorado Springs", "Fresno", "Long Beach", "Sacramento",
    "Virginia Beach", "Richmond", "Norfolk", "Durham", "Winston-Salem",
    "Greensboro", "Fayetteville", "Aurora", "Lakewood", "Arvada",
    "Fort Collins", "Pueblo", "Honolulu", "Anchorage", "Juneau",
    "Baton Rouge", "New Orleans", "Shreveport", "Birmingham", "Montgomery",
    "Huntsville", "Mobile", "Little Rock", "Fayetteville", "Knoxville",
    "Chattanooga", "Clarksville", "Murfreesboro", "Columbia", "Greenville",
    "Charleston", "Savannah", "Augusta", "Athens", "Macon",
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
    ContactCategory(
        "corporate_office",
        ["IT Support", "HR Rep", "Office Manager", "Facilities Manager", "Admin Assistant", "Payroll Contact", "Building Security", "Department Head", "Procurement"],
        ["Corporate HQ", "Regional Office", "Downtown Branch", "Tech Campus", "Main Office", "North Tower"],
        ["Follow up on laptop ticket.", "HR form needs signature.", "Office supply order.", "Badge access request.", "Facilities request for AC.", "Payroll discrepancy to fix."],
        ["No fee", "Reimbursement pending", "Company card", "Expense report"],
        ["Submit ticket before EOD.", "CC manager on the email.", "Ask for confirmation number.", "Check internal portal first."],
    ),
    ContactCategory(
        "freelance_creative",
        ["Graphic Designer", "Web Developer", "Photographer", "Videographer", "Copywriter", "Social Media Manager", "UI Designer", "Brand Consultant", "Illustrator"],
        ["Freelance Studio", "Creative Co.", "Independent", "Design Lab", "Boutique Studio", "Pixel & Ink"],
        ["Logo revision round 2.", "Website launch checklist.", "Photo shoot deliverables.", "Video edit feedback needed.", "Content calendar draft.", "Brand guide final version."],
        ["Quote: $400", "Invoice $850", "Deposit $200", "Rate $75/hr", "Package $1200"],
        ["Send brief by Tuesday.", "Need source files too.", "Ask about turnaround time.", "Confirm file format before delivery."],
    ),
    ContactCategory(
        "financial_legal",
        ["Financial Advisor", "Accountant", "Tax Preparer", "Attorney", "Paralegal", "Banker", "Loan Officer", "Insurance Agent", "Estate Planner", "Notary"],
        ["Financial Group", "Law Offices", "CPA Associates", "Wealth Management", "Insurance Agency", "First National Bank"],
        ["Tax filing extension requested.", "Will and trust update.", "Loan refinance paperwork.", "IRA contribution question.", "Business license renewal.", "Contract review needed."],
        ["Consult fee $150", "Filing fee $200", "No charge first meeting", "Retainer $500", "Processing fee $75"],
        ["Bring last 2 years returns.", "Need notarized copy.", "Ask about payment plan.", "Confirm appointment is in-person.", "Send scanned docs beforehand."],
    ),
]


def _misspell(name: str) -> str:
    """Randomly introduce a typo into a name with more variety."""
    if random.random() > 0.18 or len(name) < 4:
        return name
    
    idx = random.randint(1, len(name) - 1)
    chars = list(name)
    r = random.random()
    
    if r < 0.4: # Swap
        if idx < len(chars) - 1:
            chars[idx], chars[idx+1] = chars[idx+1], chars[idx]
    elif r < 0.7: # Omission
        chars.pop(idx)
    elif r < 0.9: # Duplication
        chars.insert(idx, chars[idx])
    else: # Wrong key (nearby char)
        chars[idx] = random.choice("abcdefghijklmnopqrstuvwxyz")
        
    return "".join(chars)

# ── India-specific data ───────────────────────────────────────────────────────

INDIA_CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Pune", "Kolkata",
    "Jaipur", "Ahmedabad", "Surat", "Lucknow", "Kanpur", "Nagpur", "Indore",
    "Bhopal", "Patna", "Vadodara", "Coimbatore", "Agra", "Nashik", "Ranchi",
    "Faridabad", "Meerut", "Rajkot", "Varanasi", "Ghaziabad", "Noida",
    "Gurugram", "Chandigarh", "Mysore", "Bhubaneswar", "Visakhapatnam",
    "Ludhiana", "Amritsar", "Jodhpur", "Raipur", "Kochi", "Thiruvananthapuram",
    "Guwahati", "Dehradun", "Jalandhar", "Aurangabad", "Solapur", "Hubli",
]

INDIA_FIRST_NAMES = [
    "Amit", "Rahul", "Vikram", "Suresh", "Rajesh", "Manoj", "Arun", "Sanjay",
    "Deepak", "Pankaj", "Rohit", "Vivek", "Nikhil", "Karan", "Arjun", "Dev",
    "Ankit", "Pradeep", "Ravi", "Mohit", "Ajay", "Vijay", "Gaurav", "Sachin",
    "Ramesh", "Dinesh", "Harish", "Girish", "Manish", "Naresh", "Rakesh",
    "Ashok", "Sunil", "Anil", "Kapil", "Tarun", "Varun", "Vishal", "Kartik",
    "Akash", "Shubham", "Abhishek", "Himanshu", "Tushar", "Nitin", "Rohan",
    "Karthik", "Suresh", "Venkat", "Bala", "Ravi", "Mani", "Prasad", "Subramaniam",
    "Arnab", "Souvik", "Debashish", "Bikash", "Subho", "Arka", "Soumit",
    "Priya", "Anjali", "Neha", "Pooja", "Kavita", "Sunita", "Rekha", "Meena",
    "Geeta", "Sita", "Anita", "Sarita", "Savita", "Vandana", "Archana",
    "Deepa", "Divya", "Priyanka", "Swati", "Shweta", "Ritu", "Nisha", "Preeti",
    "Ananya", "Shreya", "Pallavi", "Madhuri", "Sneha", "Sonali", "Manisha",
    "Komal", "Roshni", "Meenal", "Diksha", "Kiran", "Seema", "Sunita",
    "Lakshmi", "Radha", "Meera", "Sridevi", "Geetha", "Revathi", "Kavya",
    "Harpreet", "Gurpreet", "Manpreet", "Jaspreet", "Simran", "Navneet",
]

INDIA_LAST_NAMES = [
    "Sharma", "Gupta", "Singh", "Verma", "Yadav", "Tiwari", "Dubey", "Mishra",
    "Pandey", "Joshi", "Patel", "Shah", "Mehta", "Desai", "Gandhi", "Modi",
    "Kumar", "Nair", "Pillai", "Menon", "Iyer", "Iyengar", "Reddy", "Naidu",
    "Chatterjee", "Banerjee", "Mukherjee", "Ghosh", "Das", "Roy", "Sen", "Bose",
    "Kaur", "Dhillon", "Sandhu", "Gill", "Bhatia", "Arora", "Khanna", "Kapoor",
    "Saxena", "Srivastava", "Shukla", "Tripathi", "Chaudhary", "Aggarwal",
]

INDIA_CONTACT_CATEGORIES = [
    ContactCategory(
        "home_services",
        ["Plumber", "Electrician", "Carpenter", "Painter", "AC Repair", "Pest Control", "Waterproofing", "Sofa Repair"],
        ["Sri Ram Plumbers", "City Electricals", "Sharma Carpentry", "CoolAir AC Services", "CleanHome Pest Control"],
        ["Fix kitchen pipe leak.", "Wiring check for inverter.", "Paint bedroom walls.", "AC gas refill needed.", "Termite treatment quote."],
        ["Est: ₹500", "Quote: ₹1200", "₹800 including material", "₹300 visit charge"],
        ["Can come Sunday morning.", "Ask about weekend slot.", "Needs photos before quote."],
    ),
    ContactCategory(
        "auto_transport",
        ["Mechanic", "Tyre Shop", "Auto Electrician", "Car Wash", "Driving Instructor", "Two-Wheeler Repair"],
        ["Ram Motors", "City Tyre House", "Bajaj Auto Works", "Shine Car Wash", "Raj Driving School"],
        ["Engine oil change due.", "Front tyre puncture fix.", "Battery replacement.", "Full car wash booking.", "Learn gear car driving."],
        ["Est: ₹400", "₹150 per tyre", "₹600 battery", "₹250 full wash", "₹1500 per month"],
        ["Drop bike Thursday morning.", "Ask if they take UPI.", "Check Google reviews first."],
    ),
    ContactCategory(
        "health_medical",
        ["Doctor", "Compounder", "Pharmacist", "Pathology Lab", "Physiotherapist", "Eye Doctor", "Dentist"],
        ["Dr. Sharma Clinic", "City Pathology", "MediCare Pharmacy", "Vision Eye Centre", "SmileCare Dental"],
        ["Blood test report followup.", "Eye checkup appointment.", "Refill BP medicines.", "Knee pain physio session.", "Tooth cleaning due."],
        ["Fees: ₹300", "Lab: ₹800", "Copay ₹100", "₹500 session", "OPD ₹200"],
        ["Bring Aadhaar card.", "Fast for 8 hrs before blood test.", "Confirm morning slot."],
    ),
    ContactCategory(
        "education",
        ["Tuition Teacher", "Coaching Sir", "College Professor", "School Teacher", "Music Teacher", "Computer Trainer"],
        ["Sharma Coaching Centre", "City IIT Classes", "Excel Tuitions", "Digital Skills Academy"],
        ["Math doubt session.", "NEET preparation schedule.", "Python course demo class.", "Board exam revision plan.", "Music class fees pending."],
        ["₹2000/month", "₹500/session", "₹1500 batch fee", "First class free"],
        ["Bring notebook and pen.", "Ask about weekend batch.", "Confirm timing before coming."],
    ),
    ContactCategory(
        "finance_legal",
        ["CA", "Tax Consultant", "LIC Agent", "Bank Manager", "Lawyer", "Loan Officer", "Mutual Fund Agent"],
        ["Gupta & Associates CA", "LIC Office", "SBI Branch", "City Law Chambers", "Finwise Investments"],
        ["ITR filing deadline.", "LIC premium due.", "Home loan documents.", "FD renewal query.", "Will preparation."],
        ["CA fees ₹3000", "Premium ₹12000", "Processing ₹1500", "No charge consultation"],
        ["Bring PAN and Aadhaar.", "Submit Form 16.", "Ask about GST registration."],
    ),
    ContactCategory(
        "kirana_grocery",
        ["Kirana Store", "Vegetable Vendor", "Milk Supplier", "Grocery Delivery", "Wholesale Dealer"],
        ["Sharma General Store", "Ramu Kirana", "Fresh Veg Corner", "Daily Dairy"],
        ["Monthly grocery order.", "Atta and dal stock over.", "Milk packets from tomorrow.", "Wholesale rate for pulses.", "Pending bill payment."],
        ["₹2500 monthly", "₹150 pending", "Cash on delivery", "UPI accepted"],
        ["Call before 8 AM.", "Ask about home delivery.", "Check expiry before buying."],
    ),
    ContactCategory(
        "salon_parlour",
        ["Barber", "Hair Stylist", "Parlour", "Mehendi Artist", "Tailor", "Dry Cleaner"],
        ["Raju Hair Salon", "Lakme Studio", "Pooja Beauty Parlour", "Shahi Tailors", "Quick Dry Cleaners"],
        ["Haircut appointment.", "Bridal mehendi booking.", "Suit stitching order.", "Saree dry clean pickup.", "Facial and cleanup."],
        ["₹100 haircut", "₹800 mehendi", "₹1200 stitching", "₹200 dry clean"],
        ["Needs 10 days for stitching.", "Book 2 weeks before event.", "Ask for advance booking discount."],
    ),
    ContactCategory(
        "events_catering",
        ["Caterer", "Decorator", "Pandit", "Photographer", "Tent House", "DJ"],
        ["Shree Caterers", "Royal Decorators", "City Photography", "Om Events", "Sharma Tent House"],
        ["Wedding catering menu.", "Birthday decoration booking.", "Pooja samagri list.", "Photo album delivery.", "Canopy rental for function."],
        ["₹400 per plate", "Advance ₹5000", "Package ₹15000", "₹8000 day"],
        ["Confirm headcount 3 days before.", "Ask for veg/non-veg rates.", "Get written estimate."],
    ),
    ContactCategory(
        "personal_direct",
        ["Neighbour", "Colony Secretary", "Building Watchman", "Society Member", "Mohalla Contact", "Volunteer"],
        ["Society Office", "RWA", "Colony Group", "Building Committee"],
        ["Society maintenance dues.", "Water supply complaint.", "Parking dispute.", "Gate pass for visitor.", "Noise complaint followup."],
        ["₹2000 maintenance", "No cost", "Fine ₹500 maybe", "Cash only"],
        ["Speak to secretary directly.", "Call after 6 PM.", "WhatsApp message first."],
    ),
    ContactCategory(
        "repair_services",
        ["Mobile Repair", "Laptop Repair", "TV Repair", "Washing Machine Repair", "Fridge Repair", "DTH Technician"],
        ["QuickFix Mobile", "TechCare Laptops", "City Electronics Repair", "HomeAppliance Service"],
        ["Phone screen crack fix.", "Laptop battery replacement.", "TV remote not working.", "Washing machine draining issue.", "Fridge cooling problem."],
        ["₹500 screen", "₹800 battery", "₹350 visit charge", "₹1200 estimate"],
        ["Ask for 3-month warranty.", "Get bill after repair.", "Check reviews on Google."],
    ),
]


def _india_phone() -> str:
    """Generate realistic Indian mobile number."""
    first_digit = random.choice(["6", "7", "8", "9"])
    remaining = "".join([str(random.randint(0, 9)) for _ in range(9)])
    number = first_digit + remaining
    fmt = random.choices(["plain", "space5", "hyphen5", "plus91"], weights=[30, 30, 25, 15], k=1)[0]
    if fmt == "plain":
        return number
    elif fmt == "space5":
        return f"{number[:5]} {number[5:]}"
    elif fmt == "hyphen5":
        return f"{number[:5]}-{number[5:]}"
    else:
        return f"+91 {number[:5]} {number[5:]}"


def _india_address(city: str) -> str:
    """Generate realistic Indian address."""
    colonies = [
        "Shanti Nagar", "Gandhi Colony", "Civil Lines", "Nehru Nagar", "Sector 12",
        "Rajiv Nagar", "Lal Bahadur Colony", "New Colony", "Model Town", "Green Park",
        "Adarsh Nagar", "Indira Nagar", "Vikas Nagar", "Vasant Vihar", "Saket",
        "Karol Bagh", "Malviya Nagar", "Tilak Nagar", "Defence Colony", "Janakpuri",
    ]
    house_formats = [
        f"H.No {random.randint(1, 999)}",
        f"Flat {random.randint(1, 12)}{random.choice(['A','B','C','D'])}",
        f"Plot {random.randint(1, 500)}",
        f"D-{random.randint(1, 200)}",
    ]
    house = random.choice(house_formats)
    colony = random.choice(colonies)
    if random.random() < 0.4:
        return f"{house}, {colony}, {city}"
    return f"{house}, {colony}"


def generate_contact_note(used_names: set[str] | None = None, used_first_counts: dict | None = None, language: str = "english") -> dict:
    """Generate one synthetic contacts-mode note and metadata."""
    india = language == "hindi"
    category = random.choice(INDIA_CONTACT_CATEGORIES if india else CONTACT_CATEGORIES)
    if used_names is None:
        used_names = set()
    if used_first_counts is None:
        used_first_counts = {}

    name_pool_first = INDIA_FIRST_NAMES if india else FIRST_NAMES
    name_pool_last = INDIA_LAST_NAMES if india else LAST_NAMES

    first = random.choice(name_pool_first)
    last = random.choice(name_pool_last)
    full_name = f"{first} {last}" if random.random() < 0.65 else first
    for _ in range(80):
        first = random.choice(name_pool_first)
        last = random.choice(name_pool_last)
        full_name = f"{first} {last}" if random.random() < 0.65 else first
        if used_first_counts.get(first.lower(), 0) < 2 and full_name.lower() not in used_names:
            break

    full_name_typo = _misspell(full_name)
    role = random.choice(category.roles)
    phone = _india_phone() if india else _phone()
    email = _email(first, last, role)
    city = random.choice(INDIA_CITIES if india else CITIES)

    addr = _india_address(city) if india else _address(city)
    info_mode = random.choices(
        ["both", "phone", "email", "phone_addr", "all"],
        weights=[5, 60, 0, 30, 5],
        k=1
    )[0]

    def _randomize_dollars(s: str) -> str:
        if india:
            # Real people rarely write ₹ symbol — usually just the number or "Rs."
            def repl_inr(m):
                amt = m.group(1)
                r = random.random()
                if r < 0.55: return amt          # just "500" — most common
                elif r < 0.85: return f"Rs. {amt}"  # "Rs. 500" — occasional
                return m.group(0)                # "₹500" — rare (~15%)
            return re.sub(r"₹(\d+)", repl_inr, s)
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
        verbs = [
            "Talked to", "txtd", "called", "Checked with", "hit up", "check with", "call", "Met",
            "Follow up w/", "Need to talk to", "Ask", "Reminder:", "Contact:", "Reached out to",
            "Schedule w/", "Connect with", "Invoiced", "Paid", "Sent info to", "Got a quote from",
            "Messaged", "Waiting on", "Pick up from", "Drop off at", "Discussed", "Meeting with"
        ]
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
