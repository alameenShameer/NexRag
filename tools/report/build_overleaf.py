from pathlib import Path
import re
import shutil
import zipfile


ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "report"
OVERLEAF_DIR = REPORT_DIR / "overleaf"
CHAPTERS_DIR = OVERLEAF_DIR / "chapters"


SOURCE_FILES = [
    "01_introduction.md",
    "02_literature_review.md",
    "03_proposed_system.md",
    "04_results_and_discussion.md",
    "05_conclusion_and_future_scope.md",
]


UNICODE_REPLACEMENTS = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "--",
    "\u2014": "---",
    "\u2026": "...",
    "\u2192": "->",
    "\u00a0": " ",
}


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    escaped = text
    for old, new in replacements.items():
        escaped = escaped.replace(old, new)
    return escaped


def normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    for old, new in UNICODE_REPLACEMENTS.items():
        normalized = normalized.replace(old, new)
    return normalized


def strip_heading_numbers(line: str) -> str:
    stripped = line.strip()

    chapter_match = re.match(r"#\s+CHAPTER\s+\d+\s+(.+)", stripped, flags=re.IGNORECASE)
    if chapter_match:
        return f"# {chapter_match.group(1).strip()}"

    section_match = re.match(r"##\s+\d+\.\d+\s+(.+)", stripped)
    if section_match:
        return f"## {section_match.group(1).strip()}"

    subsection_match = re.match(r"###\s+\d+\.\d+\.\d+\s+(.+)", stripped)
    if subsection_match:
        return f"### {subsection_match.group(1).strip()}"

    return line


def convert_equation_line(line: str) -> str | None:
    stripped = line.strip()
    match = re.match(r"<div align=\"center\">(.*)\((\d+\.\d+)\)</div>", stripped)
    if not match:
        return None

    body = match.group(1).strip()
    eq_no = match.group(2).strip()
    body = latex_escape(body)
    return "\n".join(
        [
            r"\begin{equation}",
            rf"\text{{{body}}}",
            rf"\tag{{{eq_no}}}",
            r"\end{equation}",
        ]
    )


def convert_figure_placeholder(line: str) -> str | None:
    stripped = line.strip()
    match = re.match(r"\[Insert Figure\s+([\d.]+)\s+here:\s*(.+)\]", stripped, flags=re.IGNORECASE)
    if not match:
        return None

    description = latex_escape(match.group(2).strip())
    return "\n".join(
        [
            r"\begin{center}",
            rf"\fbox{{\parbox{{0.92\textwidth}}{{\textbf{{Figure Placeholder:}} {description}}}}}",
            r"\end{center}",
        ]
    )


def preprocess_markdown(text: str) -> str:
    lines = normalize_text(text).split("\n")
    output_lines = []

    for index, line in enumerate(lines):
        if index == 0 and line.strip().startswith("# REFERENCES"):
            continue

        equation_block = convert_equation_line(line)
        if equation_block is not None:
            output_lines.append(equation_block)
            output_lines.append("")
            continue

        figure_block = convert_figure_placeholder(line)
        if figure_block is not None:
            output_lines.append(figure_block)
            output_lines.append("")
            continue

        output_lines.append(strip_heading_numbers(line))

    return "\n".join(output_lines).rstrip() + "\n"


