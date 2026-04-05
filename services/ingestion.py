from __future__ import annotations

import hashlib
import io
import json
import re
import sqlite3
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

import pdfplumber
import requests
from bs4 import BeautifulSoup

from merge_kg import merge_ttl_files
from rag import clean_document_text, clean_pdf_page_text, get_rag_engine, is_noise_line

from .config import (
    INGESTION_STATE_DB,
    INGESTION_STATUS_PATH,
    KNOWLEDGE_BASE_PATH,
    LOCAL_RAW_DIR,
    OFFICIAL_DOCUMENTS_PATH,
    OFFICIAL_KG_PATH,
    SOURCE_MANIFEST_PATH,
    UPLOAD_DIR,
)
from .knowledge_base import get_knowledge_base_service


USER_AGENT = "NexRagIngestionBot/1.0 (+https://www.mesitam.ac.in/)"
PERSON_PREFIX_PATTERN = re.compile(r"^(Prof\.?|Dr\.?|Mr\.?|Ms\.?|Mrs\.?)\s*", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"\s+")
INTAKE_PATTERN = re.compile(r"intake of\s+(\d+)", re.IGNORECASE)
CONTENT_BLOCK_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "blockquote")
NOISE_TAGS = ("script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg")


@dataclass(frozen=True)
class OfficialSource:
    id: str
    url: str
    kind: str
    category: str
    title: str
    parser: str
    tags: List[str]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(text: str) -> str:
    lowered = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return lowered or "item"


