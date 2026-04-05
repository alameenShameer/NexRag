from __future__ import annotations

import re
from typing import List, Set


GENERIC_DEPARTMENT_TOKENS = {
    "and",
    "department",
    "dept",
    "head",
    "hod",
    "of",
    "the",
}


def normalize_department_text(text: str) -> str:
    normalized = (text or "").lower().replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9()]+", " ", normalized)
    return " ".join(normalized.split()).strip()


def meaningful_department_tokens(text: str) -> List[str]:
    tokens = []
    for token in normalize_department_text(text).split():
        if token in GENERIC_DEPARTMENT_TOKENS or len(token) < 3:
            continue
        tokens.append(token)
    return tokens


def question_mentions_alias(text: str, alias: str) -> bool:
    normalized_text = f" {normalize_department_text(text)} "
    relaxed_text = normalized_text.replace("(", " ").replace(")", " ")
    normalized_alias = normalize_department_text(alias)
    if not normalized_alias:
        return False
    alias_token = f" {normalized_alias} "
    return alias_token in normalized_text or alias_token in relaxed_text


def _dept_variants(text: str) -> Set[str]:
    variants: Set[str] = set()
    normalized = normalize_department_text(text)
    if not normalized:
        return variants
    variants.add(normalized)
    if normalized.startswith("department of "):
        variants.add(normalized.replace("department of ", "dept of ", 1))
    if normalized.startswith("dept of "):
        variants.add(normalized.replace("dept of ", "department of ", 1))
    if normalized.startswith("department "):
        variants.add(normalized.replace("department ", "dept ", 1))
    if normalized.startswith("dept "):
        variants.add(normalized.replace("dept ", "department ", 1))
    return variants


def department_aliases(text: str) -> Set[str]:
    aliases: Set[str] = set()
    normalized = normalize_department_text(text)
    base_text = re.sub(r"\s*\([^)]*\)", " ", text or "")
    base_normalized = normalize_department_text(base_text)

    aliases.update(_dept_variants(normalized))
    aliases.update(_dept_variants(base_normalized))

    base_tokens = meaningful_department_tokens(base_text)
    if base_tokens:
        base_phrase = " ".join(base_tokens)
        aliases.add(base_phrase)
        if len(base_tokens) >= 2 and base_tokens[-1] == "engineering":
            aliases.add(" ".join(base_tokens[:-1]))
        base_initials = "".join(token[0] for token in base_tokens)
        if len(base_initials) >= 2:
            aliases.add(base_initials)
        if len(base_tokens) >= 2:
            aliases.add("".join(token[0] for token in base_tokens[:2]))
    else:
        base_initials = ""

    qualifier_match = re.search(r"\(([^)]+)\)", text or "")
    if qualifier_match:
        qualifier_tokens = meaningful_department_tokens(qualifier_match.group(1))
        if qualifier_tokens:
            qualifier_phrase = " ".join(qualifier_tokens)
            aliases.add(qualifier_phrase)
            qualifier_initials = "".join(token[0] for token in qualifier_tokens)
            if len(qualifier_initials) >= 2:
                aliases.add(qualifier_initials)
            if base_initials and qualifier_initials:
                aliases.add(f"{base_initials}{qualifier_initials}")
                aliases.add(f"{base_initials} {qualifier_initials}")

    return {alias for alias in aliases if len(alias) >= 2}
