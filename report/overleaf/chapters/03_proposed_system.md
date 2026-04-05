# PROPOSED SYSTEM

## System Overview

The proposed system, NexRag, is a local-first hybrid academic assistant designed to answer institutional academic queries by integrating structured knowledge graph lookups, unstructured document retrieval, and local language model based answer generation. The system is intended for domains where both factual precision and explanatory depth are necessary. Within an academic institution, users do not ask only one kind of question. Some questions seek direct factual relations, such as identifying the faculty associated with a course or determining the department of a staff member. Other questions are more descriptive and depend on narrative information embedded in documents, such as seminar formatting instructions, report writing requirements, attendance rules, or handbook explanations. The proposed system therefore avoids treating all questions as uniform and instead uses a routing-aware architecture.

At a high level, NexRag performs five major functions. First, it receives user queries through a web-based frontend and forwards them to a backend API. Second, it classifies the query intent using a lightweight router. Third, based on the query type and the availability of evidence, it queries either the knowledge graph, the vector retrieval engine, or both. Fourth, it composes the retrieved evidence into a grounded context and passes that context to a local language model served through Ollama. Fifth, it returns the answer together with auxiliary evidence such as routing mode, source snippets, and a confidence estimate. This combination allows the system to provide both direct and explainable responses.

The current repository implementation confirms that the system is constructed as a modular pipeline rather than a monolithic script. The `api.py` module acts as the orchestration layer, `router.py` handles intent classification, `kg.py` handles SPARQL-based graph querying and Turtle validation logic, `rag.py` manages PDF extraction, chunking, indexing, and retrieval, and `llm.py` generates the final response using a local model. On the frontend, React components display the conversation, source evidence, system status, and knowledge graph editing view. This modularity is important from a software engineering perspective because it separates concerns and allows individual subsystems to be maintained, tested, and extended independently.

The system also emphasizes transparency and operational practicality. The user interface distinguishes between knowledge graph mode, vector search mode, combined mode, and no-hit fallback mode. The backend computes a confidence score based on available evidence and exposes retrieved snippets and graph sources. The frontend uses an intelligence panel to display document sources, graph evidence, and runtime health indicators such as vector readiness, graph connectivity, and local model identity. Such design choices are essential in academic contexts because users should be able to understand not only the answer itself but also where the answer came from and how reliable the system considers it.

The repository state examined for this report indicates that the document corpus currently contains seven PDF files and 290 indexed chunks. The graph layer is built from Turtle sources representing departments, faculty, courses, and regulations. These implementation details confirm that NexRag is not a theoretical architecture but a concrete working system with real ingestion, retrieval, graph modeling, and interface features. The proposed system is therefore best understood as a hybrid, modular, evidence-aware academic information assistant optimized for local deployment.

**Table 3.1 Core Software Stack Used in NexRag**

| Layer | Technology | Role in the System |
|---|---|---|
| Frontend | React + Vite + TypeScript | Chat interface, status view, source panel, KG editor |
| Backend API | FastAPI | Request handling, orchestration, upload, history, KG file services |
| Dense Retrieval | Sentence Transformers + FAISS | Embedding generation and vector indexing |
| Sparse Retrieval | BM25 (`rank_bm25`) | Lexical candidate search |
| Reranking | CrossEncoder (`ms-marco-MiniLM-L-6-v2`) | Fine-grained relevance ordering |
| KG Storage and Query | RDF/Turtle + Apache Jena Fuseki + SPARQL | Structured entity and relationship retrieval |
| Generation | Ollama + `llama3.2:3b` | Local grounded answer generation |
| Utilities | `pdfplumber`, `langchain-text-splitters`, `pandas` | PDF text extraction, chunking, logging and history |

## System Architecture

The architecture of NexRag follows a layered request-processing model in which each layer performs a narrow but essential role. The design begins with a user-facing frontend that collects natural language questions and presents streaming responses. These requests are sent to a FastAPI backend over HTTP. Inside the backend, a controller builds a chat payload, invokes a rule-based router, optionally queries the knowledge graph, retrieves document chunks from the vector pipeline, filters and ranks evidence, and finally invokes the local LLM for grounded answer generation. The resulting response is then enriched with routing metadata, evidence references, confidence values, and conversation history logging before being returned to the user interface.

