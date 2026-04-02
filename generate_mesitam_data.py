from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

os.makedirs("data/pdfs", exist_ok=True)

def create_pdf(filename, title, content_pages):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Title Page
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 200, title)
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - 230, "MES Institute of Technology and Management")
    c.drawCentredString(width / 2, height - 250, "Official Document")
    c.showPage()
    
    # Content Pages
    c.setFont("Helvetica", 12)
    y = height - 50
    
    for page_text in content_pages:
        lines = page_text.split('\n')
        for line in lines:
            if y < 50:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 12)
                
            if line.startswith("#"):
                c.setFont("Helvetica-Bold", 14)
                c.drawString(50, y, line.replace("#", "").strip())
                y -= 20
                c.setFont("Helvetica", 12)
            else:
                c.drawString(50, y, line)
                y -= 15
        c.showPage()
        y = height - 50
        
    c.save()
    print(f"Created {filename}")

# 1. KTU Handbook (Regulation)
handbook_content = [
    """# KTU B.Tech Regulations 2019
    
    # R.1 Attendance
    Attendance is the physical presence of the student in the class. 
    A student must secure a minimum of 75% attendance in each course to be eligible to appear for the End Semester Examination.
    Condonation of shortage of attendance is allowed up to 10% (i.e. between 65% and 75%).
    Condonation is allowed only twice during the entire course.
    
    # R.2 Grading System
    Grades are awarded based on the total marks (Internal + End Semester).
    S: 90% and above (Outstanding)
    A+: 85% - 90% (Excellent)
    A: 80% - 85% (Very Good)
    B+: 75% - 80% (Good)
    B: 70% - 75% (Above Average)
    C: 60% - 70% (Average)
    P: 50% - 60% (Pass)
    F: Below 50% (Fail)
    
    # R.3 Credit System
    A student needs to earn 160 credits to be eligible for the B.Tech degree.
    B.Tech (Honours) requires an additional 20 credits (Total 180).
    Minor degree also requires an additional 20 credits.
    """,
    """# R.4 Leave Rules
    # Duty Leave
    Duty leave is granted to students for participating in official events, sports, or university activities.
    Maximum limit: 10 days per semester.
    Application must be recommended by the Faculty Advisor and approved by the HOD.
    
    # Medical Leave
    Medical leave does not exempt the student from the minimum attendance requirement of 75%, 
    but can be considered for Condonation.
    """
]
create_pdf("data/pdfs/KTU_Handbook_2024.pdf", "KTU B.Tech Regulations 2024", handbook_content)

# 2. CSE Syllabus (Syllabus)
syllabus_content = [
    """# CST301 - Theory of Computation
    
    # Module 1: Finite Automata
    Introduction to Automata Theory, Strings, Languages.
    DFA (Deterministic Finite Automata): Definition, Transition diagram.
    NFA (Nondeterministic Finite Automata): Definition, Equivalence of NFA and DFA.
    
    # Module 2: Regular Expressions
    Regular Expressions and Languages.
    Pumping Lemma for Regular Languages.
    Closure properties of Regular Languages.
    
    # Assessment
    Internal Marks: 50 (2 Series Exams + Assignments)
    End Semester Exam: 100
    Credits: 4
    """,
    """# CST306 - Algorithm Analysis and Design
    
    # Module 1: Complexity Analysis
    Time and Space Complexity. Big-O notation.
    Divide and Conquer: Merge Sort, Quick Sort.
    
    # Module 2: Dynamic Programming
    Principle of Optimality.
    Knapsack Problem, Longest Common Subsequence.
    
    # Faculty
    Course Coordinator: Dr. Anitha S (HOD CSE)
    """
]
create_pdf("data/pdfs/CSE_Syllabus_S5.pdf", "Syllabus - B.Tech CSE S5", syllabus_content)

# 3. College Circular (Notice)
circular_content = [
    """# NOTICE: Tech Fest 'NexTech 2026'
    
    Date: 2026-03-15
    Venue: Main Auditorium
    
    All students are requested to participate in the upcoming Tech Fest.
    Classes will be suspended on 15th March afternoon.
    
    # Student Coordinators
    Rahul (S7 CSE)
    Priya (S5 ECE)
    """
]
create_pdf("data/pdfs/Circular_TechFest.pdf", "Circular - NexTech 2026", circular_content)
