import os
import difflib

# Define the exact mapping from the original generator config to the final 15 categories
CATEGORY_MAPPING = {
    # School & College life
    "lab equipment scheduling and calibration": "School & College life",
    "thesis defense logistics and presentation structure": "School & College life",
    "study group syllabus breakdown for midterm": "School & College life",
    "library archives access request process": "School & College life",
    "grading rubric for final engineering project": "School & College life",
    "campus wifi mesh network upgrade details": "School & College life",
    "biochemistry lecture notes on enzyme kinetics": "School & College life",
    "linear algebra matrix multiplication review": "School & College life",
    "student housing maintenance request logs": "School & College life",
    "grant proposal submission timeline": "School & College life",
    "intramural sports bracket scheduling": "School & College life",
    "academic advising degree path requirements": "School & College life",
    "chemistry titration lab safety procedures": "School & College life",
    "architecture studio model building materials": "School & College life",
    "linguistics phonetics chart memorization": "School & College life",
    
    # Work-life balance
    "quarterly OKR tracking spreadsheet setup": "Work-life balance",
    "agile sprint retrospective action items": "Work-life balance",
    "vendor procurement steps and RFP process": "Work-life balance",
    "HR benefits enrollment deadline notes": "Work-life balance",
    "B2B sales funnel conversion metrics": "Work-life balance",
    "warehouse inventory audit discrepancies": "Work-life balance",
    "server migration downtime window planning": "Work-life balance",
    "remote work VPN troubleshooting steps": "Work-life balance",
    "new hire onboarding checklist completion": "Work-life balance",
    "marketing budget allocation breakdown": "Work-life balance",
    "SOC2 compliance documentation review": "Work-life balance",
    "daily standup blockers and dependencies": "Work-life balance",
    "payroll processing holiday schedule": "Work-life balance",
    "UX design wireframe feedback loop": "Work-life balance",
    "client retention strategy session notes": "Work-life balance",
    
    # Movies / TV Shows (mapped from entertainment_movies_tv)
    "three-point lighting setups for interviews": "Movies",
    "foley sound recording techniques": "Movies",
    "screenwriting heros journey structure": "Movies",
    "non-linear video editing proxy workflow": "Movies",
    "anamorphic lens flare characteristics": "Movies",
    "color grading LUT adjustments in DaVinci": "Movies",
    "boom mic placement for dialogue scenes": "TV Shows",
    "steadycam vest balancing parameters": "TV Shows",
    "practical special effects rigging": "Movies",
    "aspect ratio framing techniques": "Movies",
    "green screen chroma keying thresholds": "TV Shows",
    "script continuity breakdown sheets": "Movies",
    "focal length depth of field calculations": "Movies",
    "storyboard panel shot lists": "Movies",
    "frame rate conversion artifacts": "TV Shows",

    # Music
    "mix EQ frequencies for bass guitar": "Music",
    "circle of fifths chord progressions": "Music",
    "MIDI quantization and swing settings": "Music",
    "analog synthesizer oscillator tuning": "Music",
    "drum kit mic placement techniques": "Music",
    "vocal compression knee and ratio settings": "Music",
    "mastering LUFS loudness targets": "Music",
    "acoustic guitar restringing gauge tension": "Music",
    "sidechain routing for kick and bass": "Music",
    "reverb tail pre-delay calculations": "Music",
    "polyrhythm timing signatures": "Music",
    "audio interface sample rate latency": "Music",
    "subtractive synthesis envelope ADSR": "Music",
    "condenser mic phantom power requirements": "Music",
    "live sound feedback loop suppression": "Music",

    # Gaming
    "pathfinding algorithm optimization": "Gaming",
    "sprite sheet resolution and atlas packing": "Gaming",
    "level design choke point analysis": "Gaming",
    "frame pacing and vsync tearing": "Gaming",
    "procedural generation seed values": "Gaming",
    "hit-box collision detection layers": "Gaming",
    "shader compilation stutter fixes": "Gaming",
    "character rigging inverse kinematics": "Gaming",
    "dialogue tree branching logic": "Gaming",
    "netcode rollback implementation": "Gaming",
    "inventory management data structures": "Gaming",
    "GPU particle system limits": "Gaming",
    "save state serialization formats": "Gaming",
    "UI layout anchoring and scaling": "Gaming",
    "controller deadzone analog stick tuning": "Gaming",

    # Food
    "dough hydration percentage calculations": "Food",
    "Maillard reaction temperature thresholds": "Food",
    "sous vide timing logs for steak": "Food",
    "sourdough starter feeding ratios": "Food",
    "emulsion stability for vinaigrettes": "Food",
    "tempering chocolate crystal structures": "Food",
    "coffee espresso extraction pressure": "Food",
    "fermentation pH levels for kimchi": "Food",
    "salt curing ratios for preservation": "Food",
    "pastry lamination butter temperatures": "Food",
    "deep frying smoke point comparisons": "Food",
    "gelatin blooming liquid measurements": "Food",
    "pressure cooking altitude adjustments": "Food",
    "dry aging humidity control parameters": "Food",
    "cheese rennet coagulation times": "Food",

    # Traditions / Celebrations
    "cultural ceremonial sequence planning": "Traditions",
    "historical origins of harvest festivals": "Traditions",
    "venue layout for ritual seating": "Celebrations",
    "traditional garment fabric sourcing": "Traditions",
    "astrological calendar date selection": "Traditions",
    "symbolic meaning of altar offerings": "Traditions",
    "procession route permit logistics": "Celebrations",
    "acoustic requirements for chanting": "Traditions",
    "ancestral lineage recitation order": "Traditions",
    "generational recipe preservation methods": "Traditions",
    "floral arrangement symbolism": "Celebrations",
    "ceremonial fire safety clearances": "Celebrations",
    "traditional dance choreography notation": "Traditions",
    "seasonal transition folklore study": "Traditions",
    "feast table setting protocols": "Celebrations",

    # Hobbies
    "woodworking dovetail joint types": "Hobbies",
    "DSLR aperture and shutter speed combinations": "Hobbies",
    "pottery kiln firing temperature schedules": "Hobbies",
    "model train scale track gauges": "Hobbies",
    "crochet yarn weight and hook sizes": "Hobbies",
    "aquarium nitrogen cycle water testing": "Hobbies",
    "stamp collecting condition grading": "Hobbies",
    "board game meeple storage dimensions": "Hobbies",
    "oil painting medium drying times": "Hobbies",
    "amateur radio antenna length tuning": "Hobbies",
    "indoor hydroponic nutrient mixing": "Hobbies",
    "fountain pen nib grinding angles": "Hobbies",
    "leatherworking saddle stitch technique": "Hobbies",
    "telescope equatorial mount alignment": "Hobbies",
    "origami crease pattern logic": "Hobbies",

    # Outdoor Adventure
    "mountaineering knot tying figure eight": "Outdoor Adventure",
    "kayak route topographic map reading": "Outdoor Adventure",
    "tent waterproofing silnylon layers": "Outdoor Adventure",
    "climbing carabiner kN strength ratings": "Outdoor Adventure",
    "backpacking base weight minimization": "Outdoor Adventure",
    "avalanche beacon grid search protocols": "Outdoor Adventure",
    "mountain bike tire PSI terrain adjustments": "Outdoor Adventure",
    "water purification filter micron sizes": "Outdoor Adventure",
    "high altitude acclimatization schedules": "Outdoor Adventure",
    "backcountry ski skin glue maintenance": "Outdoor Adventure",
    "compass magnetic declination calculation": "Outdoor Adventure",
    "hammock suspension tree strap angles": "Outdoor Adventure",
    "survival fire starting friction methods": "Outdoor Adventure",
    "rappelling descender friction control": "Outdoor Adventure",
    "trail grading elevation gain analysis": "Outdoor Adventure",

    # Weather
    "barometric pressure drop correlations": "Weather",
    "Doppler radar velocity color scales": "Weather",
    "cumulonimbus cloud formation rates": "Weather",
    "El Nino sea surface temperature anomalies": "Weather",
    "dew point spread and fog likelihood": "Weather",
    "jet stream upper level trough tracking": "Weather",
    "hurricane category wind speed thresholds": "Weather",
    "atmospheric inversion layer trapping": "Weather",
    "tornado CAPE instability indexes": "Weather",
    "relative humidity psychrometer readings": "Weather",
    "microburst downdraft velocities": "Weather",
    "cold front boundary collision dynamics": "Weather",
    "snowfall ratio temperature dependency": "Weather",
    "isobar map pressure gradient force": "Weather",
    "UV index solar radiation peaks": "Weather",

    # Travel/Transportation
    "Rome historical walking tour itineraries": "Travel/Transportation",
    "Kyoto temple preservation architectural details": "Travel/Transportation",
    "local transit map routing efficiency": "Travel/Transportation",
    "museum exhibit chronological sequencing": "Travel/Transportation",
    "national park trail elevation profiles": "Travel/Transportation",
    "historical monument limestone erosion": "Travel/Transportation",
    "subway rail gauge differences": "Travel/Transportation",
    "ancient ruin excavation grid mapping": "Travel/Transportation",
    "regional cuisine historical ingredient trade": "Travel/Transportation",
    "coastal tide pool exploration schedules": "Travel/Transportation",
    "mountain pass seasonal road closures": "Travel/Transportation",
    "cathedral stained glass restoration dates": "Travel/Transportation",
    "ferry crossing nautical mile times": "Travel/Transportation",
    "indigenous cultural site access rules": "Travel/Transportation",
    "high speed rail magnetic levitation specs": "Travel/Transportation",

    # Automotive
    "V8 engine torque spec calculations": "Automotive",
    "ceramic coating curing time logs": "Automotive",
    "tire pressure monitoring systems TPMS": "Automotive",
    "synthetic oil viscosity temperature ranges": "Automotive",
    "disc brake rotor heat dissipation": "Automotive",
    "transmission gear ratio calculations": "Automotive",
    "ECU remap air fuel mixture tuning": "Automotive",
    "suspension strut rebound damping": "Automotive",
    "aerodynamic drag coefficient testing": "Automotive",
    "battery alternator voltage output": "Automotive",
    "exhaust manifold backpressure flow": "Automotive",
    "spark plug gap firing efficiency": "Automotive",
    "catalytic converter precious metal loads": "Automotive",
    "differential limited slip mechanisms": "Automotive",
    "chassis torsional rigidity measurements": "Automotive"
}

