from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from agent.graph import graph
from agent.utils import parse_pdf

app = FastAPI()


def create_frontend_router(build_dir="../frontend/dist"):
    build_path = Path(__file__).parent.parent.parent / build_dir
    if not build_path.is_dir() or not (build_path / "index.html").is_file():
        from starlette.routing import Route

        async def dummy_frontend(request):
            return Response(
                "Frontend not built. Run 'npm run build' in the frontend directory.",
                media_type="text/plain",
                status_code=503,
            )

        return Route("/{path:path}", endpoint=dummy_frontend)

    return StaticFiles(directory=build_path, html=True)


async def _write_bytes(file_path: Path, content: bytes):
    await asyncio.to_thread(file_path.write_bytes, content)


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    paper_id = uuid.uuid4().hex[:8]
    upload_dir = Path(__file__).parent.parent.parent / "data" / "uploads" / paper_id
    await asyncio.to_thread(upload_dir.mkdir, parents=True, exist_ok=True)
    file_path = upload_dir / (file.filename or f"{paper_id}.pdf")
    content = await file.read()
    await _write_bytes(file_path, content)
    return {"paper_id": paper_id, "filename": file.filename, "pdf_path": str(file_path)}


@app.post("/api/summary")
async def create_summary(payload: dict):
    mode = payload.get("mode", "summary")
    if mode == "qa" and payload.get("pdf_path"):
        payload = {
            **payload,
            "pdf_chunks": parse_pdf(payload["pdf_path"]),
        }
    result = await graph.ainvoke(payload)
    if mode == "qa":
        return {
            "paper_id": result.get("paper_id", payload.get("paper_id")),
            "paper_title": result.get("paper_title", payload.get("paper_title", "Untitled Paper")),
            "answer": result.get("answer", ""),
            "citations": result.get("citations", []),
            "confidence": result.get("confidence", "medium"),
        }
    return {
        "paper_id": result.get("paper_id", payload.get("paper_id")),
        "paper_title": result.get("paper_title", payload.get("paper_title", "Untitled Paper")),
        "summary": result.get("final_summary", result.get("summary", "")),
    }


app.mount("/app", create_frontend_router(), name="frontend")
