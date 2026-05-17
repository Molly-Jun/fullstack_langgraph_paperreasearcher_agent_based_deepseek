from __future__ import annotations

import operator
from typing_extensions import Annotated, TypedDict

from langgraph.graph import add_messages


# ---------------------------------------------------------------------
# Summary 链路状态
# ---------------------------------------------------------------------


class OverallState(TypedDict, total=False):
    """Summary 主图共享状态（保留旧字段以兼容历史代码）。"""

    messages: Annotated[list, add_messages]
    paper_id: str
    paper_title: str
    mode: str
    summary_prompts: str
    pdf_path: str
    pdf_markdown: str
    pdf_chunks: list[dict]
    sections: list[dict]
    summary_dir: str
    note_dir: str
    section_title: str
    section_text: str
    section_summaries: Annotated[list, operator.add]
    final_summary: str
    user_question: str
    is_complete: bool
    missing_aspects: str
    follow_up_sections: list[str]


class ParseState(TypedDict, total=False):
    pdf_path: str
    paper_id: str
    summary_prompts: str
    user_question: str


class SectionState(TypedDict, total=False):
    section_title: str
    section_text: str
    paper_id: str
    summary_prompts: str


class ReflectionState(TypedDict, total=False):
    is_complete: bool
    missing_aspects: str
    follow_up_sections: list[str]


# ---------------------------------------------------------------------
# QA 链路状态（独立）
# ---------------------------------------------------------------------


class QAState(TypedDict, total=False):
    paper_id: str
    paper_title: str
    pdf_markdown: str
    user_question: str
    qa_history_window: list[dict]
    qa_plan: dict
    qa_plan_approved: bool
    qa_draft: str
    qa_draft_citations: list[str]
    qa_draft_confidence: str
    qa_critic_result: dict
    qa_revision_count: int
    qa_final_answer: str
    citations: list[str]
    confidence: str
    qa_interrupt_payload: dict


# ---------------------------------------------------------------------
# Note 链路状态（独立）
# ---------------------------------------------------------------------


class NoteState(TypedDict, total=False):
    paper_id: str
    paper_title: str
    pdf_markdown: str
    qa_history_window: list[dict]
    note_keyword: str
    note_plan: dict
    note_draft: str
    note_critic_result: dict
    note_revision_count: int
    final_note: str
    note_path: str
