from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
LOG_DIR = ROOT_DIR / "logs"
LOCAL_DIR = ROOT_DIR / "local"

UPLOAD_DIR = DATA_DIR / "uploads"
OFFICIAL_DOCUMENTS_PATH = DATA_DIR / "official_documents.json"
KNOWLEDGE_BASE_PATH = DATA_DIR / "knowledge_base.json"
OFFICIAL_KG_PATH = DATA_DIR / "mesitam_official.ttl"
UPLOAD_KNOWLEDGE_PATH = DATA_DIR / "upload_knowledge.json"
UPLOAD_KG_PATH = DATA_DIR / "mesitam_uploads.ttl"
MERGED_KG_PATH = DATA_DIR / "merged_kg.ttl"
SOURCE_MANIFEST_PATH = DATA_DIR / "official_source_manifest.json"
INGESTION_STATUS_PATH = DATA_DIR / "ingestion_status.json"
INGESTION_STATE_DB = DATA_DIR / "ingestion_state.db"
UPLOAD_STATUS_PATH = DATA_DIR / "upload_status.json"
EVALUATION_STATUS_PATH = DATA_DIR / "evaluation_status.json"
EVALUATION_METRICS_PATH = DATA_DIR / "evaluation_metrics.json"
RAGAS_RESULTS_PATH = LOG_DIR / "ragas_results.csv"
RAGAS_SUMMARY_PATH = LOG_DIR / "ragas_summary.json"
QUERY_HISTORY_FILE = LOG_DIR / "query_history.csv"

LOCAL_INGESTION_DIR = LOCAL_DIR / "ingestion"
LOCAL_RAW_DIR = LOCAL_INGESTION_DIR / "raw"
LOCAL_STAGE_DIR = LOCAL_INGESTION_DIR / "stage"


def ensure_runtime_directories() -> None:
    for path in [
        DATA_DIR,
        LOG_DIR,
        LOCAL_DIR,
        UPLOAD_DIR,
        LOCAL_INGESTION_DIR,
        LOCAL_RAW_DIR,
        LOCAL_STAGE_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


ensure_runtime_directories()
