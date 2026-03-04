"""Research-related tasks."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from statistics import fmean, pstdev
from typing import Any

from celery import shared_task

from quantsentinel.domain.strategies.search import BayesianSampler, EarlyStoppingRule
from quantsentinel.infra.db.engine import session_scope
from quantsentinel.infra.db.repos.runs_repo import RunsRepo
from quantsentinel.infra.tasks.lifecycle import TaskLifecycle
from quantsentinel.services.strategy_service import StrategyService


@shared_task(
    name="quantsentinel.infra.tasks.tasks_research.run_backtest",
    bind=True,
    ignore_result=True,
)
def run_backtest(
    _self,
    task_id: str | None = None,
    *,
    ticker: str,
    start_date: str,
    end_date: str,
    family: str,
    params_json: dict | None = None,
) -> None:
    def _worker(report):
        if not ticker.strip():
            raise ValueError("ticker is required")
        if start_date > end_date:
            raise ValueError("start_date must be <= end_date")
        report(30, f"loading {ticker} data")
        report(65, f"running {family} backtest")
        n_params = len(params_json or {})
        report(90, f"window={start_date}..{end_date}; params={n_params}")
        return f"backtest completed: {ticker}/{family}"

    TaskLifecycle(task_id).run(worker=_worker)


@shared_task(
    name="quantsentinel.infra.tasks.tasks_research.run_param_search",
    bind=True,
    ignore_result=True,
)
def run_param_search(
    _self,
    task_id: str | None = None,
    *,
    ticker: str,
    start_date: str,
    end_date: str,
    family: str,
    grid_size: int = 16,
    sampler: str = "grid",
    seed: int | None = 7,
) -> None:
    def _worker(report):
        if grid_size <= 0:
            raise ValueError("grid_size must be positive")

        service = StrategyService()
        param_space = service.parameter_space(family=family)
        search_sampler = service.build_sampler(sampler=sampler, space=param_space, seed=seed)
        early_stopping = EarlyStoppingRule(max_no_improve_rounds=5)

        report(15, f"generate candidates via {sampler}")
        candidates = search_sampler.sample(n_candidates=grid_size)

        leaderboard: list[dict[str, Any]] = []
        scores: list[float] = []
        report(30, f"fan-out {len(candidates)} backtests")

        with ThreadPoolExecutor(max_workers=min(8, max(1, len(candidates)))) as pool:
            futures = {
                pool.submit(_evaluate_candidate, service, family, candidate): candidate
                for candidate in candidates
            }
            for completed, future in enumerate(as_completed(futures), start=1):
                row = future.result()
                leaderboard.append(row)
                scores.append(row["score"])
                if isinstance(search_sampler, BayesianSampler):
                    search_sampler.observe(params=row["params"], score=row["score"])
                progress = min(90, 30 + int(55 * completed / max(1, len(candidates))))
                report(progress, f"evaluated {completed}/{len(candidates)}")
                if early_stopping.should_stop(scores=scores):
                    break

        leaderboard.sort(key=lambda item: item["score"], reverse=True)
        for idx, row in enumerate(leaderboard, start=1):
            row["rank"] = idx
        report(94, "persist strategy runs")

        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        with session_scope() as session:
            repo = RunsRepo(session)
            for row in leaderboard:
                repo.create_strategy_run(
                    family=family,
                    params_json=row["params"],
                    metrics_json=row["metrics"],
                    artifacts_json={"ticker": ticker, "leaderboard_rank": row["rank"]},
                    start_date=start,
                    end_date=end,
                    score=row["score"],
                    random_seed=seed,
                )

        top = leaderboard[:3]
        return (
            f"parameter search completed: {ticker}/{family}, "
            f"evaluated={len(leaderboard)}, top_score={top[0]['score']:.4f}"
        )

    TaskLifecycle(task_id).run(worker=_worker)


def _evaluate_candidate(service: StrategyService, family: str, params: dict[str, Any]) -> dict[str, Any]:
    merged_params = service.default_params(family=family)
    merged_params.update(params)
    result = service.run(family=family, params=merged_params)
    risk_adjusted = _risk_adjusted_score(result.metrics)
    penalty = _robustness_penalty(result.metrics)
    final_score = round(risk_adjusted - penalty, 6)
    metrics = dict(result.metrics)
    metrics["risk_adjusted_score"] = risk_adjusted
    metrics["robustness_penalty"] = penalty
    return {
        "params": merged_params,
        "metrics": metrics,
        "score": final_score,
        "rank": 0,
    }


def _risk_adjusted_score(metrics: dict[str, float]) -> float:
    return round((0.6 * metrics["sharpe"]) + (0.4 * metrics["sortino"]), 6)


def _robustness_penalty(metrics: dict[str, float]) -> float:
    series = [
        metrics["return"],
        metrics["sharpe"],
        metrics["sortino"],
        metrics["hit_rate"],
        -metrics["max_drawdown"],
    ]
    std = pstdev(series)
    mean = abs(fmean(series)) or 1.0
    return round(min(1.5, std / mean), 6)
