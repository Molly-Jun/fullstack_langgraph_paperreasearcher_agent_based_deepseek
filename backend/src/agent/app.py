from __future__ import annotations

import asyncio
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from agent.graph import note_graph, qa_graph, summary_graph
from agent.utils import (
    append_note,
    ensure_paper_workspace_dirs,
    ensure_workspace_dirs,
    get_workspace_document,
    load_paper_full_markdown,
    parse_pdf,
    scan_workspace,
    workspace_note_dir,
    workspace_summary_dir,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await asyncio.to_thread(ensure_workspace_dirs)
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 简单的内存 Job 表，跟踪后台笔记任务状态
NOTE_JOBS: dict[str, dict] = {}


def create_frontend_router(build_dir: str = "../frontend/dist"):
    build_path = Path(__file__).parent.parent.parent / build_dir
    if not build_path.is_dir() or not (build_path / "index.html").is_file():
        from starlette.routing import Route

        async def dummy_frontend(_request):
            return Response(
                "Frontend not built. Run 'npm run build' in the frontend directory.",
                media_type="text/plain",
                status_code=503,
            )

        return Route("/{path:path}", endpoint=dummy_frontend)

    return StaticFiles(directory=build_path, html=True)


async def _resolve_resource(paper_id: str) -> dict:
    resource = await asyncio.to_thread(get_workspace_document, paper_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return resource


# ---------------------------------------------------------------------
# 工作区资源 / PDF / Summary
# ---------------------------------------------------------------------


@app.get("/api/workspace/{paper_id}/summary")
async def get_workspace_summary(paper_id: str):
    resource = await _resolve_resource(paper_id)
    summary_path = Path(resource.get("summary_path") or (workspace_summary_dir() / f"{paper_id}.md"))
    if not summary_path.is_file():
        raise HTTPException(status_code=404, detail="Summary not found")
    return Response(summary_path.read_text(encoding="utf-8"), media_type="text/markdown")


@app.get("/api/workspace/{paper_id}/notes")
async def get_workspace_notes(paper_id: str):
    notes_path = workspace_note_dir() / f"{paper_id}_notes.md"
    if not notes_path.is_file():
        raise HTTPException(status_code=404, detail="Notes not found")
    return Response(notes_path.read_text(encoding="utf-8"), media_type="text/markdown")


@app.get("/api/workspace/{paper_id}/pdf")
async def get_workspace_pdf(paper_id: str):
    resource = await _resolve_resource(paper_id)
    pdf_path = Path(resource["pdf_path"])
    if not pdf_path.is_file():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name,
        headers={"Content-Disposition": f'inline; filename="{pdf_path.name}"'},
    )


@app.get("/api/pdf/{paper_id}")
async def stream_workspace_pdf(paper_id: str):
    resource = await _resolve_resource(paper_id)
    pdf_path = Path(resource["pdf_path"])
    if not pdf_path.is_file():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name,
        headers={"Content-Disposition": f'inline; filename="{pdf_path.name}"'},
    )


@app.get("/api/workspace")
async def list_workspace():
    try:
        resources = await asyncio.to_thread(scan_workspace)
        return {"workspace_id": "default", "resources": resources}
    except Exception as exc:
        return {"workspace_id": "default", "resources": [], "error": str(exc)}


@app.get("/api/workspace/{paper_id}")
async def open_workspace_document(paper_id: str):
    resource = await _resolve_resource(paper_id)
    chunks = await asyncio.to_thread(parse_pdf, resource["pdf_path"])
    return {
        "paper_id": resource["paper_id"],
        "paper_title": resource["title"],
        "pdf_path": resource["pdf_path"],
        "pdf_url": f"/api/workspace/{resource['paper_id']}/pdf",
        "has_summary": resource["has_summary"],
        "has_notes": resource["has_notes"],
        "pages": chunks,
    }


@app.get("/api/workspace/{paper_id}/pages")
async def get_workspace_pages(paper_id: str):
    resource = await _resolve_resource(paper_id)
    chunks = await asyncio.to_thread(parse_pdf, resource["pdf_path"])
    return {"paper_id": paper_id, "pages": chunks}


def _derive_paper_id(filename: str) -> str:
    stem = Path(filename).stem.lower()
    safe = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return safe or "paper"


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    paper_id = _derive_paper_id(file.filename or "paper.pdf")
    upload_dir, _paper_dir = await asyncio.to_thread(ensure_paper_workspace_dirs, paper_id)
    file_path = upload_dir / f"{paper_id}.pdf"
    content = await file.read()
    await asyncio.to_thread(file_path.write_bytes, content)
    return {"paper_id": paper_id, "filename": file.filename, "pdf_path": str(file_path)}


# ---------------------------------------------------------------------
# Summary 链路
# ---------------------------------------------------------------------


@app.post("/api/summary")
async def create_summary(payload: dict):
    """保留旧入口：仅服务 summary 模式。QA / Note 已迁移到独立端点。"""

    payload_dict = {
        "paper_id": payload.get("paper_id"),
        "paper_title": payload.get("paper_title"),
        "pdf_path": payload.get("pdf_path"),
        "mode": "summary",
        "summary_prompts": payload.get("summary_prompts", ""),
    }
    result = await summary_graph.ainvoke(payload_dict)
    summary_text = result.get("final_summary", result.get("summary", ""))
    return {
        "paper_id": result.get("paper_id", payload_dict.get("paper_id")),
        "paper_title": result.get(
            "paper_title", payload_dict.get("paper_title", "Untitled Paper")
        ),
        "summary": summary_text,
    }


