from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pymupdf4llm
from langchain_text_splitters import MarkdownHeaderTextSplitter


WORKSPACE_ROOT = Path("./data")
PDF_DIR = WORKSPACE_ROOT / "pdf"
NOTE_DIR = WORKSPACE_ROOT / "note"
SUMMARY_DIR = WORKSPACE_ROOT / "summary"
MARKDOWN_DIR = WORKSPACE_ROOT / "markdown"

MIN_SECTION_CHARS = 300
MAX_SECTION_CHARS = 6000


def parse_pdf_to_markdown(pdf_path: str) -> str:
    """使用 pymupdf4llm 把 PDF 转为带结构的 Markdown 文本。"""
    return pymupdf4llm.to_markdown(pdf_path)


def _infer_page_range(text: str, fallback_index: int) -> str:
    """根据 pymupdf4llm 输出中的页码标记推断页码范围。"""
    matches = re.findall(r"\{(\d+)\}", text) + re.findall(r"\[page\s*(\d+)\]", text, flags=re.IGNORECASE)
    pages = sorted({int(m) for m in matches if m.isdigit()})
    if not pages:
        return f"section-{fallback_index}"
    if len(pages) == 1:
        return f"p.{pages[0]}"
    return f"p.{pages[0]}-{pages[-1]}"


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"\{\d+\}", "", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def split_markdown_sections(markdown_text: str) -> list[dict[str, Any]]:
    """按 #/##/### 标题进行语义切分，并对过短章节做合并。"""
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ],
        strip_headers=False,
    )
    documents = splitter.split_text(markdown_text)
    raw_sections: list[dict[str, Any]] = []
    for index, document in enumerate(documents, start=1):
        metadata = document.metadata or {}
        title = (
            metadata.get("h3")
            or metadata.get("h2")
            or metadata.get("h1")
            or f"Section {index}"
        )
        content = document.page_content.strip()
        if not content:
            continue
        raw_sections.append(
            {
                "title": title,
                "page_range": _infer_page_range(content, index),
                "text": _normalize_text(content),
            }
        )

    if not raw_sections:
        normalized = _normalize_text(markdown_text)
        return [
            {
                "title": "Document",
                "page_range": "p.1",
                "text": normalized,
            }
        ]

    merged: list[dict[str, Any]] = []
    for section in raw_sections:
        if merged and len(section["text"]) < MIN_SECTION_CHARS:
            previous = merged[-1]
            previous["text"] = f"{previous['text']}\n\n{section['text']}"
            previous["page_range"] = _merge_page_range(previous["page_range"], section["page_range"])
            continue
        merged.append(section)

    truncated: list[dict[str, Any]] = []
    for section in merged:
        text = section["text"]
        if len(text) <= MAX_SECTION_CHARS:
            truncated.append(section)
            continue
        chunks = _hard_chunk(text, MAX_SECTION_CHARS)
        for sub_index, chunk in enumerate(chunks, start=1):
            truncated.append(
                {
                    "title": f"{section['title']} ({sub_index})",
                    "page_range": section["page_range"],
                    "text": chunk,
                }
            )
    return truncated


def _hard_chunk(text: str, limit: int) -> list[str]:
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 2 <= limit:
            buffer = f"{buffer}\n\n{paragraph}".strip()
        else:
            if buffer:
                chunks.append(buffer)
            buffer = paragraph
    if buffer:
        chunks.append(buffer)
    return chunks


def _merge_page_range(left: str, right: str) -> str:
    left_pages = [int(x) for x in re.findall(r"\d+", left)]
    right_pages = [int(x) for x in re.findall(r"\d+", right)]
    pages = sorted(set(left_pages + right_pages))
    if not pages:
        return left
    if len(pages) == 1:
        return f"p.{pages[0]}"
    return f"p.{pages[0]}-{pages[-1]}"


def parse_pdf(pdf_path: str) -> list[dict[str, Any]]:
    """对外保留的 PDF -> sections 切分入口。"""
    markdown_text = parse_pdf_to_markdown(pdf_path)
    return split_markdown_sections(markdown_text)


