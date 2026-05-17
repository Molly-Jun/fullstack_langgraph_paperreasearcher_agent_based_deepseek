from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from agent.configuration import Configuration
from agent.prompts import (
    final_summary_instructions,
    note_critic_instructions,
    note_drafter_instructions,
    note_planner_instructions,
    qa_critic_instructions,
    qa_drafter_instructions,
    qa_planner_instructions,
    section_summarizer_instructions,
    summary_prompts,
    summary_reflection_instructions,
)
from agent.state import (
    NoteState,
    OverallState,
    ParseState,
    QAState,
    ReflectionState,
    SectionState,
)
from agent.tools_and_schemas import (
    NoteCriticResult,
    NotePlan,
    QACriticResult,
    QADraft,
    QAPlan,
    ReflectionResult,
    SectionSummary,
)
from agent.utils import (
    append_structured_note,
    build_note_frontmatter,
    filter_history_by_keyword,
    format_history_window,
    parse_pdf,
    save_summary,
    split_into_sections,
)


MAX_QA_REVISIONS = 2
MAX_NOTE_REVISIONS = 2


def _make_llm(model_name: str):
    return ChatOpenAI(
        model=model_name,
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1",
        temperature=0,
        max_retries=3,
        timeout=90,
    )


# =====================================================================
# Summary 子图
# =====================================================================


