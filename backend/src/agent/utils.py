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

GLOBAL_NOTE_FILENAME = "note.md"

MIN_SECTION_CHARS = 300
MAX_SECTION_CHARS = 8000


def parse_pdf_to_markdown(pdf_path: str) -> str:
    """使用 pymupdf4llm 把 PDF 转为带结构的 Markdown 文本。"""
    return pymupdf4llm.to_markdown(pdf_path)


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"\n{3,}", "\n\n", text)
    return cleaned.strip()


def split_markdown_sections(markdown_text: str) -> list[dict[str, Any]]:
    """按 #/##/### 标题进行语义切分，并对过短章节做合并。引用以章节名为锚点。"""
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
                "text": _normalize_text(content),
            }
        )

    if not raw_sections:
        normalized = _normalize_text(markdown_text)
        return [{"title": "Document", "text": normalized}]

    merged: list[dict[str, Any]] = []
    for section in raw_sections:
        if merged and len(section["text"]) < MIN_SECTION_CHARS:
            previous = merged[-1]
            previous["text"] = f"{previous['text']}\n\n{section['text']}"
            continue
        merged.append(section)

    final: list[dict[str, Any]] = []
    for section in merged:
        text = section["text"]
        if len(text) <= MAX_SECTION_CHARS:
            final.append(section)
            continue
        chunks = _hard_chunk(text, MAX_SECTION_CHARS)
        for sub_index, chunk in enumerate(chunks, start=1):
            final.append(
                {
                    "title": f"{section['title']} ({sub_index})",
                    "text": chunk,
                }
            )
    return final


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


def parse_pdf(pdf_path: str) -> list[dict[str, Any]]:
    """对外保留的 PDF -> sections 切分入口。"""
    markdown_text = parse_pdf_to_markdown(pdf_path)
    return split_markdown_sections(markdown_text)


def split_into_sections(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """兼容旧接口：直接转换为 graph 节点期望的 sections 列表。"""
    return [
        {"title": chunk.get("title", ""), "text": chunk.get("text", "")}
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


def save_summary(paper_id: str, summary_md: str, summary_dir: str):
    paper_dir = Path(summary_dir)
    paper_dir.mkdir(parents=True, exist_ok=True)
    (paper_dir / f"{paper_id}.md").write_text(summary_md, encoding="utf-8")


def append_note(paper_id: str, qa_pair: dict, note_dir: str):
    """旧版：把单个 Q&A 追加进全局笔记文件 note.md。"""
    del paper_id  # 全局笔记不再按 paper_id 拆分文件，参数仅作向后兼容
    target_dir = Path(note_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    note_path = target_dir / GLOBAL_NOTE_FILENAME
    note = (
        f"## Q: {qa_pair['question']}\n\n"
        f"**A:** {qa_pair['answer']}\n\n"
        f"**引用：** {', '.join(qa_pair.get('citations', []))}\n\n---\n"
    )
    existing = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
    note_path.write_text(existing + note, encoding="utf-8")


def append_structured_note(note_markdown: str, note_dir: str | None = None) -> str:
    """把结构化笔记追加到统一的 data/note/note.md。"""
    target_dir = Path(note_dir) if note_dir else NOTE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    note_path = target_dir / GLOBAL_NOTE_FILENAME
    existing = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
    separator = "\n\n---\n\n" if existing.strip() else ""
    note_path.write_text(existing + separator + note_markdown.strip() + "\n", encoding="utf-8")
    return str(note_path)


def build_note_frontmatter(paper_title: str, one_line_summary: str) -> str:
    """精简版 frontmatter：仅保留时间、文献名、一句话摘要。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_title = paper_title.replace('"', "'")
    safe_summary = one_line_summary.replace('"', "'").replace("\n", " ")
    return (
        "---\n"
        f"timestamp: \"{timestamp}\"\n"
        f"paper_title: \"{safe_title}\"\n"
        f"one_line_summary: \"{safe_summary}\"\n"
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


def workspace_global_note_path() -> Path:
    return NOTE_DIR / GLOBAL_NOTE_FILENAME


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
    del paper_id  # 当前全部论文共用一套目录，参数仅作向后兼容
    ensure_workspace_dirs()
    return PDF_DIR, SUMMARY_DIR


def _global_note_exists() -> bool:
    return (NOTE_DIR / GLOBAL_NOTE_FILENAME).is_file()


def scan_workspace() -> list[dict[str, Any]]:
    ensure_workspace_dirs()
    resources: list[dict[str, Any]] = []
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    notes_present = _global_note_exists()
    notes_path_str = str(NOTE_DIR / GLOBAL_NOTE_FILENAME) if notes_present else None
    for pdf_path in pdf_files:
        paper_id = pdf_path.stem
        summary_path = SUMMARY_DIR / f"{paper_id}.md"
        resources.append(
            {
                "paper_id": paper_id,
                "title": pdf_path.stem,
                "pdf_path": str(pdf_path),
                "has_summary": summary_path.exists(),
                "has_notes": notes_present,
                "summary_path": str(summary_path) if summary_path.exists() else None,
                "notes_path": notes_path_str,
            }
        )
    return resources


def get_workspace_document(paper_id: str) -> dict[str, Any] | None:
    ensure_workspace_dirs()
    pdf_path = PDF_DIR / f"{paper_id}.pdf"
    if not pdf_path.is_file():
        return None
    summary_path = SUMMARY_DIR / f"{paper_id}.md"
    notes_present = _global_note_exists()
    return {
        "paper_id": paper_id,
        "title": pdf_path.stem,
        "pdf_path": str(pdf_path),
        "has_summary": summary_path.exists(),
        "has_notes": notes_present,
        "summary_path": str(summary_path) if summary_path.exists() else None,
        "notes_path": str(NOTE_DIR / GLOBAL_NOTE_FILENAME) if notes_present else None,
    }
