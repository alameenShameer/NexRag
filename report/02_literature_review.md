# CHAPTER 2 LITERATURE REVIEW

## 2.1 Introduction

The design of a hybrid academic assistant such as NexRag draws upon several active research areas, including retrieval-augmented generation, dense passage retrieval, sentence embedding methods, lexical ranking, reranking strategies, knowledge graph based question answering, and evaluation frameworks for grounded responses. A meaningful literature review for this project must therefore move beyond a narrow summary of chatbot papers and instead study the methods that enable accurate, evidence-backed conversational systems. This chapter reviews major foundational and related works that collectively inform the architecture of NexRag. The discussion emphasizes how each contribution addresses a distinct part of the broader problem of grounded academic question answering.

The literature reveals a general shift away from purely generative models toward systems that retrieve, rank, and integrate external evidence. This shift is driven by the recognition that language models alone are insufficient for knowledge-intensive tasks that require updatable factual grounding (Lewis et al., 2020; Gao et al., 2023). Parallel to this, semantic web and knowledge graph research has continued to demonstrate the benefits of explicit relational representation for domains where entity-level accuracy and explainability matter (Hogan et al., 2021). The hybrid design space explored in NexRag is therefore not accidental; it is a practical response to the complementary strengths and weaknesses highlighted across the reviewed literature.

## 2.2 Review of Foundational and Related Works

### 2.2.1 REALM: Retrieval-Augmented Language Model Pre-Training

Guu et al. (2020) proposed **REALM**, an influential early system showing that language models can benefit from retrieval during pre-training rather than only at inference time. REALM introduced the idea that a model could learn to access an external knowledge source as part of its internal training process, thereby improving performance on knowledge-intensive tasks without memorizing all facts solely within model parameters. The work was important because it showed that retrieval is not merely a post-processing enhancement but can be integrated into the learning objective itself.

For the present project, REALM is relevant less for its exact training setup and more for its conceptual shift. It established retrieval as a first-class component in language-centric architectures. However, REALM is computationally demanding and primarily research-oriented. Its pretraining requirements make it unsuitable for a typical institutional deployment or a local-first student project. NexRag therefore adopts retrieval at inference time rather than retraining the model, but the rationale is clearly connected to the retrieval-centric perspective advanced by REALM.

### 2.2.2 Dense Passage Retrieval for Open-Domain Question Answering

Karpukhin et al. (2020) introduced **Dense Passage Retrieval (DPR)**, showing that dual-encoder dense retrieval can outperform strong BM25 baselines on several open-domain question answering tasks. DPR represents questions and passages in a shared dense vector space and retrieves relevant passages through nearest-neighbour search. This was a major milestone because it established dense retrieval as a practical and effective alternative to purely lexical methods for semantic question answering.

DPR directly informs the dense retrieval philosophy used in NexRag. Although the project does not reimplement DPR training, it uses pretrained embedding models to achieve the same broad goal: representing text chunks and queries in an embedding space where semantically related items are close. The main strength of DPR is its ability to overcome vocabulary mismatch, which is essential in academic query answering where students may ask questions in language that differs from the exact wording in official documents. Its limitation, however, is that dense retrieval alone may favor semantically related but not necessarily policy-authoritative passages. This is one reason NexRag supplements dense retrieval with BM25 and reranking rather than relying on embeddings alone.

### 2.2.3 Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks

Lewis et al. (2020) presented the landmark **RAG** framework, in which a generator conditions its output on documents retrieved from an external corpus. The central contribution of this work was to show how retrieval and generation can be combined to improve factuality and adaptability in knowledge-intensive natural language processing. RAG became foundational because it provided both a conceptual vocabulary and a practical system design for grounded generation.

The relevance of RAG to NexRag is immediate. The project is essentially a domain-specific adaptation of retrieval-augmented principles to academic assistance. However, NexRag extends the classical RAG idea by incorporating two distinct knowledge pathways: graph facts and document evidence. While the original RAG formulation focuses on retrieved text passages, the needs of academic institutional queries require an additional structured layer. A limitation of the original RAG work, from the perspective of institutional deployments, is that it does not directly address explicit entity relations or local-first operational concerns. Nonetheless, it remains the conceptual backbone of the present project.