This architecture can be interpreted as a hybrid evidence orchestration system. The key design principle is that evidence is not sourced from a single datastore. Instead, the system treats structured graph data and unstructured PDF content as complementary knowledge reservoirs. The graph is authoritative for explicit institutional relations, while the document store is authoritative for descriptive procedural content. The architecture is therefore deliberately asymmetric: it does not simply retrieve from both sources all the time, but attempts to decide when each source is useful and when combining them is justified.

\begin{center}
\fbox{\parbox{0.92\textwidth}{\textbf{Figure Placeholder:} A block diagram showing the user interacting with the React frontend, the frontend communicating with the FastAPI API, the API invoking the router, the knowledge graph module, the RAG retrieval module, and the local LLM, with logging and status monitoring as side services.}}
\end{center}


**Figure 3.1 High-Level Architecture of NexRag**

At the frontend layer, the system provides three visible interaction surfaces. The main chat panel accepts user queries and renders responses with markdown formatting. The intelligence panel shows retrieved sources and system status. The knowledge graph editor allows authorized editing of Turtle source files. This frontend division reflects an important usability decision: conversation, evidence, and system administration are related but distinct user concerns.

At the backend layer, FastAPI provides several endpoints for status checks, document upload and deletion, chat interaction, history retrieval, graph file browsing, graph saving with validation, and graph restart support. The backend thus functions as the central mediator of all system state transitions. It is not limited to inference alone; it also exposes operational workflows for document management and graph maintenance. This is consistent with the requirements of a maintainable academic system in which knowledge sources evolve over time.

The routing layer is intentionally lightweight. Instead of invoking a learned classifier, `router.py` uses keyword-based heuristics to assign intents such as `FACULTY_INFO`, `COURSE_INFO`, `REGULATION`, `DEFINITION`, `COMPARISON`, and `GENERAL`. While simple, this approach has practical value in a bounded domain where query patterns are partially predictable. A router of this kind avoids the overhead of model training and is easy to modify when new keywords or institutional categories arise. The trade-off is reduced flexibility for ambiguous or linguistically unexpected queries, which is discussed later as a limitation and future enhancement opportunity.

The knowledge graph layer is centered around RDF/Turtle data and SPARQL queries served through a local Apache Jena Fuseki instance (Apache Software Foundation, 2026). The `kg.py` module constructs SPARQL patterns based on extracted search terms and returns human-readable formatted answers containing details such as designation, department, taught courses, or regulation descriptions. The graph layer also includes a safety-oriented update inspection routine that compares existing and new Turtle content and warns when edits remove triples. This is an important architectural choice because graph maintenance is treated not as an afterthought but as a controlled workflow with validation.

The document retrieval layer is implemented in `rag.py`. Documents are parsed using `pdfplumber`, split into chunks through a recursive character splitter, converted into dense embeddings using the `all-MiniLM-L6-v2` model, indexed in a FAISS vector store, and mirrored in metadata files that preserve source name, page markers, and category. Alongside dense indexing, BM25 is maintained over preprocessed chunk text for sparse lexical retrieval. Candidate passages from dense and sparse paths are then reranked using a cross-encoder model, and scores are normalized through a sigmoid function before filtering and final top-k selection. This layered retrieval architecture balances recall, lexical precision, and ranking quality.

The generation layer is implemented in `llm.py`. It constructs a system prompt instructing the local model to answer using the provided context, prefer the knowledge graph and document evidence when available, and explicitly acknowledge when the answer is unknown. The project uses `llama3.2:3b` through Ollama, reflecting the goal of local inference rather than dependency on cloud APIs. The final response is streamed back to the frontend where partial content is displayed incrementally. This improves perceived responsiveness and creates a more interactive user experience.

Finally, the system includes supporting layers for logging, health monitoring, and history. Query-answer pairs are logged to a CSV file, status endpoints expose counts for PDFs and vector chunks, and history endpoints allow recent interaction retrieval. These additions may appear secondary when viewed purely from an algorithmic perspective, but they are essential for a system intended to be operated and evaluated in practice.

