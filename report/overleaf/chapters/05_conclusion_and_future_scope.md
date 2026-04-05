# CONCLUSION AND FUTURE SCOPE

## Summary of Work

This project report presented the design, implementation, and analysis of **NexRag**, a local-first hybrid academic assistant intended to answer institutional queries using both structured and unstructured evidence sources. The system was motivated by a practical problem in academic environments: important information is available, but it is dispersed across document collections, regulations, course records, and departmental knowledge. Conventional search interfaces require users to perform the burden of navigation and interpretation themselves, while generic conversational systems cannot be trusted to produce institution-specific answers without grounding. NexRag addressed this challenge by combining a knowledge graph, a retrieval-augmented document pipeline, and a local language model inside a transparent full-stack application.

The work brought together multiple technical layers. On the backend, FastAPI was used as the central orchestration layer. On the retrieval side, PDFs were processed using `pdfplumber`, chunked into indexed units, embedded using a sentence-transformer model, stored in a FAISS vector index, and complemented with BM25 lexical ranking and cross-encoder reranking. On the structured side, institutional entities and relations were represented using RDF/Turtle and queried through Apache Jena Fuseki. On the generation side, a local model served through Ollama produced grounded answers using the retrieved evidence. On the frontend, React components provided chat interaction, source visualization, system status reporting, and knowledge graph editing support. The result was an integrated, evidence-aware academic assistant rather than a standalone retrieval demo or isolated chatbot.

The report also highlighted that the project is not purely conceptual. The repository currently contains seven indexed PDF documents, 290 vectorized chunks, graph files representing departments, faculty, courses, and regulations, and a set of test scripts and maintenance tools. Verification conducted on 3 April 2026 confirmed successful module imports, correct router behavior on the provided test set, successful loading of the embedding and reranking models, and strong document retrieval performance for representative academic queries such as attendance rules and seminar guidelines. Even where live services were unavailable, the distinction between implemented capability and runtime availability was documented carefully.

## Key Achievements

The project achieved a number of important engineering and academic outcomes. The first major achievement is the successful creation of a **hybrid question answering architecture** tailored to institutional academic use. The system does not depend on a single technique. Instead, it brings together graph querying for explicit relations and RAG-style retrieval for descriptive document content. This is a meaningful achievement because it reflects an understanding of the actual heterogeneity of academic information.

The second achievement is the implementation of a **local-first deployment strategy**. By using a local language model, local vector artefacts, and a local graph server, the project demonstrates that grounded academic assistance can be built without defaulting to proprietary cloud APIs. This improves deployment control and aligns well with privacy-sensitive institutional scenarios.

The third achievement is the emphasis on **evidence transparency**. The system surfaces routing mode, confidence values, document snippets, graph evidence, and health indicators in the interface. This is especially valuable in educational settings, where the usefulness of an answer is closely tied to the user's ability to trust and inspect it.

The fourth achievement is the inclusion of **maintenance-oriented workflows**. Document upload, vector rebuilding, graph file editing, deletion validation, history logging, and health-check support are all signs that the project has been approached as a practical software system rather than a one-time demonstration. This increases the long-term relevance of the work.

The fifth achievement is the educational value of the project as a **multi-disciplinary engineering system**. It integrates natural language processing, information retrieval, semantic web technologies, API design, frontend development, and system evaluation within one coherent application. This makes it a strong example of applied AI engineering at the B.Tech level.

**Table 5.1 Summary of Achievements and Forward Directions**

| Area | Achievement in Current Work | Logical Future Direction |
|---|---|---|
| Retrieval | Dense + BM25 + reranking pipeline implemented | Better corpus filtering and fusion tuning |
| Knowledge graph | RDF graph and SPARQL query flow implemented | Live graph scaling and richer ontology |
| Generation | Local grounded LLM responses implemented | Better prompt control and model upgrades |
| Interface | Source-aware chat UI with status panels | Role-based views and richer analytics |
| Maintainability | Upload, logging, KG editing, health scripts | Automated administration workflows |
| Evaluation | Functional checks and RAGAs script present | Full benchmarked end-to-end evaluation |