### 2.2.4 Leveraging Passage Retrieval with Generative Models for Open Domain Question Answering

Izacard and Grave (2021) explored how generative readers benefit from using multiple retrieved passages, leading to the influential **Fusion-in-Decoder (FiD)** line of work. Their key insight was that generative models can combine evidence across multiple retrieved passages more effectively than extractive approaches limited to a single context window. This work demonstrated that the quality of open-domain question answering improves when the model can aggregate distributed evidence rather than depend on a single best passage.

For NexRag, this work is relevant because academic answers may require evidence spanning more than one retrieved chunk, especially when documents are fragmented during chunking. The project's current implementation uses top-ranked chunks from vector search and reranking, concatenating several of them into the LLM context. This is conceptually aligned with the evidence aggregation principle behind FiD, even though the architecture in NexRag is simpler and operates through prompt-based grounding rather than a specialized decoder architecture trained end-to-end. The limitation of FiD in the present deployment context is that it assumes substantial model and training resources, whereas NexRag aims for lightweight local operability.

### 2.2.5 Sentence-BERT for Efficient Sentence Embeddings

Reimers and Gurevych (2019) introduced **Sentence-BERT (SBERT)**, which modified BERT into a siamese architecture capable of producing efficient sentence embeddings suitable for semantic similarity search. Their work addressed a major efficiency problem in vanilla BERT pairwise scoring by making it practical to compare many sentences through cosine similarity in vector space. This contribution is foundational for many modern retrieval systems because it allows semantic indexing at scale.

NexRag uses the `all-MiniLM-L6-v2` embedding model from the Sentence Transformers ecosystem, which inherits the operational logic made popular by SBERT-style embedding approaches. The importance of this work for the project lies in enabling fast semantic retrieval over chunked PDF content. Without efficient sentence or passage embeddings, dense retrieval would be computationally inconvenient for a local-first application. A limitation is that embedding quality depends on the pretrained model and may not perfectly capture institutional jargon. This reinforces the value of combining dense retrieval with lexical ranking and reranking.

### 2.2.6 BM25 and the Probabilistic Relevance Framework

Robertson and Zaragoza (2009) provided a thorough account of the **Probabilistic Relevance Framework** and the development of **BM25**, one of the most influential lexical ranking methods in information retrieval. Their work remains important because it explains why term frequency, document length normalization, and probabilistic ranking remain effective across many search problems. BM25 is especially robust when exact keywords, abbreviations, or formal phrases matter.

In academic institutional search, lexical specificity often carries critical meaning. Terms such as "condonation", "credit", "attendance", "duty leave", or course codes may need exact recognition. NexRag reflects this insight by using BM25 alongside dense retrieval rather than discarding traditional IR techniques. The literature around BM25 demonstrates that sparse retrieval continues to be valuable even in neural retrieval pipelines. Its limitation is that it cannot naturally handle semantic paraphrases or synonymy, which is why it is best used in combination with dense methods rather than as the sole retrieval engine.

### 2.2.7 Passage Re-ranking with BERT

Nogueira and Cho (2019) showed that **BERT-based passage reranking** can substantially improve ranking quality by directly modeling query-passage relevance. Their work demonstrated state-of-the-art performance on passage ranking benchmarks and helped establish the now-common pattern of using a fast first-stage retriever followed by a more precise neural reranker.

This idea is directly embedded in NexRag, where a cross-encoder reranker is applied after candidate generation from FAISS and BM25. The system thereby separates recall from precision: first gather a candidate pool, then rank it more accurately. This is an effective design for institutional query answering because users care more about the quality of the top few displayed sources than about exhaustive recall. The main limitation is computational cost. Cross-encoders are slower than dual encoders or BM25, so they are practical only over a small candidate set. NexRag manages this trade-off by reranking only the shortlisted chunks.

### 2.2.8 Reciprocal Rank Fusion and Rank Aggregation