\begin{center}
\fbox{\parbox{0.92\textwidth}{\textbf{Figure Placeholder:} A flow diagram showing query submission, intent detection, optional knowledge graph query, vector retrieval, context composition, local LLM generation, response formatting, and evidence display.}}
\end{center}


**Figure 3.2 End-to-End Query Processing Flow**

### Architectural Rationale

The selected architecture is motivated by the need to balance accuracy, maintainability, local deployability, and user trust. A pure graph architecture would fail to explain detailed procedural content from PDFs. A pure vector RAG system would struggle to answer highly relational questions with the precision needed for faculty-course queries. A pure LLM chatbot would risk unsupported generation. The hybrid architecture therefore emerges as a rational integration of complementary subsystems rather than a stacked collection of unrelated technologies.

The use of modular Python files, persisted vector artefacts, explicit graph files, and a decoupled web frontend also improves project maintainability. Each module can be developed or replaced with minimal disruption to the others. For example, the router may later be replaced by a learned classifier, or the local language model may be upgraded, without redesigning the entire system. Similarly, graph schemas can be expanded as institutional coverage grows. This extensibility is one of the strongest characteristics of the proposed architecture.

## Module Description

The system is organized into clearly identifiable modules, each responsible for a specific part of the overall workflow. Describing these modules individually is important because the functionality of NexRag arises from the coordination among them rather than from any single algorithm.

**Table 3.2 Major Backend Modules and Responsibilities**

| Module | Primary File | Main Responsibility |
|---|---|---|
| API orchestration | `api.py` | Central request processing and service endpoints |
| Query routing | `router.py` | Intent classification for incoming queries |
| Knowledge graph services | `kg.py` | SPARQL querying, search term extraction, TTL validation |
| Retrieval engine | `rag.py` | PDF extraction, chunking, embedding, indexing, retrieval |
| Generation engine | `llm.py` | Local LLM prompt construction and response streaming |
| Logging | `logger.py` | Query and answer history persistence |
| Graph merge support | `merge_kg.py` | Merging TTL files for Fuseki loading |

### User Interface Module

The frontend is the first active module from the user perspective. Implemented using React and Vite, it provides the interactive chat environment, including suggested prompts, streaming answer rendering, mode indicators, confidence display, and source listing. The frontend does more than merely present text responses. It interprets backend metadata and maps system outputs into user-comprehensible interface signals such as "Knowledge Graph", "Vector DB Search", "KG + Vector", and fallback status labels. This design contributes to user trust because the system explicitly communicates which retrieval mode was used for a given answer.

Another significant part of the interface is the intelligence panel. This panel lists retrieved document snippets, knowledge graph evidence, and system health metrics such as the number of indexed PDFs, vector chunk count, graph connectivity state, and active local model. In effect, the panel converts otherwise hidden infrastructure details into human-readable evidence traces. For a project aimed at explainable academic assistance, this is a strong design decision because it makes grounding visible instead of implicit.

The knowledge graph editor is also part of the user interface layer. It allows the viewing and editing of Turtle source files through the frontend, after which the backend validates and stores the update. Such administrative support indicates that the system is designed for iterative use rather than one-time demonstration. It also reduces the barrier to maintaining institutional knowledge because graph edits can be managed through the same application ecosystem rather than through isolated backend scripts.

### API Orchestration Module

The API module in `api.py` acts as the backbone of the system. It exposes endpoints for status retrieval, document management, history access, knowledge graph file operations, and both standard and streaming chat endpoints. More importantly, it contains the orchestration logic that decides how evidence from multiple subsystems is combined into a final response. The `build_chat_payload` routine is central here, assembling routing results, graph outputs, vector hits, evidence snippets, and confidence estimates into a single response payload.

This module is also responsible for operational safety and data hygiene. It performs file name validation for document deletion, handles exceptions when services are unavailable, rebuilds the vector store after file deletion, and performs controlled graph updates. By housing these concerns in the API layer, the system avoids pushing low-level operations into the interface or duplicating logic across modules. This is consistent with sound backend design, where orchestration, validation, and response formatting are centralized.

### Query Routing Module

