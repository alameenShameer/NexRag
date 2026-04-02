import os
import glob
from rdflib import Graph

def merge_ttl_files(data_dir="data", output_file="data/merged_kg.ttl"):
    g = Graph()
    
    # Track if we successfully parsed anything
    parsed_files = []
    
    # Glob all .ttl files in data_dir
    files = glob.glob(os.path.join(data_dir, "*.ttl"))
    
    for file in files:
        # Skip the merged file itself if it already exists
        if os.path.basename(file) == os.path.basename(output_file):
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