Cormack, Clarke and Buttcher (2009) proposed **Reciprocal Rank Fusion (RRF)** as a simple yet highly effective method for combining rankings from multiple retrieval systems. Their work showed that even straightforward fusion of independently strong rankers can outperform individual learned models in certain settings. RRF remains influential because it offers a robust method for combining heterogeneous retrieval signals without complex tuning.

NexRag does not currently implement formal RRF in the repository, but the literature remains relevant because the system already combines dense and sparse candidate generation. In its present form, the project merges candidate sets from FAISS and BM25 before reranking with a cross-encoder. RRF could serve as a natural future improvement for score fusion before reranking or as an alternative when reranking resources are constrained. The paper is therefore useful in identifying a strong and interpretable extension path even if it is not yet part of the implemented ranking stage.

### 2.2.9 BEIR: Benchmarking Retrieval in Diverse Zero-Shot Settings

Thakur et al. (2021) introduced **BEIR**, a benchmark designed to evaluate information retrieval systems across heterogeneous datasets in zero-shot settings. This work is significant because it showed that retrieval effectiveness can vary widely across domains, and strong performance on one benchmark does not guarantee robustness elsewhere. BEIR helped the research community appreciate the importance of domain diversity in retrieval evaluation.

The implication for NexRag is important: academic assistant retrieval should not be assumed effective merely because general retrieval models perform well elsewhere. Institutional documents include administrative language, abbreviated course codes, and domain-specific formatting patterns that may not match standard web or encyclopedic corpora. BEIR therefore motivates the need for local evaluation, task-specific testing, and hybrid retrieval strategies. Its limitation for the current project is that it does not directly provide an academic institutional benchmark, but its cross-domain emphasis still strongly informs the evaluation mindset adopted in this report.

### 2.2.10 Knowledge Graphs as a Foundation for Structured Reasoning

Hogan et al. (2021) presented a comprehensive treatment of **knowledge graphs**, explaining their conceptual foundations, modeling practices, query interfaces, and application relevance. This work is valuable because it makes clear that knowledge graphs are not just graph databases with labels attached; they are semantic structures in which entities and relationships are explicitly formalized for interoperable representation and reasoning.

For NexRag, this literature provides the theoretical justification for representing faculty, departments, courses, and regulations as RDF entities linked by properties such as `teaches`, `belongsTo`, and `hasHOD`. The project's use of Apache Jena Fuseki and SPARQL is consistent with semantic web principles described in the broader knowledge graph literature. The strength of this approach lies in precision and explainability. Its limitation is that graphs require curation and schema maintenance, which may be burdensome if institutional data changes frequently or originates from unstructured sources.

### 2.2.11 Knowledge-Augmented Prompting for Zero-Shot KG Question Answering

Baek, Aji and Saffari (2023) proposed **KAPING**, a framework that augments large language model prompts with retrieved knowledge graph facts for zero-shot knowledge graph question answering. This work is relevant because it bridges symbolic knowledge and language generation without requiring expensive task-specific training. The method demonstrates that retrieved graph facts can serve as useful prompt context, allowing a language model to answer questions more accurately in structured domains.

The relevance to NexRag is strong. The project's combined mode similarly incorporates knowledge graph output into the final response context alongside retrieved document evidence. Although the repository implementation does not use the same retrieval mechanism or experimental setup as KAPING, it reflects the same design intuition: graph facts should be surfaced explicitly to guide grounded answer generation. The limitation is that prompt-based graph grounding still depends on the quality of the retrieved facts and the reliability of the generator in respecting them.

### 2.2.12 REANO and Knowledge Graph Generation for Retrieval-Augmented Readers

Fang, Meng and Macdonald (2024) introduced **REANO**, which enhances retrieval-augmented reading models through knowledge graph generation. The central argument of their work is that retrieved passages contain interdependencies that plain passage lists may fail to capture, and that knowledge graph structures can help model those dependencies more effectively. This work is important because it demonstrates a deeper form of structured augmentation inside retrieval-based question answering pipelines.