def sanitize_text(text: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", text or "").strip()


def looks_like_person(text: str) -> bool:
    cleaned = sanitize_text(text)
    if not cleaned:
        return False
    return bool(PERSON_PREFIX_PATTERN.match(cleaned))


class IngestionStateStore:
    def __init__(self, db_path: Path = INGESTION_STATE_DB) -> None:
        self.db_path = db_path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    url TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    etag TEXT,
                    last_modified TEXT,
                    fingerprint TEXT,
                    content_type TEXT,
                    status TEXT,
                    title TEXT,
                    category TEXT,
                    fetched_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL,
                    index_version TEXT,
                    changed_sources INTEGER DEFAULT 0,
                    message TEXT
                )
                """
            )
            connection.commit()

    def get_source(self, url: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT source_id, etag, last_modified, fingerprint, content_type, status, title, category, fetched_at FROM sources WHERE url = ?",
                (url,),
            ).fetchone()
        if not row:
            return None
        keys = ["source_id", "etag", "last_modified", "fingerprint", "content_type", "status", "title", "category", "fetched_at"]
        return dict(zip(keys, row))

    def upsert_source(self, source: OfficialSource, metadata: Dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sources (url, source_id, etag, last_modified, fingerprint, content_type, status, title, category, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    source_id = excluded.source_id,
                    etag = excluded.etag,
                    last_modified = excluded.last_modified,
                    fingerprint = excluded.fingerprint,
                    content_type = excluded.content_type,
                    status = excluded.status,
                    title = excluded.title,
                    category = excluded.category,
                    fetched_at = excluded.fetched_at
                """,
                (
                    source.url,
                    source.id,
                    metadata.get("etag"),
                    metadata.get("last_modified"),
                    metadata.get("fingerprint"),
                    metadata.get("content_type"),
                    metadata.get("status"),
                    source.title,
                    source.category,
                    metadata.get("fetched_at"),
                ),
            )
            connection.commit()

    def add_run(self, started_at: str, status: str, message: str = "") -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO runs (started_at, status, message) VALUES (?, ?, ?)",
                (started_at, status, message),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def complete_run(self, run_id: int, status: str, index_version: str, changed_sources: int, message: str = "") -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE runs
                SET completed_at = ?, status = ?, index_version = ?, changed_sources = ?, message = ?
                WHERE id = ?
                """,
                (utc_now_iso(), status, index_version, changed_sources, message, run_id),
            )
            connection.commit()


def _load_manifest() -> List[OfficialSource]:
    with SOURCE_MANIFEST_PATH.open("r", encoding="utf-8") as file_handle:
        items = json.load(file_handle)
    return [OfficialSource(**item) for item in items]


def _fetch_url(session: requests.Session, source: OfficialSource) -> Dict[str, Any]:
    response = session.get(source.url, timeout=45)
    response.raise_for_status()
    content = response.content
    fingerprint = hashlib.sha256(content).hexdigest()
    parsed_url = urlparse(source.url)
    suffix = Path(parsed_url.path).suffix or (".pdf" if source.kind == "pdf" else ".html")
    snapshot_path = LOCAL_RAW_DIR / f"{source.id}{suffix}"
    snapshot_path.write_bytes(content)
    return {
        "content": content,
        "text": response.text if source.kind == "html" else None,
        "etag": response.headers.get("ETag"),
        "last_modified": response.headers.get("Last-Modified"),
        "content_type": response.headers.get("Content-Type"),
        "fingerprint": fingerprint,
        "snapshot_path": snapshot_path,
    }


def _plain_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.find("body") or soup
    blocks: List[str] = []
    seen: set[str] = set()
    for tag in main.find_all(CONTENT_BLOCK_TAGS):
        text = sanitize_text(tag.get_text(" ", strip=True))
        if not text:
            continue
        if len(text.split()) < 3 and tag.name not in {"h1", "h2", "h3", "h4"}:
            continue
        lowered = text.lower()
        if lowered in seen or is_noise_line(text):
            continue
        seen.add(lowered)
        blocks.append(text)

    if blocks:
        return clean_document_text("\n\n".join(blocks))

    fallback = sanitize_text(main.get_text("\n", strip=True))
    return clean_document_text(fallback)


def _extract_links(base_url: str, soup: BeautifulSoup) -> List[Dict[str, str]]:
    links: List[Dict[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = urljoin(base_url, anchor["href"])
        if href in seen:
            continue
        seen.add(href)
        label = sanitize_text(anchor.get_text(" ", strip=True))
        if label:
            links.append({"label": label, "url": href})
    return links


def _extract_facilities(text: str, source_url: str) -> List[Dict[str, Any]]:
    facility_names = [
        "Computing Facilities",
        "Central Library and Information Centre",
        "Digital Library",
        "Internet Facilities",
        "Hostels",
    ]
    facilities = []
    for name in facility_names:
        if name.lower() in text.lower():
            facilities.append(
                {
                    "id": slugify(name),
                    "name": name,
                    "description": text,
                    "source_url": source_url,
                    "highlights": [],
                }
            )
    return facilities


def _extract_about_summary(text: str) -> str:
    cleaned = text
    if "Founded in 2009" in cleaned:
        cleaned = cleaned[cleaned.index("Founded in 2009") :]
    elif "Some words about MESITAM" in cleaned:
        cleaned = cleaned[cleaned.index("Some words about MESITAM") :]

    if "Institution Code : MEK" in cleaned:
        cleaned = cleaned.split("Institution Code : MEK", 1)[0]

    return cleaned[:900]


def _parse_hods_page(source: OfficialSource, html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    text = _plain_text_from_html(html)
    faculty = []
    heading_pairs = zip(soup.find_all("h4"), soup.find_all("h5"))
    for name_tag, dept_tag in heading_pairs:
        name = sanitize_text(name_tag.get_text(" ", strip=True))
        department = sanitize_text(dept_tag.get_text(" ", strip=True))
        if not looks_like_person(name):
            continue
        faculty.append(
            {
                "id": slugify(f"{department}-{name}"),
                "name": name,
                "designation": "Head of Department",
                "department": department,
                "email": None,
                "phone": None,
                "bio": "",
                "source_url": source.url,
            }
        )
    return {
        "documents": [
            {
                "id": source.id,
                "title": source.title,
                "url": source.url,
                "category": source.category,
                "tags": source.tags,
                "text": text,
                "source_type": "official",
            }
        ],
        "faculty": faculty,
    }


def _extract_department_faculty(soup: BeautifulSoup, source_url: str, department_name: str) -> List[Dict[str, Any]]:
    faculty = []
    seen_names = set()
    for tag in soup.find_all(["h4", "h5"]):
        name = sanitize_text(tag.get_text(" ", strip=True))
        if not looks_like_person(name) or name in seen_names:
            continue
        parent_text = sanitize_text(tag.parent.get_text(" ", strip=True)) if tag.parent else name
        designation = parent_text.replace(name, "", 1).strip(" -:|")
        if "Phone" in name or "Email" in name or len(name) > 80:
            continue
        seen_names.add(name)
        faculty.append(
            {
                "id": slugify(f"{department_name}-{name}"),
                "name": name,
                "designation": designation or "Faculty",
                "department": department_name,
                "email": None,
                "phone": None,
                "bio": "",
                "source_url": source_url,
            }
        )
    return faculty


def _extract_department_courses(summary: str, department_name: str, source_url: str) -> List[Dict[str, Any]]:
    courses = []
    lowered = summary.lower()
    if "mathematics" in department_name.lower() and "science" in department_name.lower():
        return courses
    if "b.tech" in lowered or any(term in department_name.lower() for term in ["engineering", "artificial intelligence"]):
        intake_match = INTAKE_PATTERN.search(summary)
        intake = int(intake_match.group(1)) if intake_match else None
        clean_name = department_name.replace("Dept. of ", "").replace("Department of ", "")
        program_name = f"B.Tech in {clean_name}"
        courses.append(
            {
                "id": slugify(program_name),
                "name": program_name,
                "code": None,
                "description": summary,
                "department": department_name,
                "intake": intake,
                "source_url": source_url,
            }
        )
    if "mba" in lowered:
        courses.append(
            {
                "id": "mba-program",
                "name": "Master of Business Administration (MBA)",
                "code": None,
                "description": summary,
                "department": department_name,
                "intake": None,
                "source_url": source_url,
            }
        )
    return courses


def _parse_department_page(source: OfficialSource, html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    text = _plain_text_from_html(html)
    heading = soup.find("h1")
    department_name = sanitize_text(heading.get_text(" ", strip=True)) if heading else source.title
    summary_heading = next((tag for tag in soup.find_all(["h3", "h4"]) if "summary" in sanitize_text(tag.get_text(" ", strip=True)).lower()), None)
    summary_text = ""
    if summary_heading and summary_heading.parent:
        summary_text = sanitize_text(summary_heading.parent.get_text(" ", strip=True))
        summary_text = summary_text.replace("Summary", "", 1).strip()
    if not summary_text:
        summary_text = text[:900]

    faculty = _extract_department_faculty(soup, source.url, department_name)
    courses = _extract_department_courses(summary_text, department_name, source.url)

    department = {
        "id": slugify(department_name),
        "name": department_name,
        "summary": summary_text,
        "source_url": source.url,
        "faculty_count": len(faculty),
        "courses": [course["name"] for course in courses],
    }
    return {
        "documents": [
            {
                "id": source.id,
                "title": source.title,
                "url": source.url,
                "category": source.category,
                "tags": source.tags,
                "text": text,
                "source_type": "official",
            }
        ],
        "departments": [department],
        "faculty": faculty,
        "courses": courses,
    }


def _parse_simple_page(source: OfficialSource, html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    text = _plain_text_from_html(html)
    links = _extract_links(source.url, soup)
    payload: Dict[str, Any] = {
        "documents": [
            {
                "id": source.id,
                "title": source.title,
                "url": source.url,
                "category": source.category,
                "tags": source.tags,
                "text": text,
                "source_type": "official",
            }
        ]
    }

    lowered_category = source.category.lower()
    if lowered_category == "facility":
        payload["facilities"] = _extract_facilities(text, source.url)
    elif lowered_category == "placement":
        placements = [
            {
                "id": slugify(source.title),
                "title": "Career Guidance & Placement Cell",
                "summary": text[:900],
                "source_url": source.url,
                "highlights": [link["label"] for link in links if "placement" in link["label"].lower()][:6],
            }
        ]
        payload["placements"] = placements
    elif lowered_category == "faq":
        payload["faqs"] = [
            {
                "id": slugify(source.title),
                "question": f"What is available on {source.title}?",
                "answer": text[:600],
                "source_url": source.url,
                "category": source.category,
            }
        ]
    elif lowered_category == "overview":
        payload["overview"] = {
            "college": "MES Institute of Technology and Management",
            "location": "Chathannoor, Kollam, Kerala",
            "summary": _extract_about_summary(text),
        }
    return payload


def _parse_downloads_page(source: OfficialSource, html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    text = _plain_text_from_html(html)
    links = _extract_links(source.url, soup)
    documents = [
        {
            "id": source.id,
            "title": source.title,
            "url": source.url,
            "category": source.category,
            "tags": source.tags,
            "text": text,
            "source_type": "official",
        }
    ]
    faqs = []
    for link in links:
        if "/admin/pdf/" not in link["url"] and not link["url"].lower().endswith(".pdf"):
            continue
        label = link["label"]
        faqs.append(
            {
                "id": slugify(f"download-{label}"),
                "question": f"Where can I find {label}?",
                "answer": f"The document '{label}' is listed on the official MESITAM downloads page.",
                "source_url": link["url"],
                "category": "Downloads",
            }
        )
    return {
        "documents": documents,
        "faqs": faqs,
    }


def _extract_news_items(soup: BeautifulSoup, source_url: str, category: str) -> List[Dict[str, Any]]:
    items = []
    current_date = None
    for tag in soup.find_all(["li", "h2"]):
        text = sanitize_text(tag.get_text(" ", strip=True))
        if not text:
            continue
        if text.lower().startswith("posted on"):
            current_date = text.replace("Posted on :", "").strip()
            continue
        if tag.name == "h2" and len(text) > 3 and text != ".":
            items.append(
                {
                    "id": slugify(f"{category}-{text}"),
                    "title": text,
                    "posted_on": current_date,
                    "summary": text,
                    "category": category,
                    "source_url": source_url,
                }
            )
    return items


def _parse_news_or_events(source: OfficialSource, html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    text = _plain_text_from_html(html)
    category = "announcement" if source.category.lower() == "news" else "event"
    items = _extract_news_items(soup, source.url, category)
    placement_highlights = []
    for item in items:
        if "place" in item["title"].lower():
            placement_highlights.append(
                {
                    "id": slugify(f"placement-{item['title']}"),
                    "title": item["title"],
                    "summary": item["summary"],
                    "source_url": item["source_url"],
                    "highlights": [item["posted_on"]] if item.get("posted_on") else [],
                }
            )
    return {
        "documents": [
            {
                "id": source.id,
                "title": source.title,
                "url": source.url,
                "category": source.category,
                "tags": source.tags,
                "text": text,
                "source_type": "official",
            }
        ],
        "events": items,
        "placements": placement_highlights,
    }


def _parse_pdf_source(source: OfficialSource, content: bytes) -> Dict[str, Any]:
    pages = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                page_text = clean_pdf_page_text(page.extract_text() or "")
                if page_text:
                    pages.append(f"[PAGE {page_number}] {page_text}")
    except Exception:
        fallback_text = clean_document_text(content.decode("utf-8", errors="ignore"))
        if fallback_text:
            pages.append(fallback_text)

    text = clean_document_text("\n".join(pages))
    document = {
        "id": source.id,
        "title": source.title,
        "url": source.url,
        "category": source.category,
        "tags": source.tags,
        "text": text,
        "source_type": "official",
    }

    faqs = []
    lowered_title = source.title.lower()
    if "regulation" in lowered_title:
        if "75%" in text:
            faqs.append(
                {
                    "id": slugify(f"{source.id}-attendance"),
                    "question": "What is the minimum attendance required?",
                    "answer": "The official B.Tech regulation documents mention a minimum attendance requirement of 75%.",
                    "source_url": source.url,
                    "category": "Regulation",
                }
            )
        faqs.append(
            {
                "id": slugify(f"{source.id}-document"),
                "question": f"Where can I access {source.title}?",
                "answer": f"{source.title} is available from the official MESITAM downloads page.",
                "source_url": source.url,
                "category": "Regulation",
            }
        )
    return {"documents": [document], "faqs": faqs}


def _parse_source(source: OfficialSource, fetched: Dict[str, Any]) -> Dict[str, Any]:
    if source.kind == "pdf":
        return _parse_pdf_source(source, fetched["content"])

    html = fetched["text"] or ""
    parser = source.parser
    if parser == "hods":
        return _parse_hods_page(source, html)
    if parser == "department":
        return _parse_department_page(source, html)
    if parser == "downloads":
        return _parse_downloads_page(source, html)
    if parser in {"news", "events"}:
        return _parse_news_or_events(source, html)
    return _parse_simple_page(source, html)


def _merge_items(items: Iterable[Dict[str, Any]], key_field: str) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for item in items:
        key = str(item.get(key_field) or item.get("id") or slugify(json.dumps(item, sort_keys=True)))
        if key not in merged:
            merged[key] = dict(item)
            continue
        current = merged[key]
        for field, value in item.items():
            if field not in current or current[field] in (None, "", [], {}):
                current[field] = value
            elif isinstance(current[field], list) and isinstance(value, list):
                current[field] = list(dict.fromkeys([*current[field], *value]))
    return list(merged.values())


def _build_graph(knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
    nodes = []
    edges = []

    def add_node(node_id: str, label: str, node_type: str) -> None:
        nodes.append({"id": node_id, "label": label, "type": node_type})

    add_node("college-mesitam", "MESITAM", "College")

    department_lookup = {}
    for department in knowledge_base.get("departments", []):
        node_id = f"department-{department['id']}"
        department_lookup[department["name"]] = node_id
        add_node(node_id, department["name"], "Department")

    for course in knowledge_base.get("courses", []):
        node_id = f"course-{course['id']}"
        add_node(node_id, course["name"], "Course")
        edges.append({"id": f"offers-{node_id}", "source": "college-mesitam", "target": node_id, "type": "offers"})
        department_name = course.get("department")
        if department_name and department_name in department_lookup:
            edges.append(
                {
                    "id": f"belongs-{node_id}",
                    "source": node_id,
                    "target": department_lookup[department_name],
                    "type": "belongs_to",
                }
            )

    for faculty in knowledge_base.get("faculty", []):
        node_id = f"faculty-{faculty['id']}"
        add_node(node_id, faculty["name"], "Faculty")
        department_name = faculty.get("department")
        if department_name and department_name in department_lookup:
            edges.append(
                {
                    "id": f"has-faculty-{node_id}",
                    "source": department_lookup[department_name],
                    "target": node_id,
                    "type": "has_faculty",
                }
            )
            edges.append(
                {
                    "id": f"belongs-faculty-{node_id}",
                    "source": node_id,
                    "target": department_lookup[department_name],
                    "type": "belongs_to",
                }
            )

    for facility in knowledge_base.get("facilities", []):
        node_id = f"facility-{facility['id']}"
        add_node(node_id, facility["name"], "Facility")
        edges.append({"id": f"facility-{node_id}", "source": "college-mesitam", "target": node_id, "type": "has_facility"})

    for faq in knowledge_base.get("faqs", []):
        node_id = f"faq-{faq['id']}"
        add_node(node_id, faq["question"], "FAQ")
        edges.append({"id": f"faq-{node_id}", "source": "college-mesitam", "target": node_id, "type": "frequently_asked"})

    for event in knowledge_base.get("events", []):
        node_id = f"event-{event['id']}"
        add_node(node_id, event["title"], "Event")
        edges.append({"id": f"event-{node_id}", "source": "college-mesitam", "target": node_id, "type": "conducts"})

    for placement in knowledge_base.get("placements", []):
        node_id = f"placement-{placement['id']}"
        add_node(node_id, placement["title"], "Placement")
        edges.append({"id": f"placement-{node_id}", "source": node_id, "target": "college-mesitam", "type": "belongs_to"})

    return {"nodes": _merge_items(nodes, "id"), "edges": _merge_items(edges, "id")}


def _escape_ttl_literal(value: str) -> str:
    collapsed = sanitize_text((value or "").replace("\r", " ").replace("\n", " ").replace("\t", " "))
    return collapsed.replace("\\", "\\\\").replace('"', '\\"')


def _build_ttl(knowledge_base: Dict[str, Any]) -> str:
    lines = [
        "@prefix : <http://mesitam.ac.in/ns#> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
        "### Classes ###",
        ":College a rdfs:Class .",
        ":Department a rdfs:Class .",
        ":Course a rdfs:Class .",
        ":Faculty a rdfs:Class .",
        ":Event a rdfs:Class .",
        ":Facility a rdfs:Class .",
        ":FAQ a rdfs:Class .",
        ":Placement a rdfs:Class .",
        "",
        "### Properties ###",
        ":hasName a rdf:Property .",
        ":description a rdf:Property .",
        ":hasCode a rdf:Property .",
        ":hasDesignation a rdf:Property .",
        ":sourceUrl a rdf:Property .",
        ":postedOn a rdf:Property .",
        ":offers a rdf:Property .",
        ":has_faculty a rdf:Property .",
        ":conducts a rdf:Property .",
        ":has_facility a rdf:Property .",
        ":belongs_to a rdf:Property .",
        ":frequently_asked a rdf:Property .",
        "",
        "### College ###",
        ':MESITAM a :College ;',
        '    :hasName "MES Institute of Technology and Management" ;',
        '    :description "Official MESITAM knowledge graph generated from the public website and download resources." .',
        "",
    ]

    department_lookup = {}
    for department in knowledge_base.get("departments", []):
        resource = f":Department_{slugify(department['id'])}"
        department_lookup[department["name"]] = resource
        lines.extend(
            [
                f"{resource} a :Department ;",
                f'    :hasName "{_escape_ttl_literal(department["name"])}" ;',
                f'    :description "{_escape_ttl_literal(department.get("summary", "")[:1200])}" ;',
                f'    :sourceUrl "{_escape_ttl_literal(department.get("source_url", ""))}" .',
                "",
            ]
        )

    for course in knowledge_base.get("courses", []):
        resource = f":Course_{slugify(course['id'])}"
        lines.extend(
            [
                f"{resource} a :Course ;",
                f'    :hasName "{_escape_ttl_literal(course["name"])}" ;',
                f'    :description "{_escape_ttl_literal(course.get("description", "")[:1200])}" ;',
                f'    :sourceUrl "{_escape_ttl_literal(course.get("source_url", ""))}" .',
                f":MESITAM :offers {resource} .",
            ]
        )
        if course.get("department") in department_lookup:
            lines.append(f"{resource} :belongs_to {department_lookup[course['department']]} .")
        lines.append("")

    for faculty in knowledge_base.get("faculty", []):
        resource = f":Faculty_{slugify(faculty['id'])}"
        lines.extend(
            [
                f"{resource} a :Faculty ;",
                f'    :hasName "{_escape_ttl_literal(faculty["name"])}" ;',
                f'    :hasDesignation "{_escape_ttl_literal(faculty.get("designation", "Faculty")[:300])}" ;',
                f'    :sourceUrl "{_escape_ttl_literal(faculty.get("source_url", ""))}" .',
            ]
        )
        if faculty.get("department") in department_lookup:
            lines.append(f"{resource} :belongs_to {department_lookup[faculty['department']]} .")
            lines.append(f"{department_lookup[faculty['department']]} :has_faculty {resource} .")
        lines.append("")

    for facility in knowledge_base.get("facilities", []):
        resource = f":Facility_{slugify(facility['id'])}"
        lines.extend(
            [
                f"{resource} a :Facility ;",
                f'    :hasName "{_escape_ttl_literal(facility["name"])}" ;',
                f'    :description "{_escape_ttl_literal(facility.get("description", "")[:1200])}" ;',
                f'    :sourceUrl "{_escape_ttl_literal(facility.get("source_url", ""))}" .',
                f":MESITAM :has_facility {resource} .",
                "",
            ]
        )

    for faq in knowledge_base.get("faqs", []):
        resource = f":FAQ_{slugify(faq['id'])}"
        lines.extend(
            [
                f"{resource} a :FAQ ;",
                f'    :hasName "{_escape_ttl_literal(faq["question"])}" ;',
                f'    :description "{_escape_ttl_literal(faq.get("answer", "")[:1200])}" ;',
                f'    :sourceUrl "{_escape_ttl_literal(faq.get("source_url", ""))}" .',
                f":MESITAM :frequently_asked {resource} .",
                "",
            ]
        )

    for event in knowledge_base.get("events", []):
        resource = f":Event_{slugify(event['id'])}"
        lines.extend(
            [
                f"{resource} a :Event ;",
                f'    :hasName "{_escape_ttl_literal(event["title"])}" ;',
                f'    :description "{_escape_ttl_literal(event.get("summary", "")[:1200])}" ;',
                f'    :postedOn "{_escape_ttl_literal(event.get("posted_on", ""))}" ;',
                f'    :sourceUrl "{_escape_ttl_literal(event.get("source_url", ""))}" .',
                f":MESITAM :conducts {resource} .",
                "",
            ]
        )

    for placement in knowledge_base.get("placements", []):
        resource = f":Placement_{slugify(placement['id'])}"
        lines.extend(
            [
                f"{resource} a :Placement ;",
                f'    :hasName "{_escape_ttl_literal(placement["title"])}" ;',
                f'    :description "{_escape_ttl_literal(placement.get("summary", "")[:1200])}" ;',
                f'    :sourceUrl "{_escape_ttl_literal(placement.get("source_url", ""))}" .',
                f"{resource} :belongs_to :MESITAM .",
                "",
            ]
        )

    return "\n".join(lines)


def _atomic_json_dump(path: Path, payload: Dict[str, Any] | List[Dict[str, Any]]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2, ensure_ascii=False)
    tmp_path.replace(path)


def _atomic_text_dump(path: Path, content: str) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as file_handle:
        file_handle.write(content)
    tmp_path.replace(path)


class IngestionService:
    def __init__(self) -> None:
        self.state_store = IngestionStateStore()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    def _write_status(self, payload: Dict[str, Any]) -> None:
        with INGESTION_STATUS_PATH.open("w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, indent=2, ensure_ascii=False)

    def get_status(self) -> Dict[str, Any]:
        if not INGESTION_STATUS_PATH.exists():
            status = {
                "state": "idle",
                "message": "Initializing backend / Indexing documents...",
                "active_job": None,
                "last_refresh_at": None,
                "index_version": "uninitialized",
                "last_error": None,
                "changed_sources": 0,
            }
            self._write_status(status)
            return status
        with INGESTION_STATUS_PATH.open("r", encoding="utf-8") as file_handle:
            status = json.load(file_handle)

        # Recover from a stale persisted "running" state after a restart or crash.
        if status.get("state") == "running" and not (self._thread and self._thread.is_alive()):
            index_version = status.get("index_version") or "uninitialized"
            has_ready_kb = KNOWLEDGE_BASE_PATH.exists() and OFFICIAL_DOCUMENTS_PATH.exists() and index_version != "uninitialized"
            healed_status = {
                **status,
                "state": "idle" if has_ready_kb else "error",
                "message": "Knowledge base ready." if has_ready_kb else "Previous ingestion run did not finish cleanly.",
                "active_job": None,
            }
            self._write_status(healed_status)
            return healed_status

        return status

    def schedule_run(self, force: bool = False) -> Dict[str, Any]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return self.get_status()

            def runner() -> None:
                self.run_once(force=force)

            self._thread = threading.Thread(target=runner, daemon=True, name="nexrag-ingestion")
            self._thread.start()
            return self.get_status()

    def run_once(self, force: bool = False) -> Dict[str, Any]:
        started_at = utc_now_iso()
        run_id = self.state_store.add_run(started_at, "running", "Starting ingestion pipeline.")
        previous_status = self.get_status()
        self._write_status(
            {
                "state": "running",
                "message": "Initializing backend / Indexing documents...",
                "active_job": {"run_id": run_id, "started_at": started_at},
                "last_refresh_at": previous_status.get("last_refresh_at"),
                "index_version": previous_status.get("index_version", "uninitialized"),
                "last_error": None,
                "changed_sources": 0,
            }
        )

        manifest = _load_manifest()
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        changed_sources = 0
        aggregated: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        overview: Dict[str, Any] = {
            "college": "MES Institute of Technology and Management",
            "location": "Chathannoor, Kollam, Kerala",
            "summary": "Official MESITAM knowledge base.",
        }
        fingerprints: List[str] = []

        try:
            for source in manifest:
                fetched = _fetch_url(session, source)
                previous = self.state_store.get_source(source.url)
                changed = force or previous is None or previous.get("fingerprint") != fetched["fingerprint"]
                if changed:
                    changed_sources += 1
                fingerprints.append(fetched["fingerprint"])
                parsed = _parse_source(source, fetched)
                self.state_store.upsert_source(
                    source,
                    {
                        "etag": fetched.get("etag"),
                        "last_modified": fetched.get("last_modified"),
                        "fingerprint": fetched["fingerprint"],
                        "content_type": fetched.get("content_type"),
                        "status": "ok",
                        "fetched_at": utc_now_iso(),
                    },
                )
                if parsed.get("overview"):
                    overview.update(parsed["overview"])
                for field in ["documents", "departments", "faculty", "courses", "facilities", "placements", "faqs", "events"]:
                    aggregated[field].extend(parsed.get(field, []))

            status_before = self.get_status()
            if changed_sources == 0 and not force and KNOWLEDGE_BASE_PATH.exists() and OFFICIAL_DOCUMENTS_PATH.exists():
                status = {
                    "state": "idle",
                    "message": "Knowledge base is already up to date.",
                    "active_job": None,
                    "last_refresh_at": status_before.get("last_refresh_at"),
                    "index_version": status_before.get("index_version") or get_knowledge_base_service().index_version(),
                    "last_error": None,
                    "changed_sources": 0,
                }
                self.state_store.complete_run(run_id, "skipped", status["index_version"], 0, status["message"])
                self._write_status(status)
                return status

            knowledge_base = {
                "updated_at": utc_now_iso(),
                "overview": overview,
                "departments": _merge_items(aggregated["departments"], "id"),
                "faculty": _merge_items(aggregated["faculty"], "id"),
                "courses": _merge_items(aggregated["courses"], "id"),
                "facilities": _merge_items(aggregated["facilities"], "id"),
                "placements": _merge_items(aggregated["placements"], "id"),
                "faqs": _merge_items(aggregated["faqs"], "id"),
                "events": _merge_items(aggregated["events"], "id"),
                "documents": _merge_items(aggregated["documents"], "id"),
            }

            graph = _build_graph(knowledge_base)
            knowledge_base["graph"] = graph
            digest = hashlib.sha256("".join(sorted(fingerprints)).encode("utf-8")).hexdigest()[:12]
            knowledge_base["index_version"] = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{digest}"

            _atomic_json_dump(KNOWLEDGE_BASE_PATH, knowledge_base)
            _atomic_json_dump(OFFICIAL_DOCUMENTS_PATH, knowledge_base["documents"])
            _atomic_text_dump(OFFICIAL_KG_PATH, _build_ttl(knowledge_base))
            merge_ttl_files()

            rag_engine = get_rag_engine()
            rag_engine.rebuild_from_sources(upload_dir=UPLOAD_DIR, official_documents=knowledge_base["documents"])
            get_knowledge_base_service().get_data(force_reload=True)

            status = {
                "state": "idle",
                "message": "Knowledge base ready.",
                "active_job": None,
                "last_refresh_at": knowledge_base["updated_at"],
                "index_version": knowledge_base["index_version"],
                "last_error": None,
                "changed_sources": changed_sources,
            }
            self.state_store.complete_run(run_id, "completed", knowledge_base["index_version"], changed_sources, status["message"])
            self._write_status(status)
            return status
        except Exception as exc:
            status = self.get_status()
            error_message = f"Ingestion failed: {exc}"
            failed_status = {
                "state": "error",
                "message": error_message,
                "active_job": None,
                "last_refresh_at": status.get("last_refresh_at"),
                "index_version": status.get("index_version", "uninitialized"),
                "last_error": error_message,
                "changed_sources": changed_sources,
            }
            self.state_store.complete_run(run_id, "failed", failed_status["index_version"], changed_sources, error_message)
            self._write_status(failed_status)
            raise


_ingestion_service = IngestionService()


def get_ingestion_service() -> IngestionService:
    return _ingestion_service
