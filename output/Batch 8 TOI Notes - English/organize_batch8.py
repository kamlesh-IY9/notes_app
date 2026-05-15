import os
import shutil
import re

base_dir = "/home/kamleshpatil/Desktop/Notes - PR and ontata/notes_app/output/Batch 8 TOI Notes - English"
text_dir = os.path.join(base_dir, "text")
image_dir = os.path.join(base_dir, "images")

os.makedirs(text_dir, exist_ok=True)
os.makedirs(image_dir, exist_ok=True)

# Collect all pairs
pairs = []

for job_id in os.listdir(base_dir):
    job_path = os.path.join(base_dir, job_id)
    if not os.path.isdir(job_path) or job_id in ["text", "images"]:
        continue
    
    notes_path = os.path.join(job_path, "notes")
    screenshots_path = os.path.join(job_path, "screenshots")
    
    if not os.path.exists(notes_path) or not os.path.exists(screenshots_path):
        continue
        
    for note_file in os.listdir(notes_path):
        if not note_file.endswith(".txt"):
            continue
            
        # Extract ID from note filename like 1100_en_US_...
        match = re.match(r"(\d+)_", note_file)
        if not match:
            continue
            
        id_str = match.group(1)
        
        # Find matching screenshot
        screenshot_file = None
        for s_file in os.listdir(screenshots_path):
            if s_file.startswith(id_str + " ") and s_file.endswith(".jpg"):
                screenshot_file = s_file
                break
        
        if screenshot_file:
            pairs.append({
                "id": int(id_str),
                "note_path": os.path.join(notes_path, note_file),
                "screenshot_path": os.path.join(screenshots_path, screenshot_file)
            })

# Sort pairs by original ID
pairs.sort(key=lambda x: x["id"])

print(f"Found {len(pairs)} matching pairs.")

# Rename and move
for i, pair in enumerate(pairs, 1):
    new_name = f"DS104_TOI_Notes_B8_{i:03d}"
    
    new_note_path = os.path.join(text_dir, new_name + ".txt")
    new_image_path = os.path.join(image_dir, new_name + ".jpg")
    
    shutil.move(pair["note_path"], new_note_path)
    shutil.move(pair["screenshot_path"], new_image_path)
    
    if i % 50 == 0:
        print(f"Processed {i} pairs...")

print("Renaming and organization complete.")