The query routing module is implemented in `router.py` and determines the first high-level interpretation of a user question. It assigns intents such as `FACULTY_INFO`, `COURSE_INFO`, `REGULATION`, `DEFINITION`, `COMPARISON`, and `GENERAL` based on keyword presence. It also includes a spelling-correction utility for selected known terms. Even though the router is simple, its role is strategic because it influences whether the system attempts a graph lookup, a document retrieval, or both.

The choice of a rule-based router reflects the bounded nature of the academic domain. In such settings, many high-frequency query patterns are predictable, and rule-based classification can offer acceptable precision with minimal computational cost. The router also improves interpretability because its behavior can be understood and modified directly from source code. However, this simplicity introduces a limitation: it may struggle with uncommon phrasing, implicit questions, or cases where multiple intents are present in the same utterance. The current project accepts this trade-off for the sake of lightweight deployment.

### Knowledge Graph Module

The knowledge graph module in `kg.py` is responsible for structured academic facts. It communicates with the Fuseki SPARQL endpoint, extracts search terms from the user query, constructs graph queries, and formats the returned bindings into a readable response. The module handles special cases such as "who teaches" queries by first identifying a course and then querying for linked faculty members. More general entity queries attempt to match names, codes, and abbreviations against graph entities and gather direct and inverse properties for richer responses.

One of the notable aspects of the module is its effort to return human-friendly answers rather than raw triples. Property names are converted into readable labels such as "Designation" or "Department", and inverse relations are rendered into phrases such as "Taught by". This shows that the graph module is not used merely as a datastore, but as a structured evidence engine tailored for direct interaction. The inclusion of `inspect_ttl_update` further shows that the module is designed with maintainability in mind; it can detect removed triples before accepting edits, which reduces accidental graph corruption.

### Retrieval Engine Module

The retrieval module in `rag.py` is one of the most technically rich parts of the system. It begins by extracting text from PDFs using `pdfplumber`, preserving page markers so that retrieved snippets can later be traced back to approximate source pages. The extracted text is split into chunks using a recursive character text splitter with configurable chunk size and overlap. Each chunk is stored with source metadata, page information, and category labels. These preprocessing steps ensure that the downstream retriever works over manageable units rather than entire documents.

After chunking, the module computes dense embeddings using the `all-MiniLM-L6-v2` sentence-transformer model. The embeddings are inserted into a FAISS `IndexFlatL2` index and persisted to disk along with chunk metadata. In parallel, the module builds a BM25 index over tokenized chunk text. During retrieval, it generates a dense query embedding, retrieves a larger initial candidate set from FAISS, adds BM25 candidates, merges them into a unique candidate pool, and then reranks the results using a cross-encoder. The final ranking scores are normalized through a sigmoid function and filtered by a minimum score threshold before the top-k results are returned.

This module demonstrates a mature retrieval design because it combines semantic matching, lexical matching, and neural relevance estimation in a cascade. It is also operationally useful because the vector store can be rebuilt from a directory of PDFs, individual uploads can be indexed incrementally, and store statistics can be queried by the rest of the system. The presence of on-disk vector artefacts in the repository confirms that this part of the system is actively used rather than merely planned.

### Local Language Model Module

The generation module in `llm.py` is responsible for converting the gathered evidence into a coherent final answer. It constructs a detailed system prompt that instructs the model to answer using the provided context, to reuse relevant facts from conversation history when appropriate, and to state "I don't know" when the context does not support an answer. This prompt design is important because local LLMs, like remote ones, still require explicit behavioral guidance to remain grounded.

The model currently used is `llama3.2:3b` served through Ollama (Ollama, 2026). The choice of a relatively lightweight local model reflects the local-first goal of the system. The backend supports both streaming and non-streaming generation, and the frontend is designed to render streaming tokens progressively. This improves the interactivity of the system and makes the user experience feel more responsive even when retrieval and generation take noticeable time.

### Logging, History, and Maintenance Module

The system includes utility support for logging and maintenance that is easy to overlook but important in real deployments. Logged query history is stored as a CSV file and exposed through an API endpoint so that recent question-answer interactions can be revisited in the interface. The project also includes health-check scripts, graph merge utilities, and a startup batch file that launches the main services. These operational details strengthen the project's engineering maturity.

