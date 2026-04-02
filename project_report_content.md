# MESITAM Institutional AI Assistant - System Report

## 1. System Architecture

The **MESITAM Institutional AI Assistant** utilizes a **Hybrid Retrieval-Augmented Generation (RAG)** architecture, designed to run efficiently on local hardware (RTX 3050, 4GB VRAM). The system integrates structured knowledge from a Knowledge Graph (KG) with unstructured information from vector-indexed documents.

### 1.1 Core Components
1.  **Orchestrator (Streamlit)**: Manages user interaction, session state, and role-based access control (RBAC).
2.  **Semantic Router**: Classifies user queries into intents (e.g., `FACULTY_INFO`, `REGULATION`, `SYLLABUS`) to determine the optimal retrieval strategy.
3.  **Hybrid Retrieval Engine**:
    *   **Vector Store (FAISS)**: Stores chunked PDF documents (Regulations, Syllabi) using `all-MiniLM-L6-v2` embeddings. Supports metadata filtering by document category.
    *   **Knowledge Graph (Apache Jena Fuseki)**: Stores structured entity relationships (Faculty, Courses, Departments) using RDF/Turtle format. Queried via SPARQL.
4.  **Reranker**: A Cross-Encoder (`ms-marco-MiniLM-L-6-v2`) refines retrieval results to ensure high relevance before context injection.
5.  **LLM (Llama 3.2 - 3B)**: Synthesizes the final response using the retrieved hybrid context, adhering to the user's role (Student/Faculty).

### 1.2 Data Flow
1.  **User Query**: "What is the rule for Duty Leave?"
2.  **Intent Detection**: Router identifies intent as `REGULATION`.
3.  **Retrieval**:
    *   **KG**: Queries for "Duty Leave" entities (returns "Max 10 days").
    *   **Vector**: Filters index for `category="REGULATION"` and retrieves top chunks.
4.  **Reranking**: Top results are re-scored for semantic relevance.
5.  **Generation**: LLM receives context + User Role ("Student") to generate a tailored answer.

## 2. Experimental Setup
- **Hardware**: NVIDIA RTX 3050 (4GB VRAM), 16GB RAM.
- **Models**:
    - LLM: `llama3.2:3b` (Quantized GGUF/Ollama)
    - Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
    - Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Dataset**: MESITAM-specific synthetic dataset comprising KTU regulations, CSE Syllabus, and Faculty details.

## 3. Evaluation Metrics (Ragas)
The system was evaluated using the **Ragas** framework on a golden dataset of institutional queries.
- **Faithfulness**: Measures if the answer is derived *only* from the retrieved context (hallucination check).
- **Answer Relevancy**: Measures how pertinent the answer is to the user's query.
- **Context Precision**: Matches the retrieval quality against ground truth chunks.

### 3.1 Quantitative Analysis
| Metric | Score | Description |
| :--- | :--- | :--- |
| **Answer Relevancy** | **0.85** | High relevance indicates the model addresses the user's intent effectively. |
| **Context Precision** | **0.80** | 80% of top-ranked chunks contained the ground truth. |
| **Context Recall** | **0.70** | The system retrieved 70% of all relevant facts from the corpus. |
| **Faithfulness** | *N/A* | (Metric requires larger LLM for strict JSON validation) |

*Table 1: Ragas Evaluation Results on MESITAM Golden Dataset (n=5)*

## 4. Future Enhancements
To elevate the MESITAM Assistant from a prototype to a production-grade academic system, the following improvements are proposed:

### 4.1 Automated Knowledge Graph Construction
Currently, the Knowledge Graph (KG) is populated manually via Turtle (`.ttl`) files. Future work involves implementing an **Information Extraction (IE)** pipeline using standard NLP techniques to automatically scrape data from the college website and staff directories to populate the graph dynamically.

### 4.2 Application Security & Authentication
The current system uses a voluntary "Role Selector". A robust implementation would require:
- **SSO Integration**: Linking with the college's existing Google Workspace or Microsoft 365 accounts.
- **RBAC (Role-Based Access Control)**: Enforcing strict data isolation where students cannot access sensitive faculty notices.

### 4.3 Multimodal Capabilities
Incorporating **Multimedia RAG** to handle non-textual data:
- **Image Processing**: Answering questions based on diagrams in engineering syllabi.
- **Voice Interface**: Integrating OpenAI's Whisper model for speech-to-text to aid visually impaired students.

### 4.4 Advanced Graph Retrieval
Moving beyond simple SPARQL lookups to **GraphRAG**:
- Using the LLM to traverse the graph intelligently (multi-hop reasoning).
- Example: "Who is the HOD of the department that teaches the Computer Graphics course?" (Requires Course -> Dept -> HOD traversal).
