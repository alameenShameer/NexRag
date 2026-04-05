# COVER PAGE

**NEXRAG: A LOCAL-FIRST HYBRID KNOWLEDGE GRAPH AND RETRIEVAL-AUGMENTED GENERATION ACADEMIC ASSISTANT FOR ACADEMIC QUERY ANSWERING**

A project report submitted in partial fulfillment of the requirements for the award of the degree of Bachelor of Technology in Computer Science and Engineering.

Submitted by  
`[Student Name]`  
`[Register Number]`

Under the guidance of  
`[Project Guide Name]`  
`[Designation]`

Department of Computer Science and Engineering  
MES Institute of Technology and Management  
Chathannoor, Kollam, Kerala  
`[Affiliated University Name]`  
`[Month Year]`

---

# CERTIFICATE

This is to certify that the report entitled **"NexRag: A Local-First Hybrid Knowledge Graph and Retrieval-Augmented Generation Academic Assistant for Academic Query Answering"** is a bonafide record of the project work carried out by **`[Student Name]`**, bearing register number **`[Register Number]`**, in the Department of Computer Science and Engineering, MES Institute of Technology and Management, during the academic year **`[Academic Year]`**, in partial fulfillment of the requirements for the award of the degree of Bachelor of Technology in Computer Science and Engineering. This work has been carried out under my supervision and guidance and, to the best of my knowledge, has not formed the basis for the award of any degree, diploma, associateship, fellowship, or any other similar title in any university or institution.

The project report has been examined and approved by the undersigned as fulfilling the academic and technical standards expected for a final year B.Tech project. The system presented in the report demonstrates the design and development of a local-first academic assistant that integrates structured knowledge graph querying, unstructured document retrieval, and local language model based response generation for answering institutional academic queries in a grounded and transparent manner.

Guide Signature: ____________________  
Name: `[Project Guide Name]`  
Designation: `[Guide Designation]`

Head of Department Signature: ____________________  
Name: `[Head of Department Name]`  
Department of Computer Science and Engineering

External Examiner Signature: ____________________

Place: Chathannoor  
Date: `[Date]`

---

# DECLARATION

I hereby declare that the project report entitled **"NexRag: A Local-First Hybrid Knowledge Graph and Retrieval-Augmented Generation Academic Assistant for Academic Query Answering"** is the original work carried out by me during the academic year **`[Academic Year]`** under the guidance of **`[Project Guide Name]`**, Department of Computer Science and Engineering, MES Institute of Technology and Management. I further declare that this report has not been submitted, either in full or in part, to any other university or institution for the award of any degree or diploma.

I affirm that all sources of information, ideas, methods, and prior research used in preparing this report have been duly acknowledged in the text and listed in the references section in Harvard style. Wherever repository implementation details are discussed, they are based on the current codebase and locally available project artifacts. Any placeholders that remain in the front matter are intentionally left for institutional completion and do not alter the originality of the technical work described in the subsequent chapters.

Signature of Student: ____________________  
Name: `[Student Name]`  
Register Number: `[Register Number]`  
Date: `[Date]`

---

# ACKNOWLEDGEMENT

The successful completion of this project report would not have been possible without the support, encouragement, and guidance of many individuals and resources that contributed to the development of both the software system and this academic document. I express my sincere gratitude to the Department of Computer Science and Engineering, MES Institute of Technology and Management, for providing an environment that encourages experimentation, problem solving, and independent technical exploration. The academic structure, laboratory support, and continuous feedback received throughout the project period played an important role in transforming the initial idea into a coherent engineering solution.

I place on record my heartfelt thanks to **`[Project Guide Name]`**, whose supervision, timely suggestions, and constructive criticism helped shape the project at every stage. The guidance provided in problem definition, system decomposition, evaluation planning, and report organization was invaluable in ensuring that the work remained technically rigorous and academically meaningful. I also extend my gratitude to the Head of the Department, faculty members, and project coordinators for their encouragement and for creating opportunities to review the work critically during its progression.

I gratefully acknowledge the developers and research communities behind the open technical resources that enabled this work, including the authors of foundational research in retrieval-augmented generation, dense passage retrieval, sentence embeddings, neural reranking, and knowledge graph technologies. The implementation also benefited from open software ecosystems such as FastAPI, React, Apache Jena Fuseki, FAISS, Sentence Transformers, and Ollama, each of which contributed a practical capability required to build a local-first academic assistant. Their availability made it possible to study, prototype, and integrate modern information access techniques into a single system tailored for educational use.

Finally, I would like to thank my family, friends, and peers for their encouragement and patience throughout the course of this work. Their support helped sustain motivation during experimentation, debugging, documentation, and review. I remain deeply grateful to everyone who, directly or indirectly, contributed to the successful completion of this project report.

---

# ABSTRACT

Academic institutions increasingly require intelligent information access systems that can answer student and faculty queries accurately, transparently, and without dependence on proprietary cloud infrastructure. Conventional chatbots often struggle in such settings because they either rely solely on unstructured document retrieval, which may miss explicit institutional relationships, or depend exclusively on structured databases, which cannot capture the rich explanatory detail contained in handbooks, circulars, seminar guidelines, and syllabus documents. This project presents **NexRag**, a local-first hybrid academic assistant that combines a knowledge graph, a document retrieval pipeline, and a locally hosted language model to answer academic queries in a grounded and explainable manner.