def build_frontmatter() -> str:
    return r"""
\begin{titlepage}
\thispagestyle{empty}
\begin{center}
\vspace*{1.5cm}

{\Large \textbf{NEXRAG: A LOCAL-FIRST HYBRID KNOWLEDGE GRAPH AND RETRIEVAL-AUGMENTED GENERATION ACADEMIC ASSISTANT FOR ACADEMIC QUERY ANSWERING}\par}

\vspace{1.5cm}

{\large A project report submitted in partial fulfillment of the requirements for the award of the degree of Bachelor of Technology in Computer Science and Engineering\par}

\vspace{1.5cm}

Submitted by\par
\vspace{0.3cm}
{\large [Student Name]\par}
{\large [Register Number]\par}

\vspace{1cm}

Under the guidance of\par
\vspace{0.3cm}
{\large [Project Guide Name]\par}
{\large [Designation]\par}

\vfill

Department of Computer Science and Engineering\par
MES Institute of Technology and Management\par
Chathannoor, Kollam, Kerala\par
[Affiliated University Name]\par
[Month Year]

\end{center}
\end{titlepage}

\chapter*{CERTIFICATE}
\addcontentsline{toc}{chapter}{CERTIFICATE}
This is to certify that the report entitled \textbf{``NexRag: A Local-First Hybrid Knowledge Graph and Retrieval-Augmented Generation Academic Assistant for Academic Query Answering''} is a bonafide record of the project work carried out by \textbf{[Student Name]}, bearing register number \textbf{[Register Number]}, in the Department of Computer Science and Engineering, MES Institute of Technology and Management, during the academic year \textbf{[Academic Year]}, in partial fulfillment of the requirements for the award of the degree of Bachelor of Technology in Computer Science and Engineering. This work has been carried out under my supervision and guidance and, to the best of my knowledge, has not formed the basis for the award of any degree, diploma, associateship, fellowship, or any other similar title in any university or institution.

\vspace{1cm}
Guide Signature: \hrulefill

Name: [Project Guide Name]

Designation: [Guide Designation]

\vspace{0.6cm}
Head of Department Signature: \hrulefill

Name: [Head of Department Name]

\vspace{0.6cm}
External Examiner Signature: \hrulefill

\vspace{0.6cm}
Place: Chathannoor\par
Date: [Date]

\chapter*{DECLARATION}
\addcontentsline{toc}{chapter}{DECLARATION}
I hereby declare that the project report entitled \textbf{``NexRag: A Local-First Hybrid Knowledge Graph and Retrieval-Augmented Generation Academic Assistant for Academic Query Answering''} is the original work carried out by me during the academic year \textbf{[Academic Year]} under the guidance of \textbf{[Project Guide Name]}, Department of Computer Science and Engineering, MES Institute of Technology and Management. I further declare that this report has not been submitted, either in full or in part, to any other university or institution for the award of any degree or diploma.

I affirm that all sources of information, ideas, methods, and prior research used in preparing this report have been duly acknowledged in the text and listed in the references section in Harvard style.

\vspace{1cm}
Signature of Student: \hrulefill

Name: [Student Name]

Register Number: [Register Number]

Date: [Date]

\chapter*{ACKNOWLEDGEMENT}
\addcontentsline{toc}{chapter}{ACKNOWLEDGEMENT}
The successful completion of this project report would not have been possible without the support, encouragement, and guidance of many individuals and resources that contributed to the development of both the software system and this academic document. I express my sincere gratitude to the Department of Computer Science and Engineering, MES Institute of Technology and Management, for providing an environment that encourages experimentation, problem solving, and independent technical exploration.

I place on record my heartfelt thanks to \textbf{[Project Guide Name]}, whose supervision, timely suggestions, and constructive criticism helped shape the project at every stage. I also extend my gratitude to the Head of the Department, faculty members, and project coordinators for their encouragement and for creating opportunities to review the work critically during its progression.

I gratefully acknowledge the developers and research communities behind the open technical resources that enabled this work, including the authors of foundational research in retrieval-augmented generation, dense passage retrieval, sentence embeddings, neural reranking, and knowledge graph technologies.

\chapter*{ABSTRACT}
\addcontentsline{toc}{chapter}{ABSTRACT}
Academic institutions increasingly require intelligent information access systems that can answer student and faculty queries accurately, transparently, and without dependence on proprietary cloud infrastructure. Conventional chatbots often struggle in such settings because they either rely solely on unstructured document retrieval, which may miss explicit institutional relationships, or depend exclusively on structured databases, which cannot capture the rich explanatory detail contained in handbooks, circulars, seminar guidelines, and syllabus documents.

This project presents \textbf{NexRag}, a local-first hybrid academic assistant that combines a knowledge graph, a document retrieval pipeline, and a locally hosted language model to answer academic queries in a grounded and explainable manner. The proposed system integrates a FastAPI backend, a React and Vite frontend, Apache Jena Fuseki for RDF-based knowledge graph querying, FAISS for dense vector indexing, BM25 for sparse lexical matching, and a cross-encoder reranker for relevance refinement. User queries are first routed through an intent classifier, after which entity-centric questions are forwarded to the knowledge graph, document-centric questions are processed through the retrieval engine, and suitable cases are answered using a combined mode that merges graph facts with supporting document evidence.

The repository state used for this report demonstrates a functioning pipeline with seven indexed PDF documents and 290 vectorized text chunks, alongside knowledge graph source files representing departments, faculty, courses, and regulations. Verification performed on 3 April 2026 confirmed successful module imports, correct intent classification on the available router test cases, successful loading of the embedding and reranking models, and meaningful retrieval behavior for academic queries such as attendance rules and seminar guidelines.

\noindent\textbf{Keywords:} retrieval-augmented generation, knowledge graph, academic assistant, FAISS, BM25, reranking, FastAPI, React, Fuseki, local LLM

\tableofcontents
\clearpage

\chapter*{LIST OF FIGURES}
\addcontentsline{toc}{chapter}{LIST OF FIGURES}
\begin{enumerate}[label=Figure \arabic*., leftmargin=2.8cm]
\item High-Level Architecture of NexRag
\item End-to-End Query Processing Flow
\item Knowledge Graph Maintenance and Validation Workflow
\item Data Flow Diagram for the Proposed System
\item Main User Interface of the NexRag Frontend
\item Streaming Answer View with Routing and Source Evidence
\item Intelligence Panel Showing Retrieved Sources and System Status
\item Knowledge Graph Editor Interface for Turtle File Update
\item Retrieval Output for an Attendance Rule Query
\item Retrieval Output for a Seminar Guideline Query
\item Comparative Mode Analysis of KG, Vector, and Combined Responses
\end{enumerate}

\chapter*{LIST OF TABLES}
\addcontentsline{toc}{chapter}{LIST OF TABLES}
\begin{enumerate}[label=Table \arabic*., leftmargin=2.8cm]
\item Comparative Review of Related Research Works
\item Core Software Stack Used in NexRag
\item Major Backend Modules and Responsibilities
\item Conceptual Data Entities and Storage Artefacts
\item API Endpoints and Functional Roles
\item Repository Verification Summary
\item Current Indexed Document Collection
\item Sample Query Routing Outcomes
\item Sample Retrieval Outputs and Relevance Scores
\item Observed Query Log Characteristics
\item Comparative Discussion of Operating Modes
\item Summary of Achievements and Forward Directions
\end{enumerate}

\chapter*{LIST OF ABBREVIATIONS}
\addcontentsline{toc}{chapter}{LIST OF ABBREVIATIONS}
\begin{description}[leftmargin=2.6cm, style=nextline]
\item[AI] Artificial Intelligence
\item[API] Application Programming Interface
\item[BM25] Best Matching 25
\item[B.Tech] Bachelor of Technology
\item[DFD] Data Flow Diagram
\item[FAISS] Facebook AI Similarity Search
\item[KG] Knowledge Graph
\item[KTU] APJ Abdul Kalam Technological University
\item[LLM] Large Language Model
\item[PDF] Portable Document Format
\item[RAG] Retrieval-Augmented Generation
\item[RDF] Resource Description Framework
\item[RRF] Reciprocal Rank Fusion
\item[SPARQL] SPARQL Protocol and RDF Query Language
\item[TTL] Terse RDF Triple Language
\item[UI] User Interface
\end{description}
""".strip() + "\n"


