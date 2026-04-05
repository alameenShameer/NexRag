import os
import glob
from rdflib import Graph
from services.config import OFFICIAL_KG_PATH, UPLOAD_KG_PATH

def merge_ttl_files(data_dir="data", output_file="data/merged_kg.ttl"):
    g = Graph()
    
    # Track if we successfully parsed anything
    parsed_files = []
    
    preferred_files = [str(path) for path in (OFFICIAL_KG_PATH, UPLOAD_KG_PATH) if path.exists()]
    files = preferred_files or glob.glob(os.path.join(data_dir, "*.ttl"))
    
    for file in files:
        file_name = os.path.basename(file)
        # Skip inactive legacy graph sources and the merged file itself.
        if file_name == os.path.basename(output_file) or file_name in {"mesitam_data.ttl", "university_faq.ttl"}:
            continue
            
        try:
            print(f"Parsing {file}...")
            g.parse(file, format="turtle")
            parsed_files.append(file)
        except Exception as e:
            print(f"Error parsing {file}: {e}")
            
    if parsed_files:
        g.serialize(destination=output_file, format="turtle")
        print(f"Successfully merged {len(parsed_files)} files into {output_file}")
    else:
        print("No valid .ttl files found to merge.")

if __name__ == "__main__":
    merge_ttl_files()
