import os
import json
import zipfile
import shutil
from pathlib import Path

def main():
    root = Path(__file__).parent
    download_dir = root / "Download"
    download_dir.mkdir(exist_ok=True)
    
    manifest_path = root / "local_mode" / "pack-manifest.json"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    bundle_name = manifest.get("bundleName", "PineWoodDerby-Offline")
    files = manifest.get("files", [])
    optional_files = manifest.get("optionalFiles", [])
    
    zip_path = download_dir / f"{bundle_name}.zip"
    
    print(f"Building {zip_path}...")
    
    import re
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fpath in files:
            source = root / fpath
            if source.exists():
                arcname = Path(bundle_name) / fpath
                
                # Intercept config.js to permanently enable local mode in the download bundle
                if fpath == "config.js":
                    with open(source, 'r', encoding='utf-8') as cf:
                        content = cf.read()
                    # Replace the entire isLocalMode() function safely
                    content = re.sub(
                        r'function\s+isLocalMode\(\)\s*\{[\s\S]*?\}\s*catch\s*\{[\s\S]*?\}\s*\}',
                        'function isLocalMode() {\\n  return true; // Hardcoded for offline pack\\n}',
                        content
                    )
                    zf.writestr(str(arcname), content)
                else:
                    zf.write(source, arcname)
                    
                print(f"Added {fpath}")
            elif fpath not in optional_files:
                print(f"WARNING: Required file missing: {fpath}")
                
    print(f"\nSuccessfully built offline pack at: {zip_path.relative_to(root)}")

if __name__ == "__main__":
    main()
