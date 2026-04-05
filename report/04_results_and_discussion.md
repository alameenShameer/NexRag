# CHAPTER 4 RESULTS AND DISCUSSION

## 4.1 Introduction

This chapter presents the implementation evidence, observed system behavior, and analytical discussion for the NexRag project. The discussion is intentionally grounded in what could be verified directly from the repository and the local execution environment on **3 April 2026**. This approach is important because a final year report should distinguish clearly between implemented capability, available artefacts, and empirically observed outcomes. Rather than claiming idealized benchmark results that were not actually measured in this session, the chapter focuses on reproducible evidence collected from test scripts, repository artefacts, status endpoints, log files, and sample retrieval outputs.

The resulting discussion combines quantitative and qualitative observations. Quantitative elements include the current number of indexed PDFs and chunks, recorded query latencies from the log file, and observed retrieval relevance scores on sample academic queries. Qualitative analysis includes routing behavior, evidence quality, the role of graph availability, and the interpretability features exposed by the interface. Together, these observations are sufficient to assess whether the implemented system functions coherently as a hybrid academic assistant, even though some runtime services were unavailable during the verification session.

## 4.2 Implementation Environment

The repository structure and local verification commands confirm that NexRag is designed as a full-stack local deployment. The backend is implemented in Python, the frontend uses the Node and Vite ecosystem, and the knowledge graph service depends on a Java runtime for Apache Jena Fuseki. The local environment observed during verification is summarized below.

**Table 4.1 Repository Verification Summary**

| Item | Observed Result | Interpretation |
|---|---|---|
| Python runtime | 3.10.11 | Meets backend requirement |
| Node runtime | v24.11.1 | Satisfies modern frontend tooling |
| Java runtime | OpenJDK 17.0.17 | Compatible with Fuseki requirement |
| API status snapshot | 7 PDFs, 290 chunks, vector ready, local model present | Retrieval pipeline is materially configured |
| Router test | Passed | Rule-based routing is functioning on provided test cases |
| Retrieval test | Passed module load and retrieval interface checks | Dense and reranking models load successfully |
| KG test | Fuseki connection unavailable | Graph implementation exists, service inactive during test |
| Frontend build | Blocked by sandbox `spawn EPERM` | Verification limitation of environment, not a confirmed app defect |

The project README also indicates the intended component stack: Python 3.10+, Node.js 18+, Java 17+, and Ollama installed locally. The versions observed in the current environment are compatible with those requirements. This supports the claim that NexRag was designed for local execution rather than for remote API dependency.

## 4.3 Indexed Knowledge Sources

The document and graph artefacts available in the repository provide direct evidence of the knowledge sources used by the system. The `data/pdfs/` directory contains seven document files relevant to institutional academic information and project writing guidance. The vector store metadata reports 290 indexed chunks, confirming that the document corpus has already been processed into retrievable units.

**Table 4.2 Current Indexed Document Collection**

| Sl. No. | Document Name | Observed Role in the System |
|---|---|---|
| 1 | `2309.17288v3.pdf` | Research or reference material |
| 2 | `Circular_TechFest.pdf` | Institutional circular content |
| 3 | `CSE_Syllabus_S5.pdf` | Course or syllabus information |
| 4 | `Guidelines-Format_for_Project_Report.pdf` | Report writing and formatting guidance |
| 5 | `KTU_Handbook_2024.pdf` | Regulation and academic handbook source |
| 6 | `Seminar Guidelines.pdf` | Seminar process and format instructions |
| 7 | `Tips for good Presentation .pdf` | Presentation support material |

In addition to documents, the repository contains multiple Turtle files such as `mesitam_data.ttl`, `university_faq.ttl`, and `merged_kg.ttl`. Inspection of `mesitam_data.ttl` shows that the graph models departments, faculty members, courses, and regulations. Example graph facts include course entities with codes and credits, faculty designations, department abbreviations, and regulation descriptions. This confirms that the knowledge graph is semantically meaningful and not merely a placeholder dataset.

