from __future__ import annotations

import re
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Comment

# -----------------------------
# WeChat HTML -> Clean Markdown
# -----------------------------
# deps:
#   pip install beautifulsoup4 lxml
#
# usage:
#   wechat_html_to_markdown("input.html", "output.md")

FONT_RE = re.compile(r"font-size\s*:\s*([0-9.]+)\s*(px|pt)", re.I)


def _parse_font_px(style: str) -> float | None:
    m = FONT_RE.search(style or "")
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2).lower()
    return val if unit == "px" else val * 4.0 / 3.0  # 1pt ~ 1.333px


def _max_font_px(tag) -> float:
    """Find max font-size in px among tag + common inline descendants (cheap heuristic)."""
    mx = 0.0
    for t in [tag] + tag.find_all(["span", "strong", "b", "em", "i", "font"], recursive=True):
        style = t.get("style")
        if style:
            px = _parse_font_px(style)
            if px:
                mx = max(mx, px)
                if mx >= 24:
                    break
    return mx


def _clean_text(s: str) -> str:
    """Normalize whitespace but keep newlines."""
    s = s.replace("\u00a0", " ").replace("\u200b", "")
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s


def _inline_md(node) -> str:
    """Convert inline nodes to Markdown inline text (drops links/images/scripts)."""
    if isinstance(node, Comment):
        return ""
    if isinstance(node, NavigableString):
        return str(node)

    if not hasattr(node, "name") or node.name is None:
        return ""
    name = node.name.lower()

    if name in {"script", "style", "noscript"}:
        return ""
    if name in {"img", "figure", "video", "audio", "source", "iframe", "canvas", "svg"}:
        return ""
    if name == "br":
        return "\n"
    if name == "a":
        # keep only visible text, drop href to avoid leaking tracking params
        return "".join(_inline_md(c) for c in node.children)
    if name in {"strong", "b"}:
        txt = "".join(_inline_md(c) for c in node.children).strip()
        return f"**{txt}**" if txt else ""
    if name in {"em", "i"}:
        txt = "".join(_inline_md(c) for c in node.children).strip()
        return f"*{txt}*" if txt else ""
    if name == "code" and (not node.parent or (node.parent.name or "").lower() != "pre"):
        txt = node.get_text().replace("`", r"\`")
        return f"`{txt}`"

    return "".join(_inline_md(c) for c in node.children)


def _looks_like_heading(p_tag) -> tuple[bool, int]:
    """
    Conservative heuristic:
    - short text
    - mostly bold OR large font-size
    """
    text = p_tag.get_text(" ", strip=True)
    if not text or len(text) > 60:
        return (False, 0)

    bold_text = "".join(b.get_text(" ", strip=True) for b in p_tag.find_all(["strong", "b"]))
    bold_ratio = len(bold_text) / max(1, len(text))
    max_px = _max_font_px(p_tag)

    if bold_ratio >= 0.85 or max_px >= 16:
        if max_px >= 22:
            return (True, 2)
        if max_px >= 18:
            return (True, 3)
        if bold_ratio >= 0.95 and len(text) <= 30:
            return (True, 3)
        if bold_ratio >= 0.85 and len(text) <= 20:
            return (True, 4)

    return (False, 0)


def _li_to_md(li_tag, *, list_level: int, ordered: bool, index: int) -> str:
    nested_lists = []
    content_parts = []
    for c in li_tag.children:
        if hasattr(c, "name") and c.name and c.name.lower() in {"ul", "ol"}:
            nested_lists.append(c)
        else:
            content_parts.append(c)

    text = _clean_text("".join(_inline_md(c) for c in content_parts)).strip()
    if not text and not nested_lists:
        return ""

    indent = "  " * list_level
    prefix = f"{index}. " if ordered else "- "
    line = f"{indent}{prefix}{text}".rstrip() + "\n"

    nested_md = ""
    for nl in nested_lists:
        nested_md += _to_md(nl, list_level=list_level + 1)
    return line + nested_md