The proposed system integrates a FastAPI backend, a React and Vite frontend, Apache Jena Fuseki for RDF-based knowledge graph querying, FAISS for dense vector indexing, BM25 for sparse lexical matching, and a cross-encoder reranker for relevance refinement. User queries are first routed through an intent classifier, after which entity-centric questions are forwarded to the knowledge graph, document-centric questions are processed through the retrieval engine, and suitable cases are answered using a combined mode that merges graph facts with supporting document evidence. A local language model served through Ollama generates the final answer, while preserving a grounded response strategy that prioritizes retrieved evidence and explicitly acknowledges uncertainty when evidence is insufficient.

The repository state used for this report demonstrates a functioning pipeline with seven indexed PDF documents and 290 vectorized text chunks, alongside knowledge graph source files representing departments, faculty, courses, and regulations. Verification performed on 3 April 2026 confirmed successful module imports, correct intent classification on the available router test cases, successful loading of the embedding and reranking models, and meaningful retrieval behavior for academic queries such as attendance rules and seminar guidelines. The knowledge graph service itself was not active during the observed verification session, which is documented as an operational dependency rather than hidden as a limitation.

The project shows that a hybrid local-first design can improve the quality and trustworthiness of academic question answering by combining structured and unstructured knowledge sources, exposing evidence to the user, and avoiding unnecessary cloud dependence. The resulting system is especially relevant to institutional environments that require controllable deployment, explainability, and extensibility.

**Keywords:** retrieval-augmented generation, knowledge graph, academic assistant, FAISS, BM25, reranking, FastAPI, React, Fuseki, local LLM

---

# TABLE OF CONTENTS

The final page numbers should be auto-updated after exporting this draft to the required word-processed format with Roman and Arabic pagination enabled.

Cover Page  
Certificate  
Declaration  
Acknowledgement  
Abstract  
List of Figures  
List of Tables  
List of Abbreviations  

CHAPTER 1 INTRODUCTION  
1.1 Overview of the Project Domain  
1.2 Background and Importance  
1.3 Motivation  
1.4 Problem Statement  
1.5 Challenges in Existing Systems  
1.6 Objectives of the Project  
1.7 Scope and Delimitations  
1.8 Organization of the Report  

CHAPTER 2 LITERATURE REVIEW  
2.1 Introduction  
2.2 Review of Foundational and Related Works  
2.3 Comparative Analysis of Existing Approaches  
2.4 Research Gaps Identified  

CHAPTER 3 PROPOSED SYSTEM  
3.1 System Overview  
3.2 System Architecture  
3.3 Module Description  
3.4 Algorithms Used  
3.5 System Design  
3.6 Advantages of the Proposed System  
3.7 Applications  

CHAPTER 4 RESULTS AND DISCUSSION  
4.1 Introduction  
4.2 Implementation Environment  
4.3 Functional Verification  
4.4 Retrieval and Response Analysis  
4.5 Interface and Workflow Discussion  
4.6 Comparative Discussion  
4.7 Limitations of the Current Evaluation  

CHAPTER 5 CONCLUSION AND FUTURE SCOPE  
5.1 Summary of Work  
5.2 Key Achievements  
5.3 Limitations  
5.4 Future Scope  
5.5 Closing Remarks  

REFERENCES

---

# LIST OF FIGURES

Figure 3.1 High-Level Architecture of NexRag  
Figure 3.2 End-to-End Query Processing Flow  
Figure 3.3 Knowledge Graph Maintenance and Validation Workflow  
Figure 3.4 Data Flow Diagram for the Proposed System  
Figure 4.1 Main User Interface of the NexRag Frontend  
Figure 4.2 Streaming Answer View with Routing and Source Evidence  
Figure 4.3 Intelligence Panel Showing Retrieved Sources and System Status  
Figure 4.4 Knowledge Graph Editor Interface for Turtle File Update  
Figure 4.5 Retrieval Output for an Attendance Rule Query  
Figure 4.6 Retrieval Output for a Seminar Guideline Query  
Figure 4.7 Comparative Mode Analysis of KG, Vector, and Combined Responses

---

# LIST OF TABLES

Table 2.1 Comparative Review of Related Research Works  
Table 3.1 Core Software Stack Used in NexRag  
Table 3.2 Major Backend Modules and Responsibilities  
Table 3.3 API Endpoints and Functional Roles  
Table 3.4 Conceptual Data Entities and Storage Artefacts  
Table 4.1 Repository Verification Summary  
Table 4.2 Current Indexed Document Collection  
Table 4.3 Sample Query Routing Outcomes  
Table 4.4 Sample Retrieval Outputs and Relevance Scores  
Table 4.5 Observed Query Log Characteristics  
Table 4.6 Comparative Discussion of Operating Modes  
Table 5.1 Summary of Achievements and Forward Directions

---

# LIST OF ABBREVIATIONS

AI - Artificial Intelligence  
API - Application Programming Interface  
BM25 - Best Matching 25  
B.Tech - Bachelor of Technology  
CSV - Comma Separated Values  
DFD - Data Flow Diagram  
FAISS - Facebook AI Similarity Search  
FAQ - Frequently Asked Questions  
HTTP - Hypertext Transfer Protocol  
IEC - Internal Evaluation Committee  
JSON - JavaScript Object Notation  
KG - Knowledge Graph  
KNN - k-Nearest Neighbour  
KTU - APJ Abdul Kalam Technological University  
LLM - Large Language Model  
PDF - Portable Document Format  
RAG - Retrieval-Augmented Generation  
RDF - Resource Description Framework  
RRF - Reciprocal Rank Fusion  
SPARQL - SPARQL Protocol and RDF Query Language  
TTL - Terse RDF Triple Language  
UI - User Interface  
URL - Uniform Resource Locator
