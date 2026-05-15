import os
import sys
import asyncio
from pathlib import Path

backend_dir = Path("/home/kamleshpatil/Desktop/Notes - PR and ontata/notes_app/backend")
sys.path.insert(0, str(backend_dir.parent))

from dotenv import load_dotenv
load_dotenv(backend_dir.parent / ".env")

from backend.core.llm_clients import LLMClients

txt_dir = "/home/kamleshpatil/Desktop/Notes - PR and ontata/notes_app/output/Final_300_TOI_English/txt"
out_csv = "/home/kamleshpatil/Desktop/Notes - PR and ontata/notes_app/output/Final_300_TOI_English/metadata_categories.csv"

CATEGORIES = [
    "School & College life", "Work-life balance", "Movies", "TV Shows", 
    "Music", "Gaming", "Food", "Traditions", "Celebrations", "Hobbies", 
    "Outdoor Adventure", "Finance", "Weather", "Travel/Transportation", "Automotive"
]

async def main():
    llm = LLMClients()
    
    files = sorted([f for f in os.listdir(txt_dir) if f.endswith(".txt")])
    
    # Read titles (first line)
    notes_data = []
    for f in files:
        with open(os.path.join(txt_dir, f), 'r') as file:
            title = file.readline().strip()
            notes_data.append({"file": f, "title": title, "category": ""})
            
    print(f"Loaded {len(notes_data)} files.")
    
    batch_size = 50
    for i in range(0, len(notes_data), batch_size):
        batch = notes_data[i:i+batch_size]
        
        prompt = f"""You are a precise categorization assistant. Map each of the following note titles to EXACTLY one of these categories:
{', '.join(CATEGORIES)}

Note Titles:
"""
        for idx, item in enumerate(batch):
            prompt += f"{idx}. {item['title']}\n"
            
        prompt += """
Output EXACTLY in this format:
0. Category Name
1. Category Name
"""
        
        try:
            resp = await llm.generate(
                system_prompt="You are a categorization engine. Output ONLY the exact category names from the list.",
                user_prompt=prompt,
                provider="auto"
            )
            
            lines = [line.strip() for line in resp.split("\n") if "." in line]
            for idx, item in enumerate(batch):
                # find line matching idx.
                for line in lines:
                    if line.startswith(f"{idx}."):
                        cat = line.split(".", 1)[1].strip()
                        # validate
                        if cat in CATEGORIES:
                            item["category"] = cat
                        else:
                            # fuzzy match
                            for c in CATEGORIES:
                                if c.lower() in cat.lower():
                                    item["category"] = c
                                    break
                            if not item["category"]:
                                item["category"] = cat # fallback
                        break
        except Exception as e:
            print(f"Error on batch {i}: {e}")
            
        print(f"Processed up to {i + len(batch)}")
        
    with open(out_csv, "w", encoding="utf-8") as f:
        f.write("Filename,Title,Category\n")
        for item in notes_data:
            cat = item["category"].replace('"', '')
            title = item["title"].replace('"', '""')
            f.write(f"{item['file']},\"{title}\",\"{cat}\"\n")
            
    print(f"Saved metadata to {out_csv}")

if __name__ == "__main__":
    asyncio.run(main())
