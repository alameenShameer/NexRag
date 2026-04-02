# MESITAM Institutional AI Assistant

## 🎓 Project Overview
This project transforms a standard RAG system into a domain-specific assistant for **MES Institute of Technology and Management**. It is designed to run locally on moderate hardware (RTX 3050 4GB).

**Key Features:**
- **Institutional Knowledge Graph**: Models Faculty, Courses, and Departments.
- **Smart Document Library**: Filters PDFs by category (Syllabus, Regulations, Notices).
- **Role-Awareness**: Tailors answers for Students vs. Faculty.
- **Hybrid Retrieval**: Combines Vector Search (FAISS) + Graph Search (SPARQL).

## 🚀 Quick Start
1.  **Double-click** `start_mesitam_assistant.bat`.
    *   This starts the Fuseki Server (Knowledge Graph) in the background.
    *   This launches the Streamlit Interface in your browser.

2.  **Access the App**: [http://localhost:8503](http://localhost:8503)

## 📂 Project Structure
- `app.py`: Main application logic (Streamlit).
- `rag.py`: Retrieval engine (FAISS + SentenceTransformers).
- `kg.py`: Knowledge Graph connector (SPARQL).
- `router.py`: Semantic intent classifier.
- `data/mesitam_data.ttl`: RDF Data for the Knowledge Graph.
- `data/pdfs/`: Directory for Uploaded Documents.

## 🛠️ Management
### adding New Documents
1.  Go to the **"Knowledge Base"** tab in the app.
2.  Upload a PDF.
3.  **Select Category**:
    - `SYLLABUS`: For course content.
    - `REGULATION`: For university rules (KTU).
    - `NOTICE`: For circulars/events.

### Editing the Knowledge Graph
Edit `data/mesitam_data.ttl` using a text editor or Protégé, then restart the application.

## 📊 Evaluation
To Generate the "Accuracy Report" for your project:
1.  Ensure the app is NOT running (to free up VRAM).
2.  Run: `python eval_ragas.py`
3.  Results will be saved to `logs/ragas_results.csv`.

## ⚠️ Troubleshooting
- **"Connection Refused"**: Ensure `java` is installed and `start_mesitam_assistant.bat` ran successfully.
- **"CUDA OOM"**: Close other apps using GPU. The system is tuned for 4GB VRAM.
