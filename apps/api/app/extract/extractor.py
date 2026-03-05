from dataclasses import dataclass
import hashlib
import html
from html.parser import HTMLParser
import re


@dataclass(slots=True, frozen=True)
class ExtractedDocument:
    markdown: str
    title: str | None
    content_hash: str | None


NOISE_LINE_PATTERNS = (
    re.compile(r"\bcookie\b", re.IGNORECASE),
    re.compile(r"\bprivacy\b", re.IGNORECASE),
    re.compile(r"\bterms\b", re.IGNORECASE),
    re.compile(r"\bsubscribe\b", re.IGNORECASE),
    re.compile(r"\bnewsletter\b", re.IGNORECASE),
    re.compile(r"\bsign[\s-]?in\b", re.IGNORECASE),
    re.compile(r"\blog[\s-]?in\b", re.IGNORECASE),
    re.compile(r"\badvert", re.IGNORECASE),
    re.compile(r"\bsponsored\b", re.IGNORECASE),
    re.compile(r"\baccept all\b", re.IGNORECASE),
    re.compile(r"\ball rights reserved\b", re.IGNORECASE),
)

NOISE_ATTR_PATTERNS = (
    re.compile(r"cookie", re.IGNORECASE),
    re.compile(r"banner", re.IGNORECASE),
    re.compile(r"footer", re.IGNORECASE),
    re.compile(r"sidebar", re.IGNORECASE),
    re.compile(r"comment", re.IGNORECASE),
    re.compile(r"social", re.IGNORECASE),
    re.compile(r"share", re.IGNORECASE),
    re.compile(r"menu", re.IGNORECASE),
    re.compile(r"nav", re.IGNORECASE),
    re.compile(r"ads?", re.IGNORECASE),
    re.compile(r"newsletter", re.IGNORECASE),
)

IGNORE_TAGS = {
    "script",
    "style",
    "noscript",
    "svg",
    "canvas",
    "iframe",
    "nav",
    "footer",
    "aside",
    "form",
    "button",
    "input",
    "select",
    "option",
    "textarea",
}

BLOCK_TAGS = {"p", "br", "section", "article", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6"}


def extract_document(html_text: str, *, max_chars: int) -> ExtractedDocument:
    markdown, title = _extract_markdown(html_text)
    markdown = markdown.strip()
    if max_chars > 0:
        markdown = markdown[:max_chars].strip()

    content_hash = _sha256(markdown) if markdown else None
    return ExtractedDocument(markdown=markdown, title=title, content_hash=content_hash)


def chunk_passages(markdown: str, *, chunk_size: int = 900, overlap: int = 120) -> tuple[str, ...]:
    text = markdown.strip()
    if not text:
        return ()
    if chunk_size <= 0:
        return (text,)

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        paragraphs = [text]

    passages: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue

        candidate = f"{current}\n\n{paragraph}"
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        passages.append(current)
        tail = current[-overlap:] if overlap > 0 else ""
        current = f"{tail}\n\n{paragraph}".strip()
        if len(current) > chunk_size:
            passages.extend(_hard_split(current, chunk_size, overlap))
            current = ""

    if current:
        passages.append(current)

    return tuple(part.strip() for part in passages if part.strip())


def _hard_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return [chunk for chunk in chunks if chunk]


def _extract_markdown(html_text: str) -> tuple[str, str | None]:
    trafilatura_result = _try_trafilatura(html_text)
    if trafilatura_result is not None:
        return trafilatura_result

    readability_result = _try_readability(html_text)
    if readability_result is not None:
        return readability_result

    parser = _PlainTextParser()
    parser.feed(html_text)
    parser.close()
    title = parser.title.strip() if parser.title else None
    raw_text = parser.text.strip()
    cleaned = _cleanup_fallback_text(raw_text)
    return cleaned, title


def _try_trafilatura(html_text: str) -> tuple[str, str | None] | None:
    try:
        import trafilatura  # type: ignore
    except ImportError:
        return None

    extracted = trafilatura.extract(
        html_text,
        output_format="markdown",
        include_links=True,
        include_formatting=True,
        include_tables=False,
    )
    if not extracted:
        return None
    return extracted.strip(), None


def _try_readability(html_text: str) -> tuple[str, str | None] | None:
    try:
        from readability import Document  # type: ignore
    except ImportError:
        return None

    doc = Document(html_text)
    parser = _PlainTextParser()
    parser.feed(doc.summary(html_partial=True))
    parser.close()
    content = _cleanup_fallback_text(parser.text.strip())
    if not content:
        return None
    title = doc.short_title() or None
    return content, title


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._ignore_depth = 0
        self._chunks: list[str] = []
        self._capture_title = False
        self._title_parts: list[str] = []

    @property
    def text(self) -> str:
        text = "".join(self._chunks)
        text = html.unescape(text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    @property
    def title(self) -> str:
        return html.unescape("".join(self._title_parts)).strip()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._capture_title = True
            return
        if self._ignore_depth > 0:
            self._ignore_depth += 1
            return
        if tag in IGNORE_TAGS or _has_noise_attrs(attrs):
            self._ignore_depth = 1
            return
        if tag in BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._capture_title = False
            return
        if self._ignore_depth > 0:
            self._ignore_depth -= 1
            return
        if tag in {"p", "section", "article", "div", "li"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self._title_parts.append(data)
            return
        if self._ignore_depth > 0:
            return
        normalized = re.sub(r"\s+", " ", data)
        if normalized.strip():
            self._chunks.append(normalized)


def _has_noise_attrs(attrs: list[tuple[str, str | None]]) -> bool:
    for key, value in attrs:
        if key is None or value is None:
            continue
        key_lower = key.lower()
        if key_lower not in {"id", "class", "role", "aria-label"}:
            continue
        for pattern in NOISE_ATTR_PATTERNS:
            if pattern.search(value):
                return True
    return False


def _cleanup_fallback_text(text: str) -> str:
    candidate = text.strip()
    if not candidate:
        return ""

    lines = [line.strip() for line in candidate.splitlines() if line.strip()]
    filtered: list[str] = []
    short_seen: set[str] = set()
    for line in lines:
        normalized_line = re.sub(r"\s+", " ", line).strip()
        if not normalized_line:
            continue
        if _is_noise_line(normalized_line):
            continue
        if len(normalized_line) <= 60:
            lowered = normalized_line.lower()
            if lowered in short_seen:
                continue
            short_seen.add(lowered)
        filtered.append(normalized_line)

    if not filtered:
        return candidate
    cleaned = "\n".join(filtered).strip()

    # Keep content-preserving fallback behavior if cleanup removes too much.
    if len(cleaned) < max(180, int(len(candidate) * 0.55)):
        return candidate
    return cleaned


def _is_noise_line(line: str) -> bool:
    if len(line) <= 48 and line.count("|") >= 2:
        return True
    if len(line) <= 40 and line.count("·") >= 2:
        return True
    for pattern in NOISE_LINE_PATTERNS:
        if pattern.search(line):
            return True
    return False
