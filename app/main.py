from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import Settings
from app.db import Database
from app.schemas import (
    CompareRequest,
    GenerateRequest,
    GameCreateResponse,
    NumberCheckRequest,
    NumberCheckResponse,
    SyncResponse,
)
from app.services.crawler import LotteryCrawler
from app.services.evaluator import evaluate_games as _evaluate
from app.services.strategy_stats import LotteryStatsService
from app.services.strategies import (
    STRATEGIES,
    STRATEGY_CATALOG,
    STRATEGY_DESCRIPTIONS,
    STRATEGY_LABELS,
    STRATEGY_OPTION_LABELS,
    STRATEGY_OPTION_SCHEMA,
    generate_games_with_options,
)
from app.services.sync_service import SyncService


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
    stats_service = LotteryStatsService()

    app_dir = Path(__file__).resolve().parent
    ui_index_path = app_dir / "static" / "index.html"
    ui_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    def render_ui():
        return FileResponse(
            ui_index_path,
            media_type="text/html",
            headers=ui_headers,
        )

    def format_draw_date(draw_date: str) -> str:
        if not draw_date:
            return ""

        text = "".join(ch for ch in str(draw_date) if ch.isdigit())
        if len(text) == 8:
            try:
                dt = datetime.date.fromisoformat(f"{text[:4]}-{text[4:6]}-{text[6:8]}")
                return dt.isoformat()
            except ValueError:
                return f"{text[:4]}-{text[4:6]}-{text[6:8]}"

        return str(draw_date)

    def env_bool(name: str, default: bool = False) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        normalized = raw.strip().lower()
        if normalized in {"1", "true", "t", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "f", "no", "n", "off", ""}:
            return False
        return default

    def env_int(name: str, default: int) -> int:
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            value = int(raw.strip())
            return value if value > 0 else default
        except ValueError:
            return default

    def env_str(name: str) -> str:
        return os.getenv(name, "").strip()

    def build_ads_meta() -> dict:
        provider = env_str("AD_PROVIDER").lower() or "none"
        if provider not in {"none", "adsense", "adfit"}:
            provider = "none"

        enabled = env_bool("AD_ENABLED", default=(provider != "none"))
        ad_test = env_bool("AD_TEST_MODE", default=False)
        sticky_mobile_only = env_bool("AD_STICKY_MOBILE_ONLY", default=True)

        slots = {
            "top": {"enabled": False},
            "mid": {"enabled": False},
            "sticky": {"enabled": False},
        }
        result = {
            "enabled": False,
            "provider": provider,
            "ad_test": ad_test,
            "client_id": "",
            "layout": {
                "sticky_mobile_only": sticky_mobile_only,
            },
            "slots": slots,
        }

        if not enabled or provider == "none":
            return result

        if provider == "adsense":
            client_id = env_str("ADSENSE_CLIENT_ID")
            if not client_id:
                return result
            result["client_id"] = client_id
            slot_env_map = {
                "top": "ADSENSE_SLOT_TOP",
                "mid": "ADSENSE_SLOT_MID",
                "sticky": "ADSENSE_SLOT_STICKY",
            }
            for slot_name, env_name in slot_env_map.items():
                slot_id = env_str(env_name)
                if slot_id:
                    slots[slot_name] = {
                        "enabled": True,
                        "slot_id": slot_id,
                    }
            result["enabled"] = any(slot["enabled"] for slot in slots.values())
            return result

        slot_env_map = {
            "top": ("ADFIT_UNIT_TOP", "ADFIT_WIDTH_TOP", "ADFIT_HEIGHT_TOP", 728, 90),
            "mid": ("ADFIT_UNIT_MID", "ADFIT_WIDTH_MID", "ADFIT_HEIGHT_MID", 728, 90),
            "sticky": ("ADFIT_UNIT_STICKY", "ADFIT_WIDTH_STICKY", "ADFIT_HEIGHT_STICKY", 320, 100),
        }
        for slot_name, (unit_env, width_env, height_env, default_width, default_height) in slot_env_map.items():
            unit = env_str(unit_env)
            if not unit:
                continue
            slots[slot_name] = {
                "enabled": True,
                "unit": unit,
                "width": env_int(width_env, default_width),
                "height": env_int(height_env, default_height),
            }
        result["enabled"] = any(slot["enabled"] for slot in slots.values())
        return result

    def dump_model(model: object, *, exclude_unset: bool = False) -> dict:
        if hasattr(model, "model_dump"):
            return model.model_dump(exclude_unset=exclude_unset)  # type: ignore[union-attr]
        if hasattr(model, "dict"):
            return model.dict(exclude_unset=exclude_unset)  # type: ignore[union-attr]
        return {}

    def summarize_rank_distribution(games: list[dict]) -> dict[int, int]:
        summary = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for game in games:
            dist = game.get("rank_distribution", {})
            for rank in summary:
                summary[rank] += int(dist.get(rank, 0))
        return {rank: count for rank, count in summary.items() if count > 0}

    def compute_diversity_score(games: list[list[int]]) -> float:
        if len(games) < 2:
            return 1.0
        total_overlap = 0.0
        pair_count = 0
        for i in range(len(games)):
            left = set(games[i])
            for j in range(i + 1, len(games)):
                right = set(games[j])
                total_overlap += len(left & right) / 6.0
                pair_count += 1
        if pair_count == 0:
            return 1.0
        return round(max(0.0, 1.0 - (total_overlap / pair_count)), 4)

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
                "/api/games/compare",
                "/api/games/{id}",
                "/api/number-check",
                "/api/stats/lottery",
                "/api/sync/runs",
            ],
            "strategies": list(STRATEGIES.keys()),
            "strategy_catalog": STRATEGY_CATALOG,
            "strategy_labels": STRATEGY_LABELS,
            "strategy_descriptions": STRATEGY_DESCRIPTIONS,
            "strategy_options": STRATEGY_OPTION_LABELS,
            "strategy_option_schema": STRATEGY_OPTION_SCHEMA,
            "ads": build_ads_meta(),
        }

    @app.get("/")
    def serve_ui():
        return render_ui()

    @app.get("/lotto", include_in_schema=False)
    def serve_ui_alias():
        return render_ui()

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
        return render_ui()

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
                    "draw_date": format_draw_date(d.draw_date),
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

        if request.strategy not in STRATEGIES:
            raise HTTPException(status_code=400, detail="Unknown strategy")

        options = dump_model(request.options, exclude_unset=True)
        try:
            games, normalized_options = generate_games_with_options(
                request.strategy,
                request.game_count,
                request.seed,
                options,
                draws=available_draws,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        evaluated = _evaluate(games, available_draws)

        run_id = db.save_game_run(
            strategy=request.strategy,
            game_count=request.game_count,
            seed=request.seed,
            options_json=json.dumps(normalized_options, separators=(",", ":")),
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
            strategy_options=normalized_options,
            game_count=request.game_count,
            seed=request.seed,
            evaluated_until=available_draws[-1].draw_no,
            games=[
                {
                    "game_index": g["game_index"],
                    "numbers": g["numbers"],
                    "rank_distribution": g["rank_distribution"],
                    "total_hits": g["total_hits"],
                    "hits": g["hits"],
                }
                for g in evaluated
            ],
        )

    @app.post("/api/games/compare")
    def compare_games(request: CompareRequest):
        draws = db.fetch_draws()
        if not draws:
            raise HTTPException(status_code=400, detail="No draw history in DB. Run /api/sync first.")

        results: list[dict] = []
        for item in request.strategies:
            if item.strategy not in STRATEGIES:
                raise HTTPException(status_code=400, detail=f"Unknown strategy: {item.strategy}")

            options = dump_model(item.options, exclude_unset=True)
            try:
                games, normalized_options = generate_games_with_options(
                    strategy_name=item.strategy,
                    game_count=request.game_count,
                    seed=request.seed,
                    options=options,
                    draws=draws,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"{item.strategy}: {exc}")

            evaluated = _evaluate(games, draws)
            rank_distribution = summarize_rank_distribution(evaluated)
            total_hits = sum(rank_distribution.values())

            results.append(
                {
                    "strategy": item.strategy,
                    "strategy_label": STRATEGY_LABELS.get(item.strategy, item.strategy),
                    "strategy_options": normalized_options,
                    "game_count": request.game_count,
                    "total_hits": total_hits,
                    "rank_distribution": rank_distribution,
                    "diversity_score": compute_diversity_score(games),
                    "games": [
                        {
                            "game_index": g["game_index"],
                            "numbers": g["numbers"],
                            "rank_distribution": g["rank_distribution"],
                            "total_hits": g["total_hits"],
                        }
                        for g in evaluated
                    ],
                }
            )

        return {
            "evaluated_until": draws[-1].draw_no,
            "game_count": request.game_count,
            "seed": request.seed,
            "result_count": len(results),
            "results": results,
        }

    @app.post("/api/number-check", response_model=NumberCheckResponse)
    def check_numbers(request: NumberCheckRequest):
        draws = db.fetch_draws()
        if not draws:
            raise HTTPException(status_code=400, detail="No draw history in DB. Run /api/sync first.")

        game = _evaluate([request.numbers], draws)[0]
        draw_map = {d.draw_no: d for d in draws}

        hits: list[dict] = []
        for item in game["hits"]:
            draw = draw_map.get(item["draw_no"])
            if draw is None:
                continue
            hits.append(
                {
                    "draw_no": draw.draw_no,
                    "draw_date": format_draw_date(draw.draw_date),
                    "rank": item["rank"],
                    "match_count": item["match_count"],
                    "bonus_match": bool(item["bonus_match"]),
                    "draw_numbers": draw.numbers,
                    "bonus": draw.bonus,
                    "matched_numbers": item["matched_numbers"],
                }
            )

        hits.sort(key=lambda h: h["draw_no"], reverse=True)

        return NumberCheckResponse(
            numbers=request.numbers,
            total_draws=len(draws),
            evaluated_until=draws[-1].draw_no,
            rank_distribution=game["rank_distribution"],
            total_hits=game["total_hits"],
            hits=hits,
        )

    @app.get("/api/stats/lottery")
    def lottery_stats():
        draws = db.fetch_draws()
        if not draws:
            raise HTTPException(status_code=400, detail="No draw history in DB. Run /api/sync first.")
        return stats_service.build(draws)

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
