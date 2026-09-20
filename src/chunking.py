from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        sentences = re.split(r"(?<=[.!?])\s+|(?<=\.)\n", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks: list[str] = []
        for start in range(0, len(sentences), self.max_sentences_per_chunk):
            group = sentences[start : start + self.max_sentences_per_chunk]
            chunks.append(" ".join(group).strip())
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return self._split(text, self.separators)

    def _hard_cut(self, text: str) -> list[str]:
        return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if len(current_text) <= self.chunk_size:
            return [current_text]

        if not remaining_separators:
            return self._hard_cut(current_text)

        separator, rest_separators = remaining_separators[0], remaining_separators[1:]
        if separator == "":
            return self._hard_cut(current_text)

        parts = [part for part in current_text.split(separator) if part]

        pieces: list[str] = []
        for part in parts:
            if len(part) > self.chunk_size:
                pieces.extend(self._split(part, rest_separators))
            else:
                pieces.append(part)

        merged: list[str] = []
        buffer = ""
        for piece in pieces:
            candidate = f"{buffer}{separator}{piece}" if buffer else piece
            if len(candidate) <= self.chunk_size:
                buffer = candidate
            else:
                if buffer:
                    merged.append(buffer)
                buffer = piece
        if buffer:
            merged.append(buffer)
        return merged


class HeadingChunker:
    """
    Split Markdown text by heading lines ("#".."######"), one section per chunk.

    Rationale: policy/regulation documents are already authored section-by-section
    (e.g. "## Điều 4 — ..."), so each section is a natural, complete semantic unit.
    A section longer than chunk_size is handed to RecursiveChunker, and its heading
    is re-attached to every resulting sub-chunk so later fragments don't lose the
    "which section is this about" context.

    Tried and reverted: prepending each chunk with its ancestor heading(s) as a
    breadcrumb (for nested ### under ##). Measured on data/shopee-return-refund/
    with the real local embedder, it *lowered* the 5-query benchmark score
    (5/10 -> 3/10, see report/REPORT_NHOM.md) — repeating the document title on
    every chunk of a file raises all of that file's chunks' similarity roughly
    uniformly, which drowned out the distinguishing content between chunks more
    than it added useful context. Kept the flat per-heading version instead.
    """

    HEADING_RE = re.compile(r"^(#{1,6})\s+.*$", re.MULTILINE)

    def __init__(self, chunk_size: int = 500) -> None:
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        headings = list(self.HEADING_RE.finditer(text))
        if not headings:
            return RecursiveChunker(chunk_size=self.chunk_size).chunk(text)

        sections: list[tuple[str, str]] = []
        if headings[0].start() > 0:
            preamble = text[: headings[0].start()].strip()
            if preamble:
                sections.append(("", preamble))

        for index, match in enumerate(headings):
            start = match.start()
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            heading_line = match.group().strip()
            sections.append((heading_line, text[start:end].strip()))

        chunks: list[str] = []
        for heading_line, section_text in sections:
            if not section_text:
                continue
            if len(section_text) <= self.chunk_size:
                chunks.append(section_text)
                continue

            for sub_chunk in RecursiveChunker(chunk_size=self.chunk_size).chunk(section_text):
                if heading_line and not sub_chunk.startswith(heading_line):
                    chunks.append(f"{heading_line}\n{sub_chunk}")
                else:
                    chunks.append(sub_chunk)
        return chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    norm_a = math.sqrt(_dot(vec_a, vec_a))
    norm_b = math.sqrt(_dot(vec_b, vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return _dot(vec_a, vec_b) / (norm_a * norm_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size, overlap=0).chunk(text),
            "by_sentences": SentenceChunker(max_sentences_per_chunk=3).chunk(text),
            "recursive": RecursiveChunker(chunk_size=chunk_size).chunk(text),
        }

        result: dict = {}
        for name, chunks in strategies.items():
            count = len(chunks)
            avg_length = sum(len(c) for c in chunks) / count if count else 0.0
            result[name] = {"count": count, "avg_length": avg_length, "chunks": chunks}
        return result