For NexRag, REANO reinforces the general value of combining textual retrieval with graph-aware reasoning. The project uses a simpler institutional knowledge graph rather than generating graphs dynamically from retrieved passages, yet the core motivation overlaps: richer structured representation can improve the quality and coherence of answer formation. The limitation of REANO in the context of a B.Tech project is that it introduces complexity beyond what is practical for a lightweight local-first system. Nonetheless, it helps justify future expansion toward tighter graph-text integration.

### 2.2.13 G-Retriever for Textual Graph Understanding and Question Answering

He et al. (2024) presented **G-Retriever**, a retrieval-augmented framework for textual graph understanding and graph question answering. The work is significant because it targets graph-centric question answering through selective retrieval rather than attempting to encode an entire graph directly into a model prompt. This is especially relevant for scalability and for reducing hallucination when graph information is large or structurally complex.

Although NexRag focuses on an institutional graph rather than general graph QA benchmarks, the relevance is conceptual. G-Retriever shows that selective access to graph evidence can scale better than naively serializing a full graph into text. NexRag already follows this practical spirit by querying Fuseki for the needed entity relationships instead of embedding the entire graph in prompt context. The limitation is that G-Retriever addresses broader graph QA tasks than those needed here, but it still strengthens the rationale for graph-aware retrieval in hybrid assistants.

### 2.2.14 Retrieval-Augmented Generation for Large Language Models: A Survey

Gao et al. (2023) produced a survey of **retrieval-augmented generation for large language models**, synthesizing the design space of retrievers, generators, knowledge sources, and evaluation concerns. Surveys of this type are valuable not because they introduce a single method, but because they clarify the emerging taxonomy of RAG systems and the major design decisions that practitioners must make. The survey highlights issues such as retrieval quality, grounding faithfulness, system efficiency, and domain adaptation.

This work helps frame NexRag within the broader RAG landscape. It confirms that modern RAG systems increasingly depend on careful pipeline engineering rather than a single monolithic algorithm. The survey also underscores the importance of heterogeneous knowledge sources and rigorous evaluation, both of which are central to the present project. A limitation of survey literature is that it is not itself an implementation blueprint, but it is highly useful for contextualizing the architectural decisions taken in this work.

### 2.2.15 RAGAs: Automated Evaluation of Retrieval-Augmented Generation

Es et al. (2024) introduced **RAGAs**, a framework for evaluating retrieval-augmented generation systems without depending entirely on manually curated reference answers. By separating dimensions such as faithfulness, answer relevancy, context precision, and context recall, RAGAs addresses a major problem in RAG development: answer quality cannot be understood by looking only at surface fluency or final correctness. The retrieval stage and the generation stage both matter, and failures can occur in either component.

RAGAs is directly relevant to NexRag because the repository includes an evaluation script based on this framework. Even though the full evaluation was not executed during the verification session documented in Chapter 4, the presence of the script indicates that the project design acknowledges the need for multidimensional RAG evaluation. The framework is particularly valuable for a system like NexRag, where answer quality depends on routing, retrieval, graph availability, and prompt grounding. Its limitation is that evaluation itself becomes dependent on model availability and local runtime conditions, which can complicate repeatability in constrained environments.

## 2.3 Comparative Analysis of Existing Approaches

Table 2.1 summarizes the reviewed works in terms of method type, major contribution, strength, limitation, and relevance to the proposed project.

**Table 2.1 Comparative Review of Related Research Works**