def split_into_sections(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """兼容旧接口：直接转换为 graph 节点期望的 sections 列表。"""
    return [
        {
            "title": chunk.get("title", ""),
            "page_range": chunk.get("page_range", ""),
            "text": chunk.get("text", ""),
        }
        for chunk in chunks
    ]


def load_paper_full_markdown(paper_id: str) -> str:
    """读取或生成完整的 Markdown 文本，供 QA / Note 链路做全量上下文。"""
    ensure_workspace_dirs()
    cache_path = MARKDOWN_DIR / f"{paper_id}.md"
    if cache_path.is_file():
        return cache_path.read_text(encoding="utf-8")
    pdf_path = PDF_DIR / f"{paper_id}.pdf"
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found for paper_id={paper_id}")
    markdown_text = parse_pdf_to_markdown(str(pdf_path))
    cache_path.write_text(markdown_text, encoding="utf-8")
    return markdown_text


def truncate_markdown(markdown_text: str, limit: int = 60000) -> str:
    """超长 Markdown 做软截断，避免超出模型上下文。"""
    if len(markdown_text) <= limit:
        return markdown_text
    head = markdown_text[: int(limit * 0.7)]
    tail = markdown_text[-int(limit * 0.3):]
    return f"{head}\n\n[...内容过长，已截断中部...]\n\n{tail}"


def save_summary(paper_id: str, summary_md: str, summary_dir: str):
    paper_dir = Path(summary_dir)
    paper_dir.mkdir(parents=True, exist_ok=True)
    (paper_dir / f"{paper_id}.md").write_text(summary_md, encoding="utf-8")


def append_note(paper_id: str, qa_pair: dict, note_dir: str):
    """旧版：把单个 Q&A 追加进笔记文件，新流程仍可使用。"""
    paper_dir = Path(note_dir)
    paper_dir.mkdir(parents=True, exist_ok=True)
    note_path = paper_dir / f"{paper_id}_notes.md"
    note = (
        f"## Q: {qa_pair['question']}\n\n"
        f"**A:** {qa_pair['answer']}\n\n"
        f"**引用：** {', '.join(qa_pair.get('citations', []))}\n\n---\n"
    )
    existing = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
    note_path.write_text(existing + note, encoding="utf-8")


def append_structured_note(paper_id: str, note_markdown: str, note_dir: str | None = None) -> str:
    """把结构化笔记（含 YAML frontmatter）追加到 data/note/<paper_id>_notes.md。"""
    target_dir = Path(note_dir) if note_dir else NOTE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    note_path = target_dir / f"{paper_id}_notes.md"
    existing = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
    separator = "\n\n---\n\n" if existing.strip() else ""
    note_path.write_text(existing + separator + note_markdown.strip() + "\n", encoding="utf-8")
    return str(note_path)


def build_note_frontmatter(
    paper_id: str,
    paper_title: str,
    one_line_summary: str,
    tags: list[str],
) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_title = paper_title.replace('"', "'")
    safe_summary = one_line_summary.replace('"', "'").replace("\n", " ")
    tag_block = ", ".join(f'"{tag}"' for tag in tags) if tags else ""
    return (
        "---\n"
        f"timestamp: \"{timestamp}\"\n"
        f"paper_id: \"{paper_id}\"\n"
        f"paper_title: \"{safe_title}\"\n"
        f"one_line_summary: \"{safe_summary}\"\n"
        f"tags: [{tag_block}]\n"
        "---\n"
    )


def format_history_window(messages: list[dict[str, Any]] | None, limit: int = 10) -> str:
    """把最近 N 轮对话格式化成 Markdown 文本。"""
    if not messages:
        return "（暂无历史对话）"
    recent = messages[-limit:]
    rendered: list[str] = []
    for msg in recent:
        role = msg.get("type") or msg.get("role") or "user"
        content = msg.get("content", "")
        if isinstance(content, list):
            content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
        role_label = "用户" if role in {"human", "user"} else "助手"
        rendered.append(f"**{role_label}:** {content}".strip())
    return "\n\n".join(rendered) or "（暂无历史对话）"


def filter_history_by_keyword(messages: list[dict[str, Any]] | None, keyword: str) -> list[dict[str, Any]]:
    """按关键字过滤历史消息（笔记定向抽取使用）。"""
    if not messages:
        return []
    if not keyword:
        return list(messages)
    keyword_lc = keyword.lower()
    return [
        msg
        for msg in messages
        if keyword_lc in str(msg.get("content", "")).lower()
    ]


def workspace_root() -> Path:
    return WORKSPACE_ROOT


def workspace_uploads_dir() -> Path:
    return PDF_DIR


def workspace_summary_dir() -> Path:
    return SUMMARY_DIR


def workspace_note_dir() -> Path:
    return NOTE_DIR


def safe_parse_pdf(pdf_path: str) -> list[dict[str, Any]]:
    try:
        pdf_file = Path(pdf_path)
        if not pdf_file.is_file():
            return []
        return parse_pdf(pdf_path)
    except Exception:
        return []


def ensure_workspace_dirs() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    NOTE_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)


def ensure_paper_workspace_dirs(paper_id: str) -> tuple[Path, Path]:
    ensure_workspace_dirs()
    return PDF_DIR, SUMMARY_DIR


def scan_workspace() -> list[dict[str, Any]]:
    ensure_workspace_dirs()
    resources: list[dict[str, Any]] = []
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    for pdf_path in pdf_files:
        paper_id = pdf_path.stem
        summary_path = SUMMARY_DIR / f"{paper_id}.md"
        notes_path = NOTE_DIR / f"{paper_id}_notes.md"
        resources.append(
            {
                "paper_id": paper_id,
                "title": pdf_path.stem,
                "pdf_path": str(pdf_path),
                "has_summary": summary_path.exists(),
                "has_notes": notes_path.exists(),
                "summary_path": str(summary_path) if summary_path.exists() else None,
                "notes_path": str(notes_path) if notes_path.exists() else None,
            }
        )
    return resources


def get_workspace_document(paper_id: str) -> dict[str, Any] | None:
    ensure_workspace_dirs()
    pdf_path = PDF_DIR / f"{paper_id}.pdf"
    if not pdf_path.is_file():
        return None
    summary_path = SUMMARY_DIR / f"{paper_id}.md"
    notes_path = NOTE_DIR / f"{paper_id}_notes.md"
    return {
        "paper_id": paper_id,
        "title": pdf_path.stem,
        "pdf_path": str(pdf_path),
        "has_summary": summary_path.exists(),
        "has_notes": notes_path.exists(),
        "summary_path": str(summary_path) if summary_path.exists() else None,
        "notes_path": str(notes_path) if notes_path.exists() else None,
    }