## Limitations

Although NexRag demonstrates clear promise, the current project also has limitations that should be recognized honestly. The first limitation is that the router is keyword-based and therefore may not generalize well to highly varied or implicit user phrasing. While effective for a bounded academic domain, this design may misclassify ambiguous or unusually worded queries.

The second limitation is the dependence on service availability. The knowledge graph subsystem requires the Fuseki service to be running, and the generation subsystem depends on the local Ollama model being available. The verification session documented in this report showed that the graph service was offline at the time of testing. This highlights that the operational state of the full system is influenced not only by code correctness but also by coordinated service management.

The third limitation concerns evaluation depth. Although the repository includes test scripts and a RAGAs evaluation script, a comprehensive metric-driven evaluation was not completed during the observed session. As a result, the present report emphasizes functional verification and sample retrieval quality rather than large-scale statistical benchmarking.

The fourth limitation lies in corpus size and graph breadth. The current indexed PDF collection is relatively small, and the graph schema is intentionally compact. This is reasonable for a prototype, but broader institutional deployment would require more documents, richer entity types, more complete relationship coverage, and stronger update governance.

The fifth limitation concerns local model capability. A lightweight local model supports privacy and cost goals, but it may provide less expressive reasoning or linguistic polish than larger cloud-hosted models. The project therefore prioritizes controllability and groundedness over maximum raw generative sophistication.

## Future Scope

The future scope of NexRag is substantial. A first improvement would be to replace or augment the current rule-based router with a learned intent classifier capable of handling paraphrase, ambiguity, and multi-intent queries more effectively. This could increase routing robustness while preserving the transparency benefits of explicit mode labeling.

A second future direction is the introduction of **formal rank fusion**, such as Reciprocal Rank Fusion, before or alongside reranking. Since the current system already produces dense and sparse candidate sets, the addition of fusion logic would be a natural and theoretically grounded enhancement. This may improve candidate quality, especially as the corpus expands.

A third direction is the expansion of the knowledge graph. The current graph already models core institutional entities, but it could be extended to include semesters, laboratories, timetable links, examination notifications, prerequisites, event schedules, and administrative contacts. A richer ontology would improve structured query coverage and make combined graph-document answers more powerful.

A fourth improvement would involve stronger **evaluation methodology**. The repository already contains the basis for RAGAs-style evaluation. Future work can execute full end-to-end benchmarking over a larger golden dataset, measure faithfulness and context precision, and compare graph-only, retrieval-only, and combined configurations quantitatively. This would convert the current functional verification into a more rigorous research-grade assessment.

A fifth direction is operational scaling. As document volume grows, indexing and retrieval strategies may need optimization, including improved metadata filtering, batch update workflows, caching, and perhaps more scalable ANN index variants. On the graph side, automated synchronization between administrative datasets and Turtle sources could reduce manual maintenance overhead.

A sixth direction concerns user experience. Future versions could introduce authentication, role-specific dashboards for students and faculty, downloadable source summaries, administrative analytics, conversational follow-up grounding, and notification-aware retrieval over newly added documents or updated regulations.

Finally, NexRag could be generalized into a reusable platform for other institutions or other domains where structured and unstructured knowledge coexist. With appropriate reconfiguration of documents, graph schema, and prompts, the same architecture could support enterprise knowledge management, healthcare education, or regulatory assistance systems.

## Closing Remarks

NexRag demonstrates that a final year engineering project can move beyond a generic chatbot and instead address a meaningful institutional problem with architectural seriousness. The project shows how dense retrieval, lexical search, graph querying, local language generation, and user-facing evidence transparency can be combined into a coherent academic assistant. The implementation already offers a solid foundation, and the identified future directions provide a clear roadmap for turning it into a more robust institutional platform.

The most important conclusion of this work is not merely that hybrid AI systems are possible, but that they are particularly appropriate for academic domains where correctness, explainability, and controllable deployment matter. By aligning research ideas from RAG, semantic retrieval, knowledge graphs, and evaluation frameworks with a practical repository implementation, NexRag stands as a relevant and technically grounded B.Tech project with clear educational and operational value.
