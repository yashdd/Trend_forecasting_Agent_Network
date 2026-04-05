"""Normalize LLM insight text for human-facing surfaces (exports, optional API)."""
import re

_CITATION_RE = re.compile(r"\[raw_post_id=\d+\s+url=[^\]]*\]", re.IGNORECASE)
_ID_ONLY_RE = re.compile(r"\[raw_post_id=\d+\]", re.IGNORECASE)


def strip_internal_citations(text: str | None) -> str:
    if not text:
        return ""
    s = _CITATION_RE.sub("", text)
    s = _ID_ONLY_RE.sub("", s)
    return re.sub(r"\s{2,}", " ", s).strip()
