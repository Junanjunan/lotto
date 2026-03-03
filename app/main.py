from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import Settings
from app.db import Database
from app.schemas import GenerateRequest, GameCreateResponse, SyncResponse
from app.services.crawler import LotteryCrawler
from app.services.strategies import STRATEGIES
from app.services.sync_service import SyncService
from app.services.evaluator import evaluate_games as _evaluate


def create_app() -> FastAPI:
    root_path = os.getenv("FASTAPI_ROOT_PATH", "")
    app = FastAPI(title="Lotto Strategy Service", root_path=root_path)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    settings = Settings(database_path=os.getenv("LOTTO_DB_PATH", "data/lotto.db"))
    db = Database(settings)
    db.init_schema()

    crawler = LotteryCrawler(settings)
    sync_service = SyncService(settings, db, crawler)

    app_dir = Path(__file__).resolve().parent
    ui_index_path = app_dir / "static" / "index.html"

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/meta")
    def root() -> dict:
        return {
            "name": "lotto-service",
            "version": "0.1.0",
            "ui_port": 8645,
            "endpoints": [
                "/health",
                "/api/sync",
                "/api/draws",
                "/api/games",
                "/api/games/{id}",
                "/api/sync/runs",
            ],
            "strategies": list(STRATEGIES.keys()),
        }

    @app.get("/")
    def serve_ui():
        return FileResponse(ui_index_path)

    @app.get("/lotto", include_in_schema=False)
    def serve_ui_alias():
        return FileResponse(ui_index_path)

    @app.get("/lotto/{path:path}", include_in_schema=False)
    def serve_ui_lotto_path(path: str):
        excluded_prefixes = (
            "api",
            "api/",
            "docs",
            "openapi.json",
            "health",
            "meta",
            "favicon.ico",
            "assets/",
            "static/",
        )
        if path.startswith(excluded_prefixes):
            raise HTTPException(status_code=404, detail="not found")
        return FileResponse(ui_index_path)

    @app.post("/api/sync", response_model=SyncResponse)
    def run_sync() -> SyncResponse:
        output = sync_service.run_weekly_sync()
        if output.status != "success":
            raise HTTPException(status_code=502, detail="sync failed")

        return SyncResponse(
            status=output.status,
            latest_draw_no=output.latest_draw_no,
            inserted=output.inserted,
            updated=output.updated,
            skipped=output.skipped,
            run_id=output.run_id,
            source=output.source,
        )

    @app.get("/api/draws")
    def list_draws(
        start_no: Optional[int] = Query(default=None, ge=1),
        end_no: Optional[int] = Query(default=None, ge=1),
    ) -> dict:
        if start_no is not None and end_no is not None and start_no > end_no:
            raise HTTPException(status_code=400, detail="start_no must be less than or equal to end_no")
        draws = db.fetch_draws(start_no, end_no)
        return {
            "count": len(draws),
            "draws": [
                {
                    "draw_no": d.draw_no,
                    "draw_date": d.draw_date,
                    "numbers": d.numbers,
                    "bonus": d.bonus,
                }
                for d in draws
            ],
        }

    @app.post("/api/games", response_model=GameCreateResponse)
    def generate_games(request: GenerateRequest):
        available_draws = db.fetch_draws()
        if not available_draws:
            raise HTTPException(status_code=400, detail="No draw history in DB. Run /api/sync first.")

        strategy = STRATEGIES.get(request.strategy)
        if strategy is None:
            raise HTTPException(status_code=400, detail="Unknown strategy")

        games = strategy(request.game_count, request.seed)
        evaluated = _evaluate(games, available_draws)

        run_id = db.save_game_run(
            strategy=request.strategy,
            game_count=request.game_count,
            seed=request.seed,
            options_json="{}",
            evaluated_until=available_draws[-1].draw_no,
            game_sets=evaluated,
        )

        created_at = None
        with db.connect() as conn:
            row = conn.execute(
                "SELECT created_at FROM games WHERE id = ?",
                (run_id,),
            ).fetchone()
            created_at = row[0] if row else None

        return GameCreateResponse(
            run_id=run_id,
            created_at=str(created_at) if created_at else "",
            strategy=request.strategy,
            game_count=request.game_count,
            seed=request.seed,
            evaluated_until=available_draws[-1].draw_no,
            games=[
                {
                    "game_index": g["game_index"],
                    "numbers": g["numbers"],
                    "rank_distribution": g["rank_distribution"],
                    "total_hits": g["total_hits"],
                }
                for g in evaluated
            ],
        )

    @app.get("/api/games")
    def list_game_runs():
        runs = db.list_game_runs()
        return {
            "count": len(runs),
            "items": [
                {
                    "id": row[0],
                    "created_at": row[1],
                    "strategy_name": row[2],
                    "game_count": row[3],
                    "seed": row[4],
                    "options_json": row[5],
                    "evaluated_until": row[6],
                }
                for row in runs
            ],
        }

    @app.get("/api/games/{game_id}")
    def game_detail(game_id: int, include_hits: bool = Query(default=False)):
        payload = db.get_game_run_detail(game_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="game run not found")

        run = payload["run"]
        result = {
            "run": {
                "id": run["id"],
                "created_at": run["created_at"],
                "strategy_name": run["strategy_name"],
                "game_count": run["game_count"],
                "seed": run["seed"],
                "options_json": run["options_json"],
                "evaluated_until": run["evaluated_until"],
            },
            "game_sets": payload["sets"],
        }

        if include_hits:
            for item in result["game_sets"]:
                item["hits"] = db.get_game_set_hits(item["game_set_id"])

        return result

    @app.get("/api/sync/runs")
    def list_sync_runs(limit: int = 20):
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT id, started_at, finished_at, latest_draw_no, inserted_count, updated_count, skipped_count, status, source, error_message FROM sync_runs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return {
                "count": len(rows),
                "items": [dict(row) for row in rows],
            }

    return app


app = create_app()