| Work | Core Idea | Major Strength | Major Limitation | Relevance to NexRag |
|---|---|---|---|---|
| Guu et al. (2020) REALM | Retrieval during language model pre-training | Strong knowledge integration | Training complexity | Motivates retrieval-centric design |
| Karpukhin et al. (2020) DPR | Dense dual-encoder retrieval | Semantic recall | Domain mismatch risk | Supports dense retrieval stage |
| Lewis et al. (2020) RAG | Retrieval-grounded generation | Reduced hallucination | Limited structured reasoning | Conceptual base for the system |
| Izacard and Grave (2021) FiD | Multi-passage generative fusion | Better evidence aggregation | Heavy model requirements | Supports multi-chunk context design |
| Reimers and Gurevych (2019) SBERT | Efficient sentence embeddings | Practical semantic search | Embedding bias/domain gap | Supports embedding-based indexing |
| Robertson and Zaragoza (2009) BM25 | Probabilistic lexical ranking | Strong exact-term matching | Weak semantic generalization | Supports sparse retrieval stage |
| Nogueira and Cho (2019) | Cross-encoder reranking | High precision ranking | Higher latency | Supports reranking stage |
| Cormack et al. (2009) RRF | Rank fusion across systems | Simple and robust fusion | Not used alone for generation | Future enhancement path |
| Thakur et al. (2021) BEIR | Zero-shot IR benchmark | Cross-domain evaluation insight | No institutional dataset | Motivates local testing |
| Hogan et al. (2021) | Knowledge graph foundations | Structured semantics | Manual curation cost | Supports graph design |
| Baek et al. (2023) KAPING | KG facts as prompt context | Zero-shot graph grounding | Prompt reliance | Aligns with combined mode |
| Fang et al. (2024) REANO | KG generation for RAG readers | Models passage dependencies | Complex pipeline | Inspires richer graph-text coupling |
| He et al. (2024) G-Retriever | Retrieval over textual graphs | Scalable graph QA | Broader than institutional scope | Supports graph-aware retrieval reasoning |
| Gao et al. (2023) Survey | Taxonomy of RAG systems | Holistic design view | Not an implementation method | Frames overall architecture |
| Es et al. (2024) RAGAs | Multi-metric RAG evaluation | Better diagnostic evaluation | Runtime dependency | Guides evaluation methodology |

The comparison shows that no single prior work fully addresses the exact needs of a local institutional academic assistant. Dense retrieval methods solve semantic matching but not explicit entity relations. Knowledge graph methods solve structure but not rich textual explanation. Generative RAG improves answer fluency and grounding but may remain weak on structured relationship queries. Evaluation frameworks diagnose pipeline quality but do not provide the underlying retrieval or graph architecture. The proposed project therefore emerges as a practical synthesis rather than a direct replication of any one prior study.

## 2.4 Research Gaps Identified

The literature reviewed above reveals several research and implementation gaps that justify the development of NexRag. The first gap is the **lack of domain-specific hybrid assistants for institutional academic environments**. Much of the RAG literature is evaluated on open-domain question answering benchmarks, encyclopedic corpora, or generic retrieval tasks. These settings differ from academic institutional deployments, where documents are procedural, relational facts matter, and users require both concise answers and traceable sources.

The second gap is the **insufficient integration of structured and unstructured knowledge in lightweight deployments**. Many research systems either focus on document retrieval or on knowledge graph reasoning, but comparatively fewer systems address their integration in a resource-conscious, local-first environment. Yet practical institutional assistants need exactly this combination: graph precision for relationships and document evidence for explanatory detail.

The third gap is the **limited emphasis on operational transparency in end-user interfaces**. Research papers often focus on retrieval accuracy or answer correctness while paying less attention to how routing mode, evidence source, system status, and confidence should be presented to users. The NexRag repository suggests that user trust benefits when such internals are made visible through the frontend, indicating an important engineering gap between benchmark systems and real user-facing applications.

The fourth gap is the **need for maintainable institutional knowledge update workflows**. Graph-based academic assistants are only useful if administrators or developers can update entity data safely. Similarly, document-based systems are only useful if new PDFs can be uploaded and indexed without manual redesign. The literature recognizes the value of updated knowledge, but many experimental systems do not foreground operational update workflows as first-class design goals.

The fifth gap is the **evaluation gap between theoretical metrics and practical repository verification**. While frameworks like RAGAs provide sophisticated automated metrics, real deployments also require evidence that services start correctly, indexes load, queries route as expected, and retrieved outputs appear meaningful in the interface. For an academic assistant, software verification and system integration are part of answer quality. This report therefore treats evaluation more holistically than benchmark-only approaches.

In summary, the literature strongly supports the ingredients of the proposed system, but it does not fully close the gap between research prototypes and a practical academic assistant for institutional use. NexRag is designed to address this gap by combining hybrid retrieval, graph querying, local deployment, evidence visibility, and maintainable engineering workflows within a single application.