Maintenance is further supported by document upload and deletion endpoints, graph file browsing and saving, and optional knowledge graph restart logic. Taken together, these capabilities turn the system into a living application rather than a static prototype. This is particularly relevant in an institutional setting where the software must continue to evolve as documents and graph facts change.

## Algorithms Used

The proposed system uses a combination of retrieval, ranking, and validation algorithms rather than a single end-to-end model. This section explains the major computational techniques employed in NexRag and clarifies where each one fits into the pipeline.

### Embedding Technique

The dense retrieval stage uses a sentence-transformer model, specifically `all-MiniLM-L6-v2`, to convert text chunks and user queries into fixed-length vector representations. Embeddings are compact numerical vectors that capture semantic content, allowing conceptually similar texts to be compared even when they do not share the same surface words. In practical terms, this enables the system to retrieve a handbook passage about examination eligibility even when the user's wording differs from the exact wording in the source document.

The embedding process can be represented conceptually as follows:

\begin{equation}
\mathbf{e} = f(t)
\tag{3.1}
\end{equation}


where `t` denotes an input text segment and `f` denotes the embedding model. The output `e` is a dense vector in a learned semantic space. In NexRag, every PDF chunk is embedded during indexing, and every user query is embedded during retrieval. These vectors are then compared through the dense search engine.

The main advantages of embedding-based retrieval are semantic generalization and robustness to paraphrase. However, embeddings can also smooth over distinctions that matter in formal documents. Therefore, the system supplements dense retrieval with lexical BM25 ranking and neural reranking.

### Dense Vector Search

The repository uses FAISS `IndexFlatL2` for first-stage dense retrieval. This index performs nearest-neighbour search using Euclidean distance over embedding vectors. For a given query vector, the retriever identifies the closest chunk vectors in the index. Because the system stores metadata separately, each FAISS result can be mapped back to its source text, source file, and page identifier.

The dense ranking objective can be represented as:

\begin{equation}
d(q, x) = \lVert q - x \rVert_2
\tag{3.2}
\end{equation}


where `q` is the query embedding and `x` is a candidate chunk embedding. Smaller values indicate greater similarity in the vector space used by FAISS. Although the user specification for this report explicitly mentions cosine similarity, the current repository implementation uses L2 distance for first-stage vector search. Cosine similarity remains relevant conceptually because it is a widely used similarity measure for embedding spaces and may be adopted in future normalized-index variants of the system.

### Cosine Similarity as a Standard Semantic Measure

Cosine similarity is frequently used to compare embeddings by measuring the angle between two vectors rather than their absolute magnitude. It is included in this report because it is a standard theoretical tool for semantic retrieval and is useful for explaining similarity-based document search in general.

\begin{equation}
\cos(q, x) = \frac{q \cdot x}{\lVert q \rVert \lVert x \rVert}
\tag{3.3}
\end{equation}


If the embeddings are normalized, cosine similarity and Euclidean distance often produce related rankings, but they are not identical under all conditions. In NexRag, cosine similarity is best interpreted as a conceptual reference for semantic relevance, while the deployed first-stage index uses L2 distance and the final ranking is determined by the cross-encoder reranker.

### BM25 Sparse Retrieval

To complement dense retrieval, NexRag uses BM25 over tokenized chunk text. BM25 captures lexical relevance by considering term frequency, inverse document frequency, and document length normalization. This is important in academic settings because terms such as course codes, formal rule names, or technical keywords may need explicit matching.

The BM25 scoring function can be expressed as:

\begin{equation}
\begin{aligned}
\mathrm{BM25}(D, Q) &= \sum \mathrm{IDF}(q_i) \cdot \\
&\frac{f(q_i, D)\,(k_1 + 1)}{f(q_i, D) + k_1\left(1 - b + b\frac{|D|}{\mathrm{avgdl}}\right)}
\end{aligned}
\tag{3.4}
\end{equation}


where `D` is a document or chunk, `Q` is the query, `f(qi, D)` is the term frequency of query term `qi` in `D`, `|D|` is the document length, and `avgdl` is the average document length in the collection. In simple terms, BM25 rewards chunks containing important query terms while controlling for document length effects. Within NexRag, BM25 contributes candidate passages that might be missed by purely semantic retrieval.

### Cross-Encoder Reranking