def build_main_tex() -> str:
    return r"""
\documentclass[12pt,a4paper]{report}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{newtxtext,newtxmath}
\usepackage[a4paper,margin=1in]{geometry}
\usepackage{setspace}
\usepackage{graphicx}
\usepackage{array}
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{float}
\usepackage{caption}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{titlesec}
\usepackage[
  fencedCode,
  pipeTables,
  tableCaptions,
  hybrid,
  smartEllipses
]{markdown}

\hypersetup{
  colorlinks=true,
  linkcolor=black,
  urlcolor=blue
}

\setstretch{1.5}
\setlength{\parskip}{0.4em}
\setlength{\parindent}{0pt}

\titleformat{\chapter}[display]
  {\bfseries\centering\Large}
  {CHAPTER \thechapter}
  {1ex}
  {\MakeUppercase}

\titleformat{\section}
  {\bfseries\normalsize}
  {\thesection}
  {1em}
  {}

\titleformat{\subsection}
  {\bfseries\normalsize}
  {\thesubsection}
  {1em}
  {}

\markdownSetup{
  renderers = {
    link = {\href{#2}{#1}},
    headingOne = {\chapter{#1}},
    headingTwo = {\section{#1}},
    headingThree = {\subsection{#1}}
  }
}

\begin{document}

\pagenumbering{roman}
\input{frontmatter}
\clearpage

\pagenumbering{arabic}
\setcounter{page}{1}

\markdownInput{chapters/01_introduction.md}
\markdownInput{chapters/02_literature_review.md}
\markdownInput{chapters/03_proposed_system.md}
\markdownInput{chapters/04_results_and_discussion.md}
\markdownInput{chapters/05_conclusion_and_future_scope.md}

\chapter*{REFERENCES}
\addcontentsline{toc}{chapter}{REFERENCES}
\markdownInput{chapters/06_references_body.md}

\end{document}
""".strip() + "\n"


def build_readme() -> str:
    return """Overleaf-ready project for the NexRag B.Tech report.

Files:
- main.tex
- frontmatter.tex
- chapters/*.md

Recommended Overleaf settings:
- Main document: main.tex
- Compiler: pdfLaTeX

Upload options:
1. Upload the contents of this folder as a new Overleaf project.
2. Or create a blank Overleaf project and push this folder using Overleaf Git integration.
"""


def main() -> None:
    if OVERLEAF_DIR.exists():
        shutil.rmtree(OVERLEAF_DIR)

    CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)

    for file_name in SOURCE_FILES:
        source_path = REPORT_DIR / file_name
        target_path = CHAPTERS_DIR / file_name
        target_path.write_text(preprocess_markdown(source_path.read_text(encoding="utf-8")), encoding="utf-8")

    references_src = REPORT_DIR / "06_references.md"
    references_target = CHAPTERS_DIR / "06_references_body.md"
    references_target.write_text(preprocess_markdown(references_src.read_text(encoding="utf-8")), encoding="utf-8")

    (OVERLEAF_DIR / "frontmatter.tex").write_text(build_frontmatter(), encoding="utf-8")
    (OVERLEAF_DIR / "main.tex").write_text(build_main_tex(), encoding="utf-8")
    (OVERLEAF_DIR / "README.txt").write_text(build_readme(), encoding="utf-8")

    zip_path = REPORT_DIR / "NexRag-overleaf.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OVERLEAF_DIR.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(OVERLEAF_DIR))

    print(f"Overleaf project written to: {OVERLEAF_DIR}")
    print(f"Uploadable zip written to: {zip_path}")


if __name__ == "__main__":
    main()
