import json
from pathlib import Path

# Load index
index_file = Path("files/.index.json")
with open(index_file, "r", encoding="utf-8") as f:
    idx = json.load(f)

# Set all user/country_user uploaded files to "Needs Review"
modified = 0
for filename, meta in idx.items():
    uploader_role = meta.get("uploader_role", "user")
    
    # If uploaded by user or country_user, set publication_status
    if uploader_role == "user" or uploader_role.startswith("country_user_"):
        if "publication_status" not in meta:
            meta["publication_status"] = "needs_review"
            modified += 1
            print(f"✅ Set {filename} to 'Needs Review'")

# Save index
with open(index_file, "w", encoding="utf-8") as f:
    json.dump(idx, f, indent=2, ensure_ascii=False)

print(f"\n🎉 Updated {modified} files!")