import os
import shutil
import re

base_dir = "/home/kamleshpatil/Desktop/Notes - PR and ontata/notes_app/output/Batch 8 TOI Notes - English"
text_dir = os.path.join(base_dir, "text")
images_dir = os.path.join(base_dir, "images")

final_dir = "/home/kamleshpatil/Desktop/Notes - PR and ontata/notes_app/output/Final_300_TOI_English"
final_txt_dir = os.path.join(final_dir, "txt")
final_img_dir = os.path.join(final_dir, "images")

os.makedirs(final_txt_dir, exist_ok=True)
os.makedirs(final_img_dir, exist_ok=True)

# Heuristics based on client feedback
BAD_WORDS = [
    # Article tone words
    "delve", "moreover", "furthermore", "comprehensive", "holistic", 
    "testament", "tapestry", "robust", "seamless", "unlock", "empower", 
    "navigate", "journey", "crucial", "essential", "vital", "in conclusion",
    "according to", "researchers", "studies show", "this article",
    # Specific category rejections
    "boarding pass", "flight terminal", "security check", "passport control",
    "boarding process", "airport security", "gate agent", "tsa",
    # Non-car automotive words (just to be safe)
    "motorcycle", "bicycle", "airplane", "boat", "ship", "train"
]

GOOD_WORDS = [
    # Casual shorthand and reactions
    "iirc", "btw", "idk", "w/", "w/o", "b/c", "tho", "tbh", "lol", "hmm", 
    "def", "prob", "kinda", "gonna", "wanna", "rn", "make sure", "wait no",
    "asked the", "confused on", "need to test", "still not clear"
]

scored_notes = []

for filename in os.listdir(text_dir):
    if not filename.endswith(".txt"):
        continue
    
    filepath = os.path.join(text_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().lower()
        
    score = 100
    
    # Penalize article words heavily
    for bw in BAD_WORDS:
        if bw in content:
            score -= 15
            
    # Reward human-like shorthand
    for gw in GOOD_WORDS:
        if gw in content:
            score += 10
            
    # Penalize perfectly punctuated, long paragraphs (article-like)
    sentences = re.split(r'[.!?]+', content)
    long_sentences = sum(1 for s in sentences if len(s.split()) > 20)
    if long_sentences > 2:
        score -= 20
        
    # Formatting (e.g. lots of lists or weird text)
    if content.count("*") > 10:
        score -= 10
        
    scored_notes.append({
        "filename": filename,
        "score": score
    })

# Sort by score descending
scored_notes.sort(key=lambda x: x["score"], reverse=True)

# Take top 300
best_300 = scored_notes[:300]

print(f"Selecting top 300 out of {len(scored_notes)}. Lowest score selected: {best_300[-1]['score']}")

# Copy and rename
for i, item in enumerate(best_300, 1):
    old_txt = os.path.join(text_dir, item["filename"])
    # Original filename like: DS104_TOI_Notes_B8_001.txt
    old_base = item["filename"].replace(".txt", "")
    old_img = os.path.join(images_dir, old_base + ".jpg")
    
    new_base = f"DS104_TOI_Notes_B8_{i:03d}"
    new_txt = os.path.join(final_txt_dir, new_base + ".txt")
    new_img = os.path.join(final_img_dir, new_base + ".jpg")
    
    shutil.copy2(old_txt, new_txt)
    shutil.copy2(old_img, new_img)
    
    if i % 50 == 0:
        print(f"Copied {i}/300 pairs...")

print("Selection and renaming complete. Final files are in 'output/Final_300_TOI_English'")
