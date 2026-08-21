from pathlib import Path
from typing import TypedDict
from markdown_it import MarkdownIt


class HeadingInfo(TypedDict):
    level: int
    title: str
    line: int


def _load_content(source: str | Path) -> str:
    """Load Markdown from a file path or return the string directly."""
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8")
    if "\n" not in source and Path(source).is_file():
        return Path(source).read_text(encoding="utf-8")
    return source


def get_all_headings(source: str | Path) -> list[HeadingInfo]:
    """Return all headings in a Markdown source as a list.

    :param source: File path (str/Path) or Markdown text.
    :return: List of dictionaries with 'level', 'title', and 'line' (0-based).
    """
    md_text = _load_content(source)
    md_it = MarkdownIt()
    tokens = md_it.parse(md_text)

    headings: list[HeadingInfo] = []

    for i, token in enumerate(tokens):
        if token.type == "heading_open":
            level = int(token.tag[1:])
            inline_token = tokens[i + 1]
            title = inline_token.content.strip()

            headings.append({
                "level": level,
                "title": title,
            })

    return headings


def get_section(
    source: str | Path,
    target_heading: str,
    include_subsections: bool = True,
    include_heading: bool = True
) -> str | None:
    """Extract the content of a specific section by its title.

    :param source: File path (str/Path) or Markdown text.
    :param target_heading: Requested heading title (without '#').
    :param include_subsections: If True, include deeper subsections. If False,
        stop at the next heading.
    :param include_heading: Whether to include the target heading in the result.
    :return: Extracted Markdown section or None if not found.
    """
    md_text = _load_content(source)
    md_it = MarkdownIt()
    tokens = md_it.parse(md_text)
    lines = md_text.splitlines()

    target_level: int | None = None
    start_line: int | None = None
    content_start_line: int | None = None
    end_line: int = len(lines)

    for i, token in enumerate(tokens):
        if token.type == "heading_open":
            level = int(token.tag[1:])
            title = tokens[i + 1].content.strip()

            if target_level is None and title.lower() == target_heading.strip().lower():
                target_level = level
                start_line = token.map[0] if token.map else 0
                content_start_line = token.map[1] if token.map else start_line + 1
                continue

            if target_level is not None:
                is_boundary = (level <= target_level) if include_subsections else True
                if is_boundary:
                    end_line = token.map[0] if token.map else len(lines)
                    break

    if target_level is None or start_line is None:
        return None

    actual_start = start_line if include_heading else (content_start_line or start_line)
    return "\n".join(lines[actual_start:end_line]).strip()