## 4.4 Functional Verification

Functional verification was carried out using the repository's own test scripts and direct command-line checks. The `tests/test_import.py` script successfully imported the core modules and produced an API status snapshot reporting seven PDFs, 290 chunks, a ready vector store, and the active local model `llama3.2:3b`. This result is significant because it verifies that the backend modules can initialize together and that the vector artefacts already exist in a usable state.

The `tests/test_router.py` script passed all provided cases. Example outputs included mapping "What is Artificial Intelligence?" to `DEFINITION`, "Difference between RAM and ROM" to `COMPARISON`, and "How does the system work?" to `GENERAL`. For the institutional sample queries checked separately during this report preparation, the router labeled "Who teaches Computer Graphics?" as `FACULTY_INFO`, "What is the minimum attendance rule?" as `REGULATION`, and "Explain seminar guidelines" as `DEFINITION`. These observations suggest that the rule-based router functions correctly for the intended coarse categories, although the breadth of tested cases remains limited.

The `tests/test_retrieval.py` script confirmed that the embedding model and cross-encoder reranker load successfully and that the retrieval method returns a list structure as expected. The test's synthetic query about the goal of NexRag produced zero document hits, which is itself informative. It suggests that the indexed corpus is dominated by institutional and guideline documents rather than self-descriptions of the project. In other words, retrieval quality depends strongly on corpus relevance, which is precisely what a domain-bounded academic assistant should reflect.

The `tests/test_kg.py` script, by contrast, reported repeated connection refusal errors when attempting to access the Fuseki endpoint. The API status snapshot also reported `kg_ready: False`. This does not invalidate the graph subsystem, because the graph code and Turtle files are present and well-defined. Instead, it shows that live graph availability depends on the Fuseki service being started separately, and that this dependency was not satisfied during the observed verification session. For a rigorous academic report, this distinction matters.

## 4.5 Sample Routing and Retrieval Outcomes

To understand practical behavior beyond pass-fail testing, a few direct sample retrieval queries were executed against the current vector store. These queries reveal how the system performs on realistic academic prompts.

**Table 4.3 Sample Query Routing Outcomes**

| Query | Detected Intent | Expected Primary Evidence Path |
|---|---|---|
| Who teaches Computer Graphics? | `FACULTY_INFO` | Knowledge graph |
| What is the minimum attendance rule? | `REGULATION` | Vector retrieval, optionally graph if encoded |
| Explain seminar guidelines | `DEFINITION` | Document retrieval |

For the query **"What is the minimum attendance rule?"**, the retrieval engine returned a top result from `KTU_Handbook_2024.pdf` with a normalized relevance score of approximately **0.9663**. The returned text explicitly stated that a student must secure a minimum of 75% attendance to be eligible for the end semester examination and noted condonation conditions. This is a strong retrieval outcome because the passage is directly relevant, policy-specific, and drawn from the correct handbook source.

For the query **"Explain seminar guidelines"**, the retrieval engine returned top passages from `Guidelines-Format_for_Project_Report.pdf` with a score of about **0.9485**, followed by `Seminar Guidelines.pdf` with scores around **0.8702** and **0.6865**. These results are notable for two reasons. First, they show that the retriever can locate broadly relevant procedural and format-based content. Second, they also reveal a subtle ranking challenge: project report formatting guidance and seminar-specific guidance are semantically close in this corpus, so both appear in the result set. This is not necessarily incorrect, but it illustrates why reranking and context selection matter.

**Table 4.4 Sample Retrieval Outputs and Relevance Scores**