def load_and_chunk(state: ParseState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    chunks = parse_pdf(state["pdf_path"])
    paper_title = Path(state["pdf_path"]).stem
    document_markdown = "\n\n".join(chunk["text"] for chunk in chunks)
    return {
        "paper_id": state["paper_id"],
        "paper_title": paper_title,
        "pdf_path": state["pdf_path"],
        "pdf_markdown": document_markdown,
        "pdf_chunks": chunks,
        "section_summaries": [],
        "final_summary": "",
        "summary_prompts": state.get("summary_prompts", summary_prompts["summary"]),
        "summary_dir": configurable.summary_dir,
        "note_dir": configurable.note_dir,
        "sections": split_into_sections(chunks),
        "user_question": state.get("user_question", ""),
    }


def continue_to_sections(state: OverallState):
    return [
        Send(
            "summarize_section",
            {
                "section_title": section["title"],
                "section_text": section["text"],
                "paper_id": state["paper_id"],
                "summary_prompts": state.get("summary_prompts", summary_prompts["summary"]),
            },
        )
        for section in state.get("sections", [])
    ]


def summarize_section(state: SectionState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    section_title = state.get("section_title", "")
    section_text = state.get("section_text", "")
    if not section_title or not section_text:
        return {"section_summaries": []}

    llm = _make_llm(configurable.summary_model)
    prompt = section_summarizer_instructions.format(
        language=configurable.summary_language,
        section_title=section_title,
        section_text=section_text,
    )
    prompt = f"{state.get('summary_prompts', summary_prompts['summary'])}\n\n{prompt}"
    structured_llm = llm.with_structured_output(SectionSummary, method="function_calling")
    result = structured_llm.invoke(prompt)
    return {
        "section_summaries": [
            {
                "section_title": result.section_title,
                "key_points": result.key_points,
                "key_entities": result.key_entities,
                "summary_text": result.summary_text,
                "citations": result.citations,
            }
        ]
    }


def reflection(state: OverallState, config: RunnableConfig) -> ReflectionState:
    configurable = Configuration.from_runnable_config(config)
    llm = _make_llm(configurable.summary_model)
    prompt = summary_reflection_instructions.format(
        paper_title=state.get("paper_title", "Untitled Paper"),
        summaries="\n\n---\n\n".join(
            f"## {item['section_title']}\n{item['summary_text']}\n\nCitations: {', '.join(item.get('citations', []))}"
            for item in state.get("section_summaries", [])
        ),
    )
    structured_llm = llm.with_structured_output(ReflectionResult, method="function_calling")
    result = structured_llm.invoke(prompt)
    return {
        "is_complete": result.is_complete,
        "missing_aspects": result.missing_aspects,
        "follow_up_sections": result.follow_up_sections,
    }


def route_after_reflection(state: OverallState):
    return "finalize_summary"


def _format_section_summary_block(item: dict) -> str:
    title = item.get("section_title", "")
    summary = item.get("summary_text", "")
    entities = item.get("key_entities") or []
    citations = item.get("citations") or []
    parts = [f"### {title}", summary]
    if entities:
        parts.append("- key_entities: " + ", ".join(entities))
    if citations:
        parts.append("- citations: " + "; ".join(citations))
    return "\n".join(parts)


def finalize_summary(state: OverallState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    llm = _make_llm(configurable.summary_model)
    summaries_block = "\n\n---\n\n".join(
        _format_section_summary_block(item)
        for item in state.get("section_summaries", [])
    )
    prompt = final_summary_instructions.format(
        language=configurable.summary_language,
        paper_title=state.get("paper_title", "Untitled Paper"),
        summaries=summaries_block,
    )
    result = llm.invoke(prompt)
    summary_text = result.content if hasattr(result, "content") else str(result)
    save_summary(state["paper_id"], summary_text, configurable.summary_dir)
    return {"final_summary": summary_text, "messages": [AIMessage(content=summary_text)]}


summary_builder = StateGraph(OverallState, config_schema=Configuration)
summary_builder.add_node("parse_and_chunk", load_and_chunk)
summary_builder.add_node("summarize_section", summarize_section)
summary_builder.add_node("reflection", reflection)
summary_builder.add_node("finalize_summary", finalize_summary)
summary_builder.add_edge(START, "parse_and_chunk")
summary_builder.add_conditional_edges("parse_and_chunk", continue_to_sections, ["summarize_section"])
summary_builder.add_edge("summarize_section", "reflection")
summary_builder.add_conditional_edges("reflection", route_after_reflection, ["finalize_summary"])
summary_builder.add_edge("finalize_summary", END)
summary_graph = summary_builder.compile(name="summary-agent")


# =====================================================================
# QA 子图（HITL）
# =====================================================================


def qa_planner_node(state: QAState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    llm = _make_llm(configurable.qa_model)
    paper_markdown = state.get("pdf_markdown", "")
    history_text = format_history_window(state.get("qa_history_window", []), limit=10)
    prompt = qa_planner_instructions.format(
        language=configurable.summary_language,
        paper_title=state.get("paper_title", "Untitled Paper"),
        history=history_text,
        user_question=state.get("user_question", ""),
        paper_markdown=paper_markdown,
    )
    structured_llm = llm.with_structured_output(QAPlan, method="function_calling")
    result = structured_llm.invoke(prompt)
    plan_dict = {
        "plan_text": result.plan_text,
        "research_steps": result.research_steps,
    }
    return {
        "qa_plan": plan_dict,
        "qa_plan_approved": False,
        "qa_revision_count": 0,
        "qa_interrupt_payload": {
            "stage": "plan_review",
            "plan": plan_dict,
            "user_question": state.get("user_question", ""),
        },
    }


def _format_plan_block(plan: dict) -> str:
    if not plan:
        return "（无可用计划）"
    parts = [plan.get("plan_text", "")]
    steps = plan.get("research_steps") or []
    if steps:
        parts.append("**调研步骤：**\n" + "\n".join(f"- {s}" for s in steps))
    return "\n\n".join(p for p in parts if p)


def qa_drafter_node(state: QAState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    llm = _make_llm(configurable.qa_model)
    plan = state.get("qa_plan") or {}
    history_text = format_history_window(state.get("qa_history_window", []), limit=10)
    paper_markdown = state.get("pdf_markdown", "")
    revision_count = state.get("qa_revision_count", 0) or 0
    revision_block = ""
    critic = state.get("qa_critic_result") or {}
    if revision_count > 0 and critic.get("rewrite_instructions"):
        revision_block = (
            "## 上一版被驳回，请按以下意见修改：\n"
            f"{critic.get('rewrite_instructions')}\n\n"
            f"上一版草稿：\n{state.get('qa_draft', '')}"
        )

    prompt = qa_drafter_instructions.format(
        language=configurable.summary_language,
        paper_title=state.get("paper_title", "Untitled Paper"),
        approved_plan=_format_plan_block(plan),
        history=history_text,
        user_question=state.get("user_question", ""),
        paper_markdown=paper_markdown,
        revision_block=revision_block,
    )
    structured_llm = llm.with_structured_output(QADraft, method="function_calling")
    result = structured_llm.invoke(prompt)
    return {
        "qa_draft": result.answer,
        "qa_draft_citations": result.citations,
        "qa_draft_confidence": result.confidence,
        "qa_revision_count": revision_count + 1,
    }


def qa_critic_node(state: QAState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    llm = _make_llm(configurable.qa_model)
    plan = state.get("qa_plan") or {}
    prompt = qa_critic_instructions.format(
        approved_plan=_format_plan_block(plan),
        user_question=state.get("user_question", ""),
        draft=state.get("qa_draft", ""),
    )
    structured_llm = llm.with_structured_output(QACriticResult, method="function_calling")
    result = structured_llm.invoke(prompt)
    critic_dict = {
        "is_acceptable": result.is_acceptable,
        "critique": result.critique,
        "issues": result.issues,
        "rewrite_instructions": result.rewrite_instructions,
    }
    return {"qa_critic_result": critic_dict}


def route_after_qa_critic(state: QAState):
    critic = state.get("qa_critic_result") or {}
    revisions = state.get("qa_revision_count", 0) or 0
    if critic.get("is_acceptable") or revisions >= (MAX_QA_REVISIONS + 1):
        return "qa_finalize"
    return "qa_drafter"


def qa_finalize_node(state: QAState, config: RunnableConfig):
    answer = state.get("qa_draft", "")
    citations = state.get("qa_draft_citations", []) or []
    confidence = state.get("qa_draft_confidence", "medium") or "medium"
    return {
        "qa_final_answer": answer,
        "citations": citations,
        "confidence": confidence,
    }


qa_builder = StateGraph(QAState, config_schema=Configuration)
qa_builder.add_node("qa_planner", qa_planner_node)
qa_builder.add_node("qa_drafter", qa_drafter_node)
qa_builder.add_node("qa_critic", qa_critic_node)
qa_builder.add_node("qa_finalize", qa_finalize_node)
qa_builder.add_edge(START, "qa_planner")
qa_builder.add_edge("qa_planner", "qa_drafter")
qa_builder.add_edge("qa_drafter", "qa_critic")
qa_builder.add_conditional_edges("qa_critic", route_after_qa_critic, ["qa_drafter", "qa_finalize"])
qa_builder.add_edge("qa_finalize", END)

qa_checkpointer = MemorySaver()
qa_graph = qa_builder.compile(
    name="qa-agent",
    checkpointer=qa_checkpointer,
    interrupt_before=["qa_drafter"],
)


# =====================================================================
# Note 子图（后台静默）
# =====================================================================


def note_planner_node(state: NoteState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    llm = _make_llm(configurable.qa_model)
    keyword = state.get("note_keyword", "") or ""
    history = filter_history_by_keyword(state.get("qa_history_window", []), keyword)
    history_text = format_history_window(history, limit=10)
    paper_markdown = state.get("pdf_markdown", "")
    prompt = note_planner_instructions.format(
        paper_title=state.get("paper_title", "Untitled Paper"),
        keyword=keyword or "（无关键词，按对话整体抽取）",
        history=history_text,
        paper_markdown=paper_markdown,
    )
    structured_llm = llm.with_structured_output(NotePlan, method="function_calling")
    result = structured_llm.invoke(prompt)
    plan_dict = {
        "plan_text": result.plan_text,
        "must_record_qa": result.must_record_qa,
        "one_line_summary": result.one_line_summary,
    }
    return {"note_plan": plan_dict, "note_revision_count": 0}


def _format_note_plan_block(plan: dict) -> str:
    if not plan:
        return "（无可用规划）"
    parts = [plan.get("plan_text", "")]
    qa_items = plan.get("must_record_qa") or []
    if qa_items:
        parts.append("**必录问答要点：**\n" + "\n".join(f"- {s}" for s in qa_items))
    one_line = plan.get("one_line_summary") or ""
    if one_line:
        parts.append(f"**一句话总结：** {one_line}")
    return "\n\n".join(p for p in parts if p)


def note_drafter_node(state: NoteState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    llm = _make_llm(configurable.qa_model)
    plan = state.get("note_plan") or {}
    history = filter_history_by_keyword(
        state.get("qa_history_window", []),
        state.get("note_keyword", "") or "",
    )
    history_text = format_history_window(history, limit=10)
    paper_markdown = state.get("pdf_markdown", "")
    revision_count = state.get("note_revision_count", 0) or 0
    critic = state.get("note_critic_result") or {}
    revision_block = ""
    if revision_count > 0 and critic.get("rewrite_instructions"):
        revision_block = (
            "## 上一版被驳回，请按以下意见修改：\n"
            f"{critic.get('rewrite_instructions')}\n\n"
            f"上一版笔记：\n{state.get('note_draft', '')}"
        )

    prompt = note_drafter_instructions.format(
        plan_block=_format_note_plan_block(plan),
        paper_title=state.get("paper_title", "Untitled Paper"),
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        history=history_text,
        paper_markdown=paper_markdown,
        revision_block=revision_block,
    )
    result = llm.invoke(prompt)
    draft_text = result.content if hasattr(result, "content") else str(result)
    return {
        "note_draft": draft_text,
        "note_revision_count": revision_count + 1,
    }


def note_critic_node(state: NoteState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    llm = _make_llm(configurable.qa_model)
    plan = state.get("note_plan") or {}
    prompt = note_critic_instructions.format(
        plan_block=_format_note_plan_block(plan),
        draft=state.get("note_draft", ""),
    )
    structured_llm = llm.with_structured_output(NoteCriticResult, method="function_calling")
    result = structured_llm.invoke(prompt)
    critic_dict = {
        "is_acceptable": result.is_acceptable,
        "coverage_issues": result.coverage_issues,
        "style_issues": result.style_issues,
        "rewrite_instructions": result.rewrite_instructions,
    }
    return {"note_critic_result": critic_dict}


def route_after_note_critic(state: NoteState):
    critic = state.get("note_critic_result") or {}
    revisions = state.get("note_revision_count", 0) or 0
    if critic.get("is_acceptable") or revisions >= (MAX_NOTE_REVISIONS + 1):
        return "note_persist"
    return "note_drafter"


def _ensure_frontmatter(note_markdown: str, state: NoteState) -> str:
    """若模型遗漏 frontmatter，则补一个最小可用的（仅含 timestamp / paper_title / one_line_summary）。"""
    if note_markdown.lstrip().startswith("---"):
        return note_markdown
    plan = state.get("note_plan") or {}
    one_line = (plan.get("one_line_summary") or "笔记自动生成").strip().split("\n", 1)[0][:80]
    frontmatter = build_note_frontmatter(
        paper_title=state.get("paper_title", "Untitled Paper"),
        one_line_summary=one_line,
    )
    return f"{frontmatter}\n{note_markdown}"


def note_persist_node(state: NoteState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    final_note = _ensure_frontmatter(state.get("note_draft", ""), state)
    note_path = append_structured_note(
        note_markdown=final_note,
        note_dir=configurable.note_dir,
    )
    return {"final_note": final_note, "note_path": note_path}


note_builder = StateGraph(NoteState, config_schema=Configuration)
note_builder.add_node("note_planner", note_planner_node)
note_builder.add_node("note_drafter", note_drafter_node)
note_builder.add_node("note_critic", note_critic_node)
note_builder.add_node("note_persist", note_persist_node)
note_builder.add_edge(START, "note_planner")
note_builder.add_edge("note_planner", "note_drafter")
note_builder.add_edge("note_drafter", "note_critic")
note_builder.add_conditional_edges("note_critic", route_after_note_critic, ["note_drafter", "note_persist"])
note_builder.add_edge("note_persist", END)
note_graph = note_builder.compile(name="note-agent")


# =====================================================================
# 主图：保留默认入口（langgraph dev 可视化），仅包装 summary 流
# =====================================================================


graph = summary_graph