# ---------------------------------------------------------------------
# QA 链路（HITL）
# ---------------------------------------------------------------------


def _normalize_history(messages: list | None) -> list[dict]:
    if not messages:
        return []
    normalized: list[dict] = []
    for item in messages:
        if isinstance(item, dict):
            normalized.append(
                {
                    "type": item.get("type") or item.get("role") or "user",
                    "content": item.get("content", ""),
                }
            )
    return normalized


@app.post("/api/qa/plan")
async def qa_start_plan(payload: dict):
    """启动 QA 流，跑到 qa_drafter 之前的 interrupt 处停下，返回审批用的 plan。"""

    paper_id = payload.get("paper_id")
    if not paper_id:
        raise HTTPException(status_code=400, detail="paper_id is required")
    user_question = payload.get("user_question", "").strip()
    if not user_question:
        raise HTTPException(status_code=400, detail="user_question is required")

    resource = await _resolve_resource(paper_id)
    try:
        markdown_text = await asyncio.to_thread(load_paper_full_markdown, paper_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    thread_id = f"qa-{uuid.uuid4().hex}"
    config = {"configurable": {"thread_id": thread_id}}
    state_payload = {
        "paper_id": paper_id,
        "paper_title": payload.get("paper_title") or resource.get("title", paper_id),
        "pdf_markdown": markdown_text,
        "user_question": user_question,
        "qa_history_window": _normalize_history(payload.get("qa_history_window")),
    }

    await qa_graph.ainvoke(state_payload, config=config)
    snapshot = await asyncio.to_thread(qa_graph.get_state, config)
    plan = (snapshot.values or {}).get("qa_plan", {})
    next_nodes = list(snapshot.next or ())
    return {
        "thread_id": thread_id,
        "paper_id": paper_id,
        "plan": plan,
        "next_nodes": next_nodes,
        "interrupted": "qa_drafter" in next_nodes,
    }


@app.post("/api/qa/resume")
async def qa_resume(payload: dict):
    """带审批后的计划恢复 QA 图执行，跑完 drafter+critic 直到收敛。"""

    thread_id = payload.get("thread_id")
    if not thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required")
    approved_plan = payload.get("plan") or {}
    if isinstance(approved_plan, str):
        approved_plan = {
            "plan_text": approved_plan,
            "research_steps": [],
            "expected_evidence": [],
            "success_criteria": [],
        }

    config = {"configurable": {"thread_id": thread_id}}
    snapshot = await asyncio.to_thread(qa_graph.get_state, config)
    if snapshot is None or not snapshot.values:
        raise HTTPException(status_code=404, detail="QA thread not found or expired")

    await asyncio.to_thread(
        qa_graph.update_state,
        config,
        {"qa_plan": approved_plan, "qa_plan_approved": True},
    )
    result = await qa_graph.ainvoke(None, config=config)
    return {
        "thread_id": thread_id,
        "paper_id": result.get("paper_id"),
        "answer": result.get("qa_final_answer", result.get("qa_draft", "")),
        "citations": result.get("citations", []),
        "confidence": result.get("confidence", "medium"),
        "critic_result": result.get("qa_critic_result"),
    }


# ---------------------------------------------------------------------
# Note 链路（后台静默）
# ---------------------------------------------------------------------


def _run_note_job(job_id: str, payload: dict) -> None:
    """同步执行 note_graph，更新内存中的 Job 状态。"""

    NOTE_JOBS[job_id] = {"status": "running"}
    try:
        result = note_graph.invoke(payload)
        NOTE_JOBS[job_id] = {
            "status": "done",
            "note_path": result.get("note_path"),
            "final_note": result.get("final_note"),
            "critic_result": result.get("note_critic_result"),
        }
    except Exception as exc:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        NOTE_JOBS[job_id] = {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
        }


@app.post("/api/note/extract")
async def note_extract(payload: dict, background_tasks: BackgroundTasks):
    """触发笔记 Agent，立即返回 job_id，不阻塞前端。"""

    paper_id = payload.get("paper_id")
    if not paper_id:
        raise HTTPException(status_code=400, detail="paper_id is required")

    resource = await _resolve_resource(paper_id)
    try:
        markdown_text = await asyncio.to_thread(load_paper_full_markdown, paper_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    job_id = f"note-{uuid.uuid4().hex}"
    note_payload = {
        "paper_id": paper_id,
        "paper_title": payload.get("paper_title") or resource.get("title", paper_id),
        "pdf_markdown": markdown_text,
        "qa_history_window": _normalize_history(payload.get("qa_history_window")),
        "note_keyword": payload.get("note_keyword", "") or "",
    }
    NOTE_JOBS[job_id] = {"status": "queued"}
    background_tasks.add_task(_run_note_job, job_id, note_payload)
    return {"job_id": job_id, "paper_id": paper_id, "status": "queued"}


@app.get("/api/note/status/{job_id}")
async def note_status(job_id: str):
    job = NOTE_JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Note job not found")
    return {"job_id": job_id, **job}


# ---------------------------------------------------------------------
# 旧版 Q&A 笔记追加接口（保留兼容）
# ---------------------------------------------------------------------


@app.post("/api/workspace/{paper_id}/notes")
async def append_workspace_note(paper_id: str, payload: dict):
    await _resolve_resource(paper_id)
    await asyncio.to_thread(
        append_note,
        paper_id,
        {
            "question": payload.get("question", ""),
            "answer": payload.get("answer", ""),
            "citations": payload.get("citations", []),
        },
        str(workspace_note_dir()),
    )
    return {"paper_id": paper_id, "saved": True}


app.mount("/app", create_frontend_router(), name="frontend")
