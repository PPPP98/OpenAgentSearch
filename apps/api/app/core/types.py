from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class SearchRequest:
    query: str
    limit: int = 10
    page: int = 1
    categories: tuple[str, ...] = field(default_factory=tuple)
    engines: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        query = self.query.strip()
        if not query:
            raise ValueError("query must not be empty")
        if not 1 <= self.limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        if self.page < 1:
            raise ValueError("page must be >= 1")

        categories = tuple(cat.strip() for cat in self.categories if cat and cat.strip())
        engines = tuple(engine.strip() for engine in self.engines if engine and engine.strip())
        object.__setattr__(self, "query", query)
        object.__setattr__(self, "categories", categories)
        object.__setattr__(self, "engines", engines)


@dataclass(slots=True, frozen=True)
class SearchResult:
    url: str
    title: str
    snippet: str = ""
    source: str | None = None
    score: float | None = None

    def __post_init__(self) -> None:
        url = self.url.strip()
        if not url:
            raise ValueError("url must not be empty")
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "title", self.title.strip())
        object.__setattr__(self, "snippet", self.snippet.strip())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip() or None)


@dataclass(slots=True, frozen=True)
class ExtractRequest:
    url: str
    max_chars: int = 20_000

    def __post_init__(self) -> None:
        url = self.url.strip()
        if not url:
            raise ValueError("url must not be empty")
        if self.max_chars < 1:
            raise ValueError("max_chars must be >= 1")
        object.__setattr__(self, "url", url)


@dataclass(slots=True, frozen=True)
class ExtractResult:
    url: str
    markdown: str
    passages: tuple[str, ...] = field(default_factory=tuple)
    title: str | None = None
    content_hash: str | None = None

    def __post_init__(self) -> None:
        url = self.url.strip()
        if not url:
            raise ValueError("url must not be empty")
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "markdown", self.markdown.strip())
        normalized_passages = tuple(p.strip() for p in self.passages if p and p.strip())
        object.__setattr__(self, "passages", normalized_passages)
        if self.title is not None:
            object.__setattr__(self, "title", self.title.strip() or None)
        if self.content_hash is not None:
            object.__setattr__(self, "content_hash", self.content_hash.strip() or None)