After collecting candidates from FAISS and BM25, the system applies a cross-encoder reranker. Unlike dual-encoder retrieval, which embeds query and passage separately, a cross-encoder evaluates the query and passage jointly and predicts a relevance score. This makes it more computationally expensive but substantially more precise for short candidate lists.

The raw cross-encoder score is normalized in the repository using the sigmoid function:

\begin{equation}
\sigma(z) = \frac{1}{1 + e^{-z}}
\tag{3.5}
\end{equation}


This converts raw logits into scores between 0 and 1, which are then used as the retrieval confidence values reported in the result payload. The system sorts the candidates by this normalized score and filters out items below a configurable threshold. As a result, the reranker determines the practical relevance ordering seen by the user.

### Confidence Computation

The backend computes an interpretable confidence percentage based on the available evidence. If both graph and vector evidence are present, the confidence score is blended from a graph evidence score, a vector evidence score, and a corroboration bonus. If only one source is available, the corresponding evidence score is used. This confidence calculation is heuristic rather than statistically calibrated, but it offers a meaningful user-facing signal about evidence strength.

The confidence design is important because academic assistants should communicate uncertainty. Even a good retrieval result does not guarantee that the final answer is comprehensive, and a graph fact may be incomplete if the graph has not been fully maintained. A heuristic confidence layer is therefore preferable to silent overconfidence, even if it remains an area for future methodological improvement.

### Pseudo-code for Major Algorithms

The following pseudo-code represents the core computational procedures of NexRag.

**Algorithm 3.1 PDF Indexing and Vector Store Update**

```text
Input: PDF file path p, category c
Output: Number of indexed chunks

1. Extract text T from PDF p page by page
2. Split T into overlapping chunks C
3. For each chunk in C:
4.     Attach metadata: source name, page number, category
5. Encode all chunk texts into embedding vectors E
6. Add E to FAISS index
7. Append metadata records to chunk store
8. Rebuild BM25 over all chunk texts
9. Persist FAISS index and metadata to disk
10. Return |C|
```

**Algorithm 3.2 Hybrid Retrieval and Reranking**

```text
Input: User query q, top_k, optional category filter
Output: Ranked list of evidence chunks

1. Encode q into dense query vector vq
2. Search FAISS index for an expanded candidate set
3. Collect valid dense candidates and metadata
4. Tokenize q and score all chunks using BM25
5. Add high-scoring BM25 candidates not already selected
6. Create query-chunk pairs for all unique candidates
7. Run cross-encoder on each pair to obtain raw relevance scores
8. Apply sigmoid normalization to each raw score
9. Sort candidates by normalized score in descending order
10. Filter candidates below the minimum score threshold
11. Return the top_k remaining candidates
```

**Algorithm 3.3 Query Routing and Context Construction**

```text
Input: User question q, conversation history h
Output: Retrieval payload for answer generation

1. Detect intent i using the router
2. If i belongs to graph-oriented categories:
3.     Query the knowledge graph and store graph answer g
4. Retrieve vector candidates r from the retrieval engine
5. If graph answer exists and vector evidence is weak:
6.     Suppress vector context
7. Build context list from g and top vector snippets
8. Estimate confidence based on graph and/or vector evidence
9. Mark routing mode as KG, Vector, Combined, or No Hit
10. Return payload with context, sources, snippets, and confidence
```

**Algorithm 3.4 Knowledge Graph Update Validation**

```text
Input: Existing Turtle content old_ttl, new Turtle content new_ttl
Output: Validation result and removal preview

1. Parse old_ttl into RDF graph G_old
2. Parse new_ttl into RDF graph G_new
3. Compute removed triples R = G_old - G_new
4. If parsing fails:
5.     Reject update as invalid Turtle
6. If R is non-empty and confirmation is not provided:
7.     Return warning with count and preview of removed triples
8. Otherwise:
9.     Accept the update and persist new_ttl
```

### Discussion on RRF and Applicability

Because the report specification specifically mentions Reciprocal Rank Fusion, it is important to distinguish between implemented and candidate algorithms. NexRag currently does not execute formal RRF in the repository. Instead, it forms a union of dense and BM25 candidates and then relies on cross-encoder reranking. Nevertheless, RRF remains directly applicable as a future improvement because it would allow score-agnostic fusion of dense and sparse rankings before reranking or even in place of reranking when computational resources are limited. The present architecture is therefore compatible with RRF even though it does not yet instantiate it.

