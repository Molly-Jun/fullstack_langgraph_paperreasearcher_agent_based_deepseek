from __future__ import annotations

import operator
from typing_extensions import Annotated, TypedDict

from langgraph.graph import add_messages


class OverallState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    paper_id: str
    paper_title: str
    mode: str
    summary_prompts: str
    pdf_path: str
    pdf_chunks: list[dict]
    sections: list[dict]
    notes_dir: str
    section_title: str
    section_text: str
    page_range: str
    section_summaries: Annotated[list, operator.add]
    final_summary: str
    user_question: str
    relevant_chunks: str
    answer: str
    citations: list[str]
    confidence: str


class ParseState(TypedDict):
    pdf_path: str
    paper_id: str
    summary_prompts: str
    user_question: str


class SectionState(TypedDict):
    section_title: str
    section_text: str
    page_range: str
    paper_id: str
    summary_prompts: str


class ReflectionState(TypedDict):
    is_complete: bool
    missing_aspects: str
    follow_up_sections: list[str]
