"""Research service."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import Any
from uuid import uuid4


@dataclass
class ResearchRun:
    run_id: str
    project_id: str
    folds: list[dict[str, Any]]
    summary: dict[str, Any]


@dataclass
class ResearchProject:
    project_id: str
    name: str
    metadata: dict[str, Any] = field(default_factory=dict)
    runs: list[ResearchRun] = field(default_factory=list)


class ResearchService:
    """Project and walk-forward run manager."""

    def __init__(self) -> None:
        self._projects: dict[str, ResearchProject] = {}

    def create_project(self, *, name: str, metadata: dict[str, Any] | None = None) -> ResearchProject:
        if not name.strip():
            raise ValueError("project name is required")

        project = ResearchProject(project_id=str(uuid4()), name=name.strip(), metadata=metadata or {})
        self._projects[project.project_id] = project
        return project

    def list_projects(self) -> list[ResearchProject]:
        return list(self._projects.values())

    def get_runs(self, project_id: str) -> list[ResearchRun]:
        return [*self._require_project(project_id).runs]

    def run_walk_forward(
        self,
        *,
        project_id: str,
        returns: list[float],
        folds: int,
        trading_cost_bps: float,
        slippage_bps: float,
        max_position: float = 1.0,
        max_drawdown_limit: float = 0.2,
    ) -> ResearchRun:
        if folds < 2:
            raise ValueError("walk-forward requires at least 2 folds")
        if not returns:
            raise ValueError("returns cannot be empty")
        if max_position <= 0 or max_position > 1:
            raise ValueError("max_position must be in (0, 1]")
        if trading_cost_bps < 0 or slippage_bps < 0:
            raise ValueError("cost/slippage cannot be negative")

        project = self._require_project(project_id)
        fold_size = max(1, len(returns) // folds)

        fold_results: list[dict[str, Any]] = []
        net_cost_ratio = (trading_cost_bps + slippage_bps) / 10_000

        for fold_idx in range(folds):
            start = fold_idx * fold_size
            end = len(returns) if fold_idx == folds - 1 else (fold_idx + 1) * fold_size
            segment = returns[start:end]
            if not segment:
                continue

            adjusted = [
                self._apply_risk(self._apply_costs(value=r, cost_ratio=net_cost_ratio), max_position=max_position)
                for r in segment
            ]
            cumulative = self._cumulative(adjusted)
            max_dd = self._max_drawdown(cumulative)
            pnl = sum(adjusted)
            breach = max_dd > max_drawdown_limit
            penalty = (max_dd - max_drawdown_limit) if breach else 0.0
            pnl_after_risk = pnl - penalty

            fold_results.append(
                {
                    "fold": fold_idx + 1,
                    "start": start,
                    "end": end,
                    "gross_pnl": round(sum(segment), 8),
                    "net_pnl": round(pnl_after_risk, 8),
                    "max_drawdown": round(max_dd, 8),
                    "volatility": round(pstdev(adjusted) if len(adjusted) > 1 else 0.0, 8),
                    "risk_breach": breach,
                }
            )

        if len(fold_results) < 2:
            raise ValueError("insufficient data to produce >=2 folds")

        net_pnls = [item["net_pnl"] for item in fold_results]
        summary = {
            "folds": len(fold_results),
            "avg_net_pnl": round(mean(net_pnls), 8),
            "total_net_pnl": round(sum(net_pnls), 8),
            "worst_drawdown": max(item["max_drawdown"] for item in fold_results),
            "stability": round(1.0 / (1.0 + (pstdev(net_pnls) if len(net_pnls) > 1 else 0.0)), 8),
            "risk_breach_folds": sum(1 for item in fold_results if item["risk_breach"]),
            "trading_cost_bps": trading_cost_bps,
            "slippage_bps": slippage_bps,
            "max_position": max_position,
            "max_drawdown_limit": max_drawdown_limit,
        }

        run = ResearchRun(
            run_id=str(uuid4()),
            project_id=project_id,
            folds=fold_results,
            summary=summary,
        )
        project.runs.append(run)
        return run

    def _apply_costs(self, *, value: float, cost_ratio: float) -> float:
        return value - cost_ratio

    def _apply_risk(self, value: float, *, max_position: float) -> float:
        return max(-max_position, min(max_position, value))

    def _cumulative(self, values: list[float]) -> list[float]:
        out: list[float] = []
        total = 0.0
        for value in values:
            total += value
            out.append(total)
        return out

    def _max_drawdown(self, cumulative: list[float]) -> float:
        peak = float("-inf")
        drawdown = 0.0
        for value in cumulative:
            peak = max(peak, value)
            drawdown = max(drawdown, peak - value)
        return drawdown

    def _require_project(self, project_id: str) -> ResearchProject:
        if project_id not in self._projects:
            raise ValueError(f"project not found: {project_id}")
        return self._projects[project_id]