## System Design

System design in NexRag can be understood through four complementary viewpoints: data design, control flow design, API design, and maintenance design. Each viewpoint reflects a different aspect of how the software behaves in operation.

### Data Design

The system does not use a traditional relational database. Instead, it relies on a set of specialized storage artefacts aligned with the type of information being handled. Structured institutional facts are stored as RDF/Turtle files and served through Fuseki. Unstructured document chunks are stored as metadata records in a serialized file and paired with a FAISS index for vector similarity search. Interaction history is stored as CSV logs, while uploaded source PDFs remain in a local directory. This heterogeneous storage design is appropriate because the knowledge handled by the system is itself heterogeneous.

**Table 3.3 Conceptual Data Entities and Storage Artefacts**

| Information Type | Example Content | Storage Form |
|---|---|---|
| Institutional entities | Faculty, departments, courses, regulations | RDF/Turtle files |
| Graph service data | Merged institutional graph | Fuseki dataset |
| Document corpus | Handbooks, seminar guidelines, report instructions | PDF files in `data/pdfs/` |
| Dense retrieval index | Chunk vectors | `vector_store.index` |
| Chunk metadata | Source, page, category, chunk text | `chunks_metadata.pkl` |
| Interaction logs | Timestamp, question, answer, intent, latency | `logs/query_history.csv` |

The repository's current graph data includes classes such as `Department`, `Faculty`, `Course`, and `Regulation`, together with properties such as `hasName`, `hasHOD`, `teaches`, `belongsTo`, `hasDesignation`, `hasCredit`, and `governedBy`. This schema is intentionally minimal but expressive enough for common institutional questions. On the document side, metadata attached to chunks preserves source document identity and page origin, enabling the system to report evidence in a user-facing manner.

### Data Flow Design

The data flow of NexRag starts with a user query and passes through retrieval, interpretation, and presentation stages. At the context level, the system can be represented as a single processing unit that accepts user queries and institutional knowledge sources as inputs and returns grounded answers as outputs. At a more detailed level, the flow includes query classification, graph query execution, vector retrieval, evidence fusion, generation, logging, and frontend rendering.

\begin{center}
\fbox{\parbox{0.92\textwidth}{\textbf{Figure Placeholder:} A workflow diagram showing Turtle source editing in the frontend, API validation, triple-difference inspection, user confirmation on deletions, file save, graph merge, and Fuseki restart.}}
\end{center}


**Figure 3.3 Knowledge Graph Maintenance and Validation Workflow**

\begin{center}
\fbox{\parbox{0.92\textwidth}{\textbf{Figure Placeholder:} A level-1 DFD showing user query entering the API, splitting toward router, KG module, and RAG module, then converging into context construction, LLM generation, response formatting, and history logging.}}
\end{center}


**Figure 3.4 Data Flow Diagram for the Proposed System**

The DFD perspective is useful because it clarifies that NexRag is neither a pure graph query engine nor a pure text retriever. It is a coordinating system in which multiple evidence flows converge before answer generation. This convergence is exactly what enables combined mode responses.

### API and Workflow Design

The backend exposes several endpoints that operationalize the system architecture. These endpoints are not only implementation details; they define the observable capabilities of the software.

**Table 3.4 API Endpoints and Functional Roles**

| Endpoint | Method | Function |
|---|---|---|
| `/api/status` | GET | Returns system readiness, PDF count, chunk count, model and KG state |
| `/api/documents` | GET | Lists available PDF files |
| `/api/documents/{filename}` | DELETE | Deletes a PDF and rebuilds the vector store |
| `/api/upload` | POST | Uploads and indexes a new PDF |
| `/api/chat` | POST | Returns a complete grounded answer |
| `/api/chat/stream` | POST | Streams grounded answer chunks |
| `/api/history` | GET | Returns recent interaction history |
| `/api/kg-files` | GET | Lists editable Turtle source files |
| `/api/kg-source/{filename}` | GET/POST | Reads or overwrites Turtle source content |
| `/api/kg-save/{filename}` | POST | Validates and saves Turtle content with deletion checks |
| `/api/kg-restart` | POST | Rebuilds the merged graph and restarts the KG service |

