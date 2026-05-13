from __future__ import annotations

import asyncio
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from agent.graph import graph
from agent.utils import (
    append_note,
    ensure_paper_workspace_dirs,
    ensure_workspace_dirs,
    get_workspace_document,
    parse_pdf,
    scan_workspace,
    workspace_summary_dir,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await asyncio.to_thread(ensure_workspace_dirs)
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/api/workspace/{paper_id}/summary")
async def get_workspace_summary(paper_id: str):
    resource = await _resolve_resource(paper_id)
    summary_path = Path(resource.get("summary_path") or (workspace_summary_dir() / f"{paper_id}.md"))
    if not summary_path.is_file():
        raise HTTPException(status_code=404, detail="Summary not found")
    return Response(summary_path.read_text(encoding="utf-8"), media_type="text/markdown")


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


@app.post("/api/summary")
async def create_summary(payload: dict):
    mode = payload.get("mode", "summary")
    normalized_payload: dict = {
        "paper_id": payload.get("paper_id"),
        "paper_title": payload.get("paper_title"),
        "pdf_path": payload.get("pdf_path"),
        "mode": mode,
        "user_question": payload.get("user_question", ""),
        "summary_prompts": payload.get("summary_prompts", ""),
    }

    if mode == "qa" and normalized_payload.get("pdf_path"):
        normalized_payload["pdf_chunks"] = await asyncio.to_thread(
            parse_pdf, normalized_payload["pdf_path"]
        )

    result = await graph.ainvoke(normalized_payload)
    if mode == "qa":
        return {
            "paper_id": result.get("paper_id", normalized_payload.get("paper_id")),
            "paper_title": result.get(
                "paper_title", normalized_payload.get("paper_title", "Untitled Paper")
            ),
            "answer": result.get("answer", ""),
            "citations": result.get("citations", []),
            "confidence": result.get("confidence", "medium"),
        }
    summary_text = result.get("final_summary", result.get("summary", ""))
    return {
        "paper_id": result.get("paper_id", normalized_payload.get("paper_id")),
        "paper_title": result.get(
            "paper_title", normalized_payload.get("paper_title", "Untitled Paper")
        ),
        "summary": summary_text,
    }


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
        str(workspace_summary_dir()),
    )
    return {"paper_id": paper_id, "saved": True}


app.mount("/app", create_frontend_router(), name="frontend")