def _to_md(node, *, list_level: int = 0) -> str:
    """Convert block-ish nodes to Markdown."""
    if isinstance(node, Comment):
        return ""
    if isinstance(node, NavigableString):
        return str(node)

    if not hasattr(node, "name") or node.name is None:
        return ""
    name = node.name.lower()

    # hard drop
    if name in {"script", "style", "noscript", "img", "figure", "video", "audio", "source", "iframe", "canvas", "svg"}:
        return ""

    # containers
    if name in {"article", "div", "section"}:
        return "".join(_to_md(c, list_level=list_level) for c in node.children)

    # headings
    if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = int(name[1])
        text = _clean_text("".join(_inline_md(c) for c in node.children)).strip()
        return f"{'#' * level} {text}\n\n" if text else ""

    # paragraph (with heading heuristic)
    if name == "p":
        text_plain = node.get_text(" ", strip=True)
        if not text_plain:
            return ""
        is_h, lvl = _looks_like_heading(node)
        if is_h:
            return f"{'#' * lvl} {_clean_text(text_plain).strip()}\n\n"
        text = _clean_text("".join(_inline_md(c) for c in node.children)).strip()
        return f"{text}\n\n" if text else ""

    # blockquote
    if name == "blockquote":
        inner = _clean_text("".join(_to_md(c, list_level=list_level) for c in node.children)).strip()
        if not inner:
            return ""
        lines = [ln for ln in inner.splitlines() if ln.strip()]
        return "\n".join([f"> {ln}" for ln in lines]) + "\n\n"

    # lists
    if name == "ul":
        items = [
            _li_to_md(li, list_level=list_level, ordered=False, index=1)
            for li in node.find_all("li", recursive=False)
        ]
        return "".join(items) + ("\n" if any(items) else "")

    if name == "ol":
        items = []
        for idx, li in enumerate(node.find_all("li", recursive=False), start=1):
            items.append(_li_to_md(li, list_level=list_level, ordered=True, index=idx))
        return "".join(items) + ("\n" if items else "")

    # code block
    if name == "pre":
        code = node.get_text().rstrip("\n")
        return f"```\n{code}\n```\n\n" if code.strip() else ""

    # table (minimal: TSV lines)
    if name == "table":
        rows = []
        for tr in node.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if any(cells):
                rows.append("\t".join(cells))
        return ("\n".join(rows) + "\n\n") if rows else ""

    if name == "hr":
        return "\n---\n\n"

    # default: recurse
    return "".join(_to_md(c, list_level=list_level) for c in node.children)


def wechat_html_to_markdown(src_html_path: str, out_md_path: str) -> None:
    """
    Convert a downloaded WeChat public-account HTML file into clean, structured Markdown.
    - No images
    - Drops link hrefs to avoid tracking parameters
    - Preserves headings/paragraphs/lists/quotes/code/table (best-effort)
    """
    html = Path(src_html_path).read_text(encoding="utf-8", errors="ignore")

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # Title (WeChat common)
    title_tag = soup.select_one("#activity-name") or soup.select_one(".rich_media_title") or soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else ""

    # Main content (WeChat common)
    content = (
        soup.select_one("#js_content")
        or soup.select_one("div.rich_media_content")
        or soup.select_one("#img-content")
        or soup.body
        or soup
    )

    # Remove comments
    for c in content.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()

    # Remove noisy tags (and images)
    for tag in content.find_all(
        ["script", "style", "noscript", "iframe", "form", "input", "button", "textarea", "select", "option",
         "img", "figure", "video", "audio", "source", "canvas", "svg"]
    ):
        tag.decompose()

    # Unwrap links: keep only visible text, drop href
    for a in content.find_all("a"):
        a.replace_with(a.get_text(" ", strip=True))

    # Strip all attributes for cleanliness/privacy (keeps structure)
    for tag in content.find_all(True):
        tag.attrs = {}

    md = _clean_text(_to_md(content)).strip()
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"

    # Prepend title as H1 if not already present
    if title:
        first_line = md.splitlines()[0].strip() if md.splitlines() else ""
        if not (first_line.startswith("# ") and first_line[2:].strip() == title):
            md = f"# {title}\n\n" + md

    out_path = Path(out_md_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python wechat_clean.py <src.html> <out.md>")
        raise SystemExit(2)

    wechat_html_to_markdown(sys.argv[1], sys.argv[2])
