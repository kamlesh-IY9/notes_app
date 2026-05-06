#!/bin/bash

# Process a directory pair (notes and screenshots)
process_directory() {
    local base_dir="$1"
    local notes_dir="$base_dir/notes"
    local screenshots_dir="$base_dir/screenshots"
    local trash_dir="$base_dir/trash"
    
    echo "Processing $base_dir..."
    
    # Create trash directory if it doesn't exist
    mkdir -p "$trash_dir"
    
    # Track used names to avoid duplicates
    declare -A used_names
    
    # Process each notes file
    for notes_file in "$notes_dir"/*.txt; do
        # Skip if no files match
        [[ ! -f "$notes_file" ]] && continue
        
        # Get the first line of the notes file
        first_line=$(head -n 1 "$notes_file")
        
        # Clean the first line for use as filename
        # Remove problematic characters and extra spaces
        clean_name=$(echo "$first_line" | sed 's/[<>:"/\\|?*]//g' | sed 's/  */ /g' | sed 's/^ *//' | sed 's/ *$//')
        
        # Split into words and take 2-6 words
        words=($clean_name)
        word_count=${#words[@]}
        
        if [ $word_count -lt 2 ]; then
            # If less than 2 words, use what we have
            selected_words=("${words[@]}")
        elif [ $word_count -gt 6 ]; then
            # If more than 6 words, take first 6
            selected_words=("${words[@]:0:6}")
        else
            # Use all words (2-6 words)
            selected_words=("${words[@]}")
        fi
        
        # Join words back together
        base_name=$(IFS=' '; echo "${selected_words[*]}")
        
        # Handle duplicate names
        counter=1
        final_name="$base_name"
        while [[ -n "${used_names[$final_name]}" ]]; do
            final_name="${base_name} ($counter)"
            ((counter++))
        done
        
        # Mark this name as used
        used_names["$final_name"]=1
        
        # Get file extensions
        notes_ext="${notes_file##*.}"
        
        # Find corresponding screenshot file
        base_num=$(basename "$notes_file" | cut -d'_' -f1)
        screenshot_file="$screenshots_dir/${base_num}*.jpg"
        
        # Check if screenshot file exists
        if compgen -G "$screenshot_file" > /dev/null; then
            # Get the actual screenshot file path
            screenshot_file=$(ls $screenshots_dir/${base_num}*.jpg | head -1)
            screenshot_ext="${screenshot_file##*.}"
            
            # Rename both files
            mv "$notes_file" "$notes_dir/${final_name}.${notes_ext}"
            mv "$screenshot_file" "$screenshots_dir/${final_name}.${screenshot_ext}"
            echo "Renamed: $base_num -> $final_name"
        else
            # No matching screenshot, move notes to trash
            mv "$notes_file" "$trash_dir/"
            echo "Moved to trash (no matching screenshot): $(basename "$notes_file")"
        fi
    done
    
    # Process orphaned screenshot files (those without matching notes)
    for screenshot_file in "$screenshots_dir"/*.jpg; do
        # Skip if no files match
        [[ ! -f "$screenshot_file" ]] && continue
        
        # Extract the number part
        base_num=$(basename "$screenshot_file" | cut -d' ' -f1)
        
        # Check if corresponding notes file exists
        notes_file="$notes_dir/${base_num}_*.txt"
        if ! compgen -G "$notes_file" > /dev/null; then
            # No matching notes file, move screenshot to trash
            mv "$screenshot_file" "$trash_dir/"
            echo "Moved to trash (no matching notes): $(basename "$screenshot_file")"
        fi
    done
    
    echo "Finished processing $base_dir"
    echo "------------------------"
}

# Process both directories
process_directory "0bdf8da3d089"
process_directory "b5be811d4125"

echo "All processing complete!"