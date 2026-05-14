import os
from pathlib import Path

# Paths
TXT_DIR = Path("/home/kamleshpatil/Desktop/Notes - PR and ontata/notes_app/output/final hindi b1 TOI/txt")

# Category mapping keywords
CAT_MAP = {
    "finance stocks portfolio": ["धन", "बजट", "आईपओ", "सेंसेक्स", "निफ्टी", "टर्म शीट", "आरबीआई", "टैक्स", "बॉन्ड", "लोन", "वायदा", "सेबी", "निवेश", "स्टॉक", "मूल्य"],
    "technology": ["मॉडल", "तुलना", "एआई", "मल्टीमॉडल", "मैपिंग", "सिस्टम", "सॉफ्टवेयर", "डिजिटल", "वेक्टर", "अनुक्रमण", "डेटा", "मेमोरी", "सर्च", "प्रोसेसर", "कंप्यूटर"],
    "academic professional": ["मिशन", "सौर", "आदित्य", "गगनयन", "इसरो", "एनालिसिस", "अध्ययन", "विश्लेषण", "गणना", "प्रयोग", "फिजिक्स", "केमिस्ट्री", "थ्योरी", "समीक्षा"],
    "government politics": ["राज्य", "राजनीति", "शासन", "नीति", "सार्वजनिक", "सशोधन", "अंतरराष्ट्रीय", "मामले", "प्रशासन", "नगर", "योजना"],
    "weather": ["विक्षोभ", "तापमान", "ताप", "गर्मी", "लू", "हीटवेव", "मानसून", "चक्रवात", "बारिश", "बाढ़", "पर्यावरण", "स्मॉग", "हवा", "वायु"],
    "food": ["पनीर", "किण्वन", "ब्रेड", "रोटी", "दूध", "मक्खन", "घी", "दाल", "तड़का", "व्यंजन", "रेसिपी", "खाना"],
    "health fitness": ["फिजियोथेरेपी", "फिटनेस", "योग", "आसन", "व्यायाम", "स्वास्थ्य", "बीमारी", "डॉक्टर", "शरीर"],
    "sports": ["क्रिकेट", "मैच", "बल्लेबाजी", "गेंदबाजी", "टी20", "आईपीएल", "पावरप्ले", "रन", "विकेट", "फील्डर", "स्पिन"],
    "automotive": ["इलेक्ट्रिक", "बस", "स्कूटर", "वाहन", "टायर", "इंजन", "मैकेनिक", "ब्रेकिंग", "चार्जिंग", "ईवी", "रेंज"],
    "gaming": ["गेमिंग", "कंसोल", "गेम", "प्लेयर", "स्कोर", "लेवल", "ईस्पोर्ट्स"],
    "travel vacation": ["यात्रा", "पर्यटन", "होटल", "टिकट", "सफर", "छुट्टियां"],
}

def get_category(title, content):
    text = (title + " " + content).lower()
    for cat, keywords in CAT_MAP.items():
        if any(kw in text for kw in keywords):
            return cat
    return "academic professional" # Default

def process():
    files = sorted(list(TXT_DIR.glob("*.txt")))
    results = []
    
    for f in files:
        lines = f.read_text(encoding='utf-8').split('\n')
        title = lines[0] if lines else ""
        content = " ".join(lines[1:])
        
        category = get_category(title, content)
        results.append((f.name, category))
        
    print("Filename\tCategory")
    for fname, cat in results:
        print(f"{fname}\t{cat}")

if __name__ == "__main__":
    process()
