import os
import re

# Use the current working directory provided by the environment
base_dir = "./output/jobs"
report_file = "./quality_report.md"

def is_bad(name):
    # Check for non-ASCII
    try:
        name.encode("ascii")
    except UnicodeEncodeError:
        return True
    
    # Check for specific "gibberish" or "technical" tokens identified by user
    suspicious_tokens = ["getattr", "DateTime", "Likewise", "_v back", "iku-square", "backend Ri"]
    if any(token in name for token in suspicious_tokens):
        return True
    
    return False

bad_files_found = []

if os.path.exists(base_dir):
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if is_bad(f):
                bad_files_found.append(os.path.join(root, f))

with open(report_file, "w") as rf:
    rf.write("# Quality Audit Report\n\n")
    rf.write("## Findings\n")
    rf.write(f"Total 'nonsense' files identified: {len(bad_files_found)}\n\n")
    
    if bad_files_found:
        rf.write("### List of problematic files:\n")
        for bf in bad_files_found:
            rf.write(f"- {bf}\n")
        rf.write("\n## Recommendation\n")
        rf.write("These files should be deleted as they represent LLM hallucinations or technical glitches rather than authentic data.\n")
    else:
        rf.write("No 'nonsense' files found meeting the criteria. The dataset appears clean.\n")

print(f"Report generated at {report_file}")