txt_dir = "/home/kamleshpatil/Desktop/Notes - PR and ontata/notes_app/output/Final_300_TOI_English/txt"
out_file = "/home/kamleshpatil/Desktop/Notes - PR and ontata/notes_app/output/Final_300_TOI_English/copy_paste_categories.txt"

files = sorted([f for f in os.listdir(txt_dir) if f.endswith(".txt")])

final_categories = []
for f in files:
    with open(os.path.join(txt_dir, f), 'r') as file:
        title = file.readline().strip().lower()
        
    best_match = None
    best_score = 0
    
    for key, category in CATEGORY_MAPPING.items():
        score = difflib.SequenceMatcher(None, title, key.lower()).ratio()
        if score > best_score:
            best_score = score
            best_match = category
            
    # Hardcoded overrides for items we know the LLM sometimes shortens or rephrases
    if "dslr aperture" in title or "dsp apert" in title:
        best_match = "Hobbies"
    if "marketing budget" in title or "sales funnel" in title or "procurement" in title:
        # Move these from Work-life to Finance based on client preference
        best_match = "Finance"
    
    if not best_match:
        best_match = "Other"
        
    final_categories.append(best_match)

# Write to file
with open(out_file, "w") as f:
    for cat in final_categories:
        f.write(cat + "\n")

print(f"Generated {len(final_categories)} clean categories to {out_file}")
