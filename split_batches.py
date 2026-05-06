import os
import shutil

organized_dir = "output/Batch - 3 Final - P & R Notes/organized"
text_dir = os.path.join(organized_dir, "text")
img_dir = os.path.join(organized_dir, "image")

batch1_dir = os.path.join(organized_dir, "batch_1")
batch2_dir = os.path.join(organized_dir, "batch_2")

for b_dir in [batch1_dir, batch2_dir]:
    os.makedirs(os.path.join(b_dir, "text"), exist_ok=True)
    os.makedirs(os.path.join(b_dir, "image"), exist_ok=True)

# Get all text files and sort them
text_files = sorted([f for f in os.listdir(text_dir) if f.endswith('.txt')])
total_files = len(text_files)
midpoint = total_files // 2

for i, txt_file in enumerate(text_files):
    base_name = os.path.splitext(txt_file)[0]
    
    # Find matching image file
    img_file = None
    for ext in ['.jpg', '.png', '.jpeg']:
        candidate = base_name + ext
        if os.path.exists(os.path.join(img_dir, candidate)):
            img_file = candidate
            break
            
    if not img_file:
        print(f"Warning: No image found for {txt_file}")
        continue
        
    # Determine target batch
    if i < midpoint:
        target_b_dir = batch1_dir
    else:
        target_b_dir = batch2_dir
        
    # Move files
    src_txt = os.path.join(text_dir, txt_file)
    src_img = os.path.join(img_dir, img_file)
    
    dst_txt = os.path.join(target_b_dir, "text", txt_file)
    dst_img = os.path.join(target_b_dir, "image", img_file)
    
    shutil.move(src_txt, dst_txt)
    shutil.move(src_img, dst_img)

# Remove empty old directories
os.rmdir(text_dir)
os.rmdir(img_dir)

print(f"Split {total_files} into two batches:")
print(f"Batch 1: {midpoint} pairs")
print(f"Batch 2: {total_files - midpoint} pairs")