The main workflow for answering a question can be summarized as follows. The user submits a query through the frontend. The backend receives the request and determines its intent. If the intent suggests graph relevance, the system queries the knowledge graph. Independently, the retrieval engine searches for relevant document chunks using dense and sparse methods. Weak vector results may be suppressed if a graph answer is strong and sufficient. The available evidence is then assembled into a context string and passed to the local LLM. The generated answer is formatted, logged, and returned along with sources, confidence, and routing metadata.

This design ensures that the API layer acts as the single source of truth for operational behavior. It also makes the system easier to test because each capability is exposed through a predictable endpoint rather than buried inside frontend logic.

### Maintenance and Validation Design

The design explicitly includes maintenance workflows. Uploaded PDFs can be added through the API and indexed immediately. Deleted PDFs trigger a rebuild of the vector store to preserve retrieval consistency. Knowledge graph source files can be edited through the interface and validated before saving. The update inspection routine identifies removed triples and asks for confirmation when graph data would be deleted. This reduces the risk of silent data loss.

Such maintenance-oriented design is especially important in an institutional assistant because knowledge sources are not static. Department assignments may change, seminar instructions may be revised, and new project guidelines may need to be added. A system that lacks update workflows would quickly become obsolete. NexRag addresses this concern directly.

## Advantages of the Proposed System

The proposed system offers several advantages over simpler academic assistance approaches.

First, it provides **hybrid evidence coverage**. By combining a knowledge graph with document retrieval, the system can answer both relational and descriptive questions. This gives it broader functional coverage than systems based only on PDFs or only on graph facts.

Second, it offers **grounded response generation**. The local language model is not asked to answer from its internal memory alone. Instead, it is supplied with retrieved evidence and explicitly instructed to avoid unsupported answers. This reduces the risk of hallucination and improves trustworthiness.

Third, it supports **evidence transparency**. The interface exposes routing mode, retrieved snippets, graph sources, and confidence indicators. Users can therefore inspect why the system answered in a certain way instead of being forced to accept opaque outputs.

Fourth, it is **local-first and cost-aware**. The use of a local language model, local vector index, and local graph service reduces dependency on external APIs and supports privacy-sensitive deployment. This is especially beneficial for educational institutions operating under budget or data governance constraints.

Fifth, it is **maintainable and extensible**. New PDFs can be indexed, graph content can be edited, health checks can be run, and evaluation scripts can be extended. The modular code organization also makes future replacement of components feasible.

Sixth, it supports **incremental modernization**. An institution can start with a small graph and a few documents, then expand both over time. The system does not require a fully perfect graph or a massive corpus on day one. This lowers the adoption barrier.

## Applications

The immediate application of NexRag is as an institutional academic assistant for students, faculty members, and administrative users. It can answer questions related to course ownership, faculty assignment, academic regulations, seminar expectations, report formatting, syllabus details, and institutional procedures. Because it preserves evidence, it can also serve as a support tool during orientation, advising, and departmental coordination.

Beyond its immediate use, the same architecture can be adapted to other bounded knowledge environments. In healthcare education, it could support policy and curriculum lookup using guidelines and structured staff or department relations. In legal education, it could combine statutory document retrieval with structured case or statute metadata. In enterprise settings, it could assist employees by combining policy manuals with structured organizational information. The underlying principle is the same: where both structured relationships and unstructured documents matter, a hybrid assistant becomes valuable.

Another application lies in academic administration and quality assurance. Because the system can expose indexed document counts, graph health, and conversation logs, it can support internal audits of information accessibility. Institutions could use the platform to identify common questions, missing documents, or incomplete graph relations. Thus, the system is not only a query answering tool but also a knowledge operations aid.

In a broader educational technology context, NexRag demonstrates a reusable architecture for local-first, evidence-aware assistants. This makes it relevant as a teaching example for courses in artificial intelligence, information retrieval, semantic web technologies, and full-stack software engineering. As a B.Tech project, it therefore has value both as a deployable artifact and as a reference implementation of a modern hybrid AI system.