| Query | Top Source | Page | Score | Observation |
|---|---|---|---|---|
| What is the minimum attendance rule? | `KTU_Handbook_2024.pdf` | 1 | 0.9663 | Highly relevant policy passage |
| What is the minimum attendance rule? | `KTU_Handbook_2024.pdf` | N/A | 0.2770 | Supportive but secondary passage |
| Explain seminar guidelines | `Guidelines-Format_for_Project_Report.pdf` | 1 | 0.9485 | Strong high-level guidance match |
| Explain seminar guidelines | `Seminar Guidelines.pdf` | 1 | 0.8702 | Direct seminar-specific evidence |
| Explain seminar guidelines | `Seminar Guidelines.pdf` | N/A | 0.6865 | Useful supporting detail on abstract structure |

These retrieval outcomes support the claim that the system is effective for academic document lookup when the query aligns with the indexed content. They also illustrate the value of hybrid retrieval. A purely lexical search might miss semantically relevant handbook text if the wording differs, while a purely dense search could over-associate neighboring academic concepts. The current cascade reduces this risk by combining dense retrieval, BM25, and reranking.

## 4.6 Interface and Workflow Discussion

The repository's frontend code reveals a thoughtfully structured user interaction model. The application includes a welcome state with suggested prompts, a chat panel with streaming markdown rendering, route labels for answer origin, an evidence panel, a system status dashboard, and a knowledge graph editor overlay. Together, these interface choices elevate the project from a backend demonstration to an operational user-facing system.

[Insert Figure 4.1 here: Screenshot of the main NexRag welcome screen showing the brand mark, suggested prompts, left sidebar, and message input bar.]

**Figure 4.1 Main User Interface of the NexRag Frontend**

When an answer is produced, the interface displays not only the content but also a mode label such as "Knowledge Graph", "Vector DB Search", "KG + Vector", or "No Retrieval Hit". This is pedagogically and practically useful. It teaches the user how the system is reasoning at a high level and allows quick detection when the system had weak or absent evidence.

[Insert Figure 4.2 here: Screenshot of an assistant response showing streamed content, route badge, confidence percentage, and source references under the answer bubble.]

**Figure 4.2 Streaming Answer View with Routing and Source Evidence**

The intelligence panel further enhances interpretability by listing retrieved sources with page numbers and relevance bars. If a graph source is present, it is labeled distinctly from document evidence. The same panel also reports system status, including whether the knowledge graph is connected, whether the vector engine is active, and which local language model is configured.

[Insert Figure 4.3 here: Screenshot of the intelligence panel displaying retrieved sources on one tab and PDF, KG, vector, and LLM status on the other tab.]

**Figure 4.3 Intelligence Panel Showing Retrieved Sources and System Status**

The knowledge graph editor is especially important for maintainability. It exposes a graph administration path without requiring direct file editing in the backend workspace. When combined with backend triple-removal inspection, it provides a safer update workflow for structured knowledge.

[Insert Figure 4.4 here: Screenshot of the knowledge graph editor view showing Turtle content editing and save controls.]

**Figure 4.4 Knowledge Graph Editor Interface for Turtle File Update**

From a user experience standpoint, these interface elements contribute strongly to explainability. Many chatbot systems hide all internal evidence and status. NexRag, by contrast, reveals system internals in a controlled and readable form. This is a meaningful strength of the implementation.

## 4.7 Performance Analysis and Log-Based Observations

The repository includes a query history log that provides limited but useful latency observations. Two recorded interactions showed latencies of **13.87 seconds** for the query "What is RAG?" and **11.18 seconds** for the query "Who teaches CS301?". These values should not be interpreted as definitive benchmark results because they represent a very small sample and likely include local model generation time, retrieval time, and whatever runtime conditions existed at the time of logging. However, they do indicate that the system operates in a response window consistent with local RAG pipelines using CPU or modest local hardware.

**Table 4.5 Observed Query Log Characteristics**

| Logged Query | Intent | Latency (s) | Observed Response Character |
|---|---|---|---|
| What is RAG? | `DEFINITION` | 13.87 | Explanatory answer grounded in retrieved context |
| Who teaches CS301? | `GENERAL` | 11.18 | Fallback uncertainty due missing supporting evidence at that time |

