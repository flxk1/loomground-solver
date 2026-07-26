"""Standalone and injected evidence resolution for interoperability requests."""
from __future__ import annotations

import hashlib

from .interop import EvidenceRef


class InlineEvidenceProvider:
    """Strict provider over JSON-safe evidence embedded in a request.

    Entries are keyed by ``(source_id, item_id)`` and carry ``text`` or full-source
    ``content``. Digests are SHA-256 over UTF-8 ``content`` (falling back to ``text``).
    """

    def __init__(self, entries=()):
        self._entries = {}
        for entry in entries:
            key = (str(entry.get("source_id", "")), str(entry.get("item_id", "")))
            if key in self._entries:
                raise ValueError(f"duplicate inline evidence {key!r}")
            self._entries[key] = dict(entry)

    @classmethod
    def from_request(cls, request):
        return cls(request.extensions.get("inline_evidence", ()))

    def resolve(self, ref: EvidenceRef) -> dict:
        key = (ref.source_id, ref.item_id)
        entry = self._entries.get(key)
        if entry is None and ref.item_id:
            entry = self._entries.get((ref.source_id, ""))
        if entry is None:
            raise KeyError(f"evidence not found: {key!r}")
        return dict(entry)

    def verify(self, ref: EvidenceRef) -> bool:
        try:
            entry = self.resolve(ref)
        except KeyError:
            return False
        if entry.get("source_id") != ref.source_id:
            return False
        if ref.item_id and entry.get("item_id", "") not in ("", ref.item_id):
            return False
        content = str(entry.get("content", entry.get("text", "")))
        if ref.span_start is not None and ref.span_end is not None:
            if ref.span_end > len(content):
                return False
        if ref.content_digest:
            actual = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
            if actual != ref.content_digest.lower():
                return False
        return True


def grounded_text(ref: EvidenceRef, payload: dict) -> str:
    content = str(payload.get("content", payload.get("text", "")))
    if ref.span_start is not None and ref.span_end is not None:
        return content[ref.span_start:ref.span_end]
    return str(payload.get("text", content))
