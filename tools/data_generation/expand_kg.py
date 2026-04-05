import random
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

departments = ["CSE", "ECE", "ME", "CE", "EEE"]
designations = ["Assistant Professor", "Associate Professor", "Professor"]
names = ["Aisha", "Babu", "Chitra", "Deepak", "Elena", "Faisal", "Gita", "Hari", "Isha", "John", "Kavya", "Leo", "Maya", "Nitin", "Omar", "Pooja", "Qasim", "Ravi", "Sita", "Tariq", "Uma", "Varun", "Zara"]

courses = [
    ("CS", "Computer Networks", "CN"),
    ("CS", "Database Systems", "DBMS"),
    ("CS", "Operating Systems", "OS"),
    ("CS", "Data Structures", "DS"),
    ("EC", "Signals & Systems", "SS"),
    ("EC", "VLSI Design", "VLSI"),
    ("EC", "Microcontrollers", "MC"),
    ("ME", "Thermodynamics", "TD"),
    ("ME", "Fluid Mechanics", "FM"),
    ("ME", "Machine Design", "MD"),
    ("CE", "Structural Analysis", "SA"),
    ("CE", "Fluid Dynamics", "FD"),
    ("CE", "Surveying", "SUR"),
    ("EE", "Power Systems", "PS"),
    ("EE", "Control Systems", "CS")
]

with open("data/mesitam_data.ttl", "a", encoding="utf-8") as f:
    f.write("\n### Auto-Generated Departments ###\n")
    f.write(":CE a :Department ;\n    :hasName \"Civil Engineering\" ;\n    :abbreviation \"CE\" .\n\n")
    f.write(":EEE a :Department ;\n    :hasName \"Electrical and Electronics Engineering\" ;\n    :abbreviation \"EEE\" .\n\n")

    f.write("### Auto-Generated Faculty ###\n")
    for i, name in enumerate(names):
        dept = random.choice(departments)
        desig = random.choice(designations)
        f.write(f":Prof_{name} a :Faculty ;\n")
        f.write(f"    :hasName \"Prof. {name}\" ;\n")
        f.write(f"    :hasDesignation \"{desig}\" ;\n")
        f.write(f"    :belongsTo :{dept} .\n\n")

    f.write("### Auto-Generated Courses ###\n")
    for idx, (code_prefix, name, abbr) in enumerate(courses):
        f.write(f":{abbr}_{idx} a :Course ;\n")
        f.write(f"    :hasName \"{name}\" ;\n")
        f.write(f"    :abbreviation \"{abbr}\" ;\n")
        f.write(f"    :hasCode \"{code_prefix}20{idx}\" ;\n")
        f.write(f"    :hasCredit 4 .\n\n")

print("Added much more data to mesitam_data.ttl")
