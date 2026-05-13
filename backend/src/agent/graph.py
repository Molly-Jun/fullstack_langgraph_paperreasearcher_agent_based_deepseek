from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from agent.configuration import Configuration
from agent.prompts import (
    final_summary_instructions,
    qa_instructions,
    section_summarizer_instructions,
    summary_prompts,
    summary_reflection_instructions,
)
from agent.state import OverallState, ParseState, ReflectionState, SectionState
from agent.tools_and_schemas import QAResponse, ReflectionResult, SectionSummary
from agent.utils import append_note, get_relevant_chunks, parse_pdf, save_summary, split_into_sections

load_dotenv()

if os.getenv("DEEPSEEK_API_KEY") is None:
    raise ValueError("DEEPSEEK_API_KEY is not set")


def _make_llm(model_name: str):
    return ChatOpenAI(
        model=model_name,
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1",
        temperature=0,
        max_retries=2,
    )


def load_and_chunk(state: ParseState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    chunks = parse_pdf(state["pdf_path"])
    sections = split_into_sections(chunks)
    paper_title = Path(state["pdf_path"]).stem
    return {
        "paper_id": state["paper_id"],
        "paper_title": paper_title,
        "pdf_path": state["pdf_path"],
        "pdf_chunks": chunks,
        "section_summaries": [],
        "final_summary": "",
        "summary_prompts": state.get("summary_prompts", "请生成结构清晰、带页码引用的标准摘要。"),
        "summary_dir": configurable.summary_dir,
        "note_dir": configurable.note_dir,
        "sections": sections,
        "user_question": state.get("user_question", ""),
    }


def continue_to_sections(state: OverallState):
    # 为每一个章节生成一个 Send 对象，把局部状态（包含 section_text 等）发送给 summarize_section 节点
    # 触发并行处理，写明节点以及对应传递的信息
    return [
        Send(
            "summarize_section",
            {
                "section_title": section["title"],
                "section_text": section["text"],
                "page_range": section["page_range"],
                "paper_id": state["paper_id"],
                "summary_prompts": state.get("summary_prompts", "请生成结构清晰、带页码引用的标准摘要。"),
            },
        )
        for section in state.get("sections", [])
    ]


def summarize_section(state: SectionState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    section_title = state.get("section_title", "")
    section_text = state.get("section_text", "")
    page_range = state.get("page_range", "")
    if not section_title or not section_text:
        return {"section_summaries": []}

    llm = _make_llm(configurable.summary_model)
    prompt = section_summarizer_instructions.format(
        language=configurable.summary_language,
        section_title=section_title,
        page_range=page_range,
        section_text=section_text,
    )
    prompt = f"{state.get('summary_prompts', summary_prompts['summary'])}\n\n{prompt}"
    structured_llm = llm.with_structured_output(SectionSummary, method="function_calling")
    result = structured_llm.invoke(prompt)
    # 让llm生成结构化输出以便agent使用
    return {
        # 结果会被 LangGraph 自动累加到 state["section_summaries"] 列表中
        "section_summaries": [
            {
                "section_title": result.section_title,
                "key_points": result.key_points,
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
    if state.get("is_complete", False):
        return "finalize_summary"

    sections_by_title = {section["title"]: section for section in state.get("sections", [])}
    follow_up_titles = state.get("follow_up_sections", [])
    resend = []

    for title in follow_up_titles:
        section = sections_by_title.get(title)
        if section:
            resend.append(
                Send(
                    "summarize_section",
                    {
                        "section_title": section["title"],
                        "section_text": section["text"],
                        "page_range": section["page_range"],
                        "paper_id": state["paper_id"],
                        "summary_prompts": state.get("summary_prompts", "请生成结构清晰、带页码引用的标准摘要。"),
                    },
                )
            )

    return resend if resend else "finalize_summary"


def finalize_summary(state: OverallState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    llm = _make_llm(configurable.summary_model)
    prompt = final_summary_instructions.format(
        language=configurable.summary_language,
        paper_title=state.get("paper_title", "Untitled Paper"),
        summaries="\n\n---\n\n".join(
            f"### {item['section_title']}\n{item['summary_text']}\n\n- Citations: {', '.join(item.get('citations', []))}"
            for item in state.get("section_summaries", [])
        ),
    )
    result = llm.invoke(prompt)
    summary_text = result.content if hasattr(result, "content") else str(result)
    save_summary(state["paper_id"], summary_text, configurable.summary_dir)
    return {"final_summary": summary_text, "messages": [AIMessage(content=summary_text)]}


def retrieve_context(state: OverallState):
    relevant = get_relevant_chunks(state.get("pdf_chunks", []), state.get("user_question", ""))
    return {"relevant_chunks": relevant}


def answer_question(state: OverallState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    llm = _make_llm(configurable.qa_model)
    prompt = qa_instructions.format(
        language=configurable.summary_language,
        paper_title=state.get("paper_title", "Untitled Paper"),
        relevant_chunks=state.get("relevant_chunks", ""),
        question=state.get("user_question", ""),
    )
    structured_llm = llm.with_structured_output(QAResponse, method="function_calling")
    result = structured_llm.invoke(prompt)
    return {
        "answer": result.answer,
        "citations": result.citations,
        "confidence": result.confidence,
        "messages": [AIMessage(content=result.answer)],
    }


def save_note_node(state: OverallState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    paper_id = state.get("paper_id") or getattr(configurable, "paper_id", None)
    if paper_id is None:
        paper_id = "unknown"
    append_note(
        paper_id,
        {
            "question": state.get("user_question", ""),
            "answer": state.get("answer", ""),
            "citations": state.get("citations", []),
        },
        configurable.note_dir,
    )
    return {}


def route_by_mode(state: OverallState):
    return "parse_and_chunk" if state.get("mode", "summary") == "summary" else "retrieve_context"


builder = StateGraph(OverallState, config_schema=Configuration)

builder.add_node("parse_and_chunk", load_and_chunk)
builder.add_node("summarize_section", summarize_section)
builder.add_node("reflection", reflection)
builder.add_node("finalize_summary", finalize_summary)
builder.add_node("retrieve_context", retrieve_context)
builder.add_node("answer_question", answer_question)
builder.add_node("save_note", save_note_node)

builder.add_conditional_edges(START, route_by_mode, ["parse_and_chunk", "retrieve_context"])
builder.add_conditional_edges("parse_and_chunk", continue_to_sections, ["summarize_section"])
builder.add_edge("summarize_section", "reflection")
builder.add_conditional_edges(
    "reflection",
    route_after_reflection,
    ["summarize_section", "finalize_summary"],
)
builder.add_edge("finalize_summary", END)

builder.add_edge("retrieve_context", "answer_question")
builder.add_edge("answer_question", "save_note")
builder.add_edge("save_note", END)

graph = builder.compile(name="paper-agent")
