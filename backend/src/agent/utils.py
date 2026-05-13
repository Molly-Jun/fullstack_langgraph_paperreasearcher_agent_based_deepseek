from pathlib import Path
from typing import Any

import fitz


WORKSPACE_ROOT = Path("./data")
PDF_DIR = WORKSPACE_ROOT / "pdf"
NOTE_DIR = WORKSPACE_ROOT / "note"
SUMMARY_DIR = WORKSPACE_ROOT / "summary"


def parse_pdf(pdf_path: str) -> list[dict[str, Any]]:
    document = fitz.open(pdf_path)
    chunks: list[dict[str, Any]] = []
    for page_number, page in enumerate(document, start=1):
        text = page.get_text("text").strip()
        if text:
            chunks.append({"page": page_number, "text": text, "section_title": f"Page {page_number}"})
    document.close()
    return chunks


def split_into_sections(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for chunk in chunks:
        sections.append(
            {
                "title": chunk["section_title"],
                "page_range": f"p.{chunk['page']}",
                "text": chunk["text"],
            }
        )
    return sections


def save_summary(paper_id: str, summary_md: str, summary_dir: str):
    paper_dir = Path(summary_dir)
    paper_dir.mkdir(parents=True, exist_ok=True)
    (paper_dir / f"{paper_id}.md").write_text(summary_md, encoding="utf-8")


def append_note(paper_id: str, qa_pair: dict, note_dir: str):
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


def get_relevant_chunks(pdf_chunks: list, question: str, top_k: int = 5) -> str:
    question_terms = {term.lower() for term in question.split() if term.strip()}
    scored_chunks: list[tuple[int, dict[str, Any]]] = []
    for chunk in pdf_chunks:
        text = chunk.get("text", "")
        score = sum(1 for term in question_terms if term in text.lower())
        scored_chunks.append((score, chunk))
    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    selected = [chunk for score, chunk in scored_chunks[:top_k] if score > 0]
    if not selected:
        selected = pdf_chunks[:top_k]
    return "\n\n".join(f"[p.{chunk['page']}] {chunk['text']}" for chunk in selected)


def workspace_root() -> Path:
    return WORKSPACE_ROOT


def workspace_uploads_dir() -> Path:
    return PDF_DIR


def workspace_summary_dir() -> Path:
    return SUMMARY_DIR


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
