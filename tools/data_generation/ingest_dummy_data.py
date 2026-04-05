import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from rag import index_pdf

files = [
    ("data/pdfs/KTU_Handbook_2024.pdf", "REGULATION"),
    ("data/pdfs/CSE_Syllabus_S5.pdf", "SYLLABUS"),
    ("data/pdfs/Circular_TechFest.pdf", "NOTICE")
]

print("--- Starting Bulk Ingestion for MESITAM ---")
for path, cat in files:
    if os.path.exists(path):
        print(f"Ingesting {path} as {cat}...")
        index_pdf(path, category=cat)
    else:
        print(f"Skipping {path} (Not Found)")
        
print("Bulk Ingestion Complete!")