The latency observations highlight an important reality of local-first systems: response quality and data control improve, but the speed may be lower than highly optimized cloud services. For an academic assistant, this trade-off is often acceptable, especially if transparency and privacy are prioritized. The use of streaming responses also helps reduce perceived delay because users begin receiving output before the full answer is complete.

The retrieval engine itself appears operationally strong within the available corpus. The very high top score for the attendance rule query suggests that the reranking pipeline is able to identify clearly relevant policy passages. At the same time, the result mix for seminar guidance indicates that semantically adjacent documents can compete for top positions, which is typical in academic corpora where multiple documents discuss related formats and expectations. This indicates that the current retrieval pipeline is effective but would still benefit from richer document categorization, better query-aware filtering, or future rank fusion strategies.

[Insert Figure 4.5 here: Screenshot or generated result card showing the attendance-rule retrieval output with the KTU handbook source and relevance score.]

**Figure 4.5 Retrieval Output for an Attendance Rule Query**

[Insert Figure 4.6 here: Screenshot or generated result card showing the seminar-guideline retrieval output with multiple ranked supporting documents.]

**Figure 4.6 Retrieval Output for a Seminar Guideline Query**

## 4.8 Comparative Discussion of Operating Modes

The system behavior can be understood by comparing its four practical operating modes: knowledge graph mode, vector search mode, combined mode, and no-hit fallback mode. Each mode corresponds to a different evidence availability condition and has distinct strengths.

**Table 4.6 Comparative Discussion of Operating Modes**

| Mode | Trigger Condition | Strength | Limitation |
|---|---|---|---|
| Knowledge Graph Mode | Structured fact found, vector context unnecessary or unavailable | Precise entity-level answers | Limited descriptive detail |
| Vector Search Mode | Document evidence found without graph match | Strong explanatory answers from PDFs | May miss direct institutional relations |
| Combined Mode | Both graph and document evidence are strong | Best balance of fact and explanation | Depends on quality of both subsystems |
| No Retrieval Hit | No supporting evidence found | Honest uncertainty handling | User receives no substantive answer |

In theoretical terms, combined mode is the most powerful because it can present a concise graph fact and then support it with document-backed explanation. However, this mode also depends on both the graph service and retrieval engine being available. During the verification session used for this report, the graph service was offline, so practical behavior was dominated by vector retrieval and routing logic. This does not reduce the architectural value of combined mode, but it does limit what could be demonstrated live.

[Insert Figure 4.7 here: A comparative visual summarizing KG mode, vector mode, combined mode, and no-hit mode with their input evidence and output characteristics.]

**Figure 4.7 Comparative Mode Analysis of KG, Vector, and Combined Responses**

## 4.9 Limitations of the Current Evaluation

The current evaluation has several important limitations that should be acknowledged openly. First, the knowledge graph service was not active during the verification session, so end-to-end demonstration of graph-backed answering was not possible at runtime, even though the graph code and data are present. Second, the frontend production build check was blocked by sandbox restrictions producing a `spawn EPERM` error, which prevented a clean build verification within this environment. Third, the available query log contains only a small number of historical examples and therefore cannot support statistically meaningful latency analysis.

Fourth, although the repository contains a RAGAs evaluation script and golden datasets, a complete metric-based evaluation was not executed in this session because it depends on active local models and services. Fifth, the router tests cover only a small set of representative cases and do not constitute exhaustive intent classification validation. Finally, the current document corpus is relatively small, which is useful for a bounded prototype but does not yet test the scalability of retrieval under substantially larger institutional archives.

Despite these limitations, the observed evidence is still sufficient to support the main claim of the project: NexRag is a coherent hybrid academic assistant with working document retrieval, clear modular architecture, transparent interface design, and an implemented pathway for knowledge graph integration. The evaluation therefore supports feasibility and functional readiness while also identifying the next steps required for a more rigorous deployment-grade assessment.
