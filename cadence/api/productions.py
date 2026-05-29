"""API de producciones guardadas en output/."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from cadence.analysis.rsong_to_midi import convert_rsong_file, load_rsong

OUTPUT_DIR = Path("output")
router = APIRouter(prefix="/productions", tags=["productions"])


def _safe_rsong_path(filename: str) -> Path:
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido.")
    name = filename if filename.endswith(".rsong") else f"{filename}.rsong"
    path = OUTPUT_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Producción no encontrada.")
    return path


@router.get("")
def list_productions():
    """Lista .rsong en output/ ordenados por fecha (más reciente primero)."""
    if not OUTPUT_DIR.exists():
        return {"productions": []}

    items = []
    for path in sorted(OUTPUT_DIR.glob("*.rsong"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            rsong = load_rsong(path)
        except Exception:
            continue
        header = rsong.get("header", {})
        validation = rsong.get("validation", {})
        items.append({
            "id": path.name,
            "filename": path.name,
            "title": header.get("title", path.stem),
            "bpm": header.get("bpm"),
            "key": header.get("key"),
            "duration_ms": header.get("duration_ms"),
            "total_bars": header.get("total_bars"),
            "validation_score": validation.get("score"),
            "track_count": len(rsong.get("tracks", [])),
            "has_midi": path.with_suffix(".mid").exists(),
            "created_at": datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc,
            ).isoformat(),
        })
    return {"productions": items}


@router.get("/{filename}")
def get_production(filename: str):
    """Devuelve el JSON .rsong completo."""
    return load_rsong(_safe_rsong_path(filename))


@router.get("/{filename}/midi")
def get_production_midi(filename: str):
    """Devuelve el .mid (genera desde .rsong si no existe)."""
    rsong_path = _safe_rsong_path(filename)
    mid_path = rsong_path.with_suffix(".mid")
    if not mid_path.exists() or rsong_path.stat().st_mtime > mid_path.stat().st_mtime:
        convert_rsong_file(rsong_path, mid_path)
    return FileResponse(
        mid_path,
        media_type="audio/midi",
        filename=mid_path.name,
    )
