from pathlib import Path
from typing import Any

import fitz


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


def save_summary(paper_id: str, summary_md: str, notes_dir: str):
    paper_dir = Path(notes_dir) / paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)
    (paper_dir / "summary.md").write_text(summary_md, encoding="utf-8")


def append_note(paper_id: str, qa_pair: dict, notes_dir: str):
    paper_dir = Path(notes_dir) / paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)
    note_path = paper_dir / "notes.md"
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
