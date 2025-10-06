"""A/B 測試框架。"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

EXPERIMENT_DIR = Path("data/experiments")
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
EXPERIMENT_FILE = EXPERIMENT_DIR / "ab_tests.json"


@dataclass
class Experiment:
    name: str
    variants: Dict[str, Any]
    created_at: str = datetime.utcnow().isoformat()
    notes: str | None = None
    results: Dict[str, Any] = None  # type: ignore[assignment]


def _load_experiments() -> List[Dict[str, Any]]:
    if not EXPERIMENT_FILE.exists():
        return []
    try:
        return json.loads(EXPERIMENT_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save_experiments(data: List[Dict[str, Any]]) -> None:
    EXPERIMENT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def register_experiment(name: str, variants: Dict[str, Any], notes: str | None = None) -> None:
    experiments = _load_experiments()
    experiments.append(asdict(Experiment(name=name, variants=variants, notes=notes, results={})))
    _save_experiments(experiments)


def record_result(name: str, variant: str, metric: str, value: float) -> None:
    experiments = _load_experiments()
    for experiment in experiments:
        if experiment['name'] == name:
            experiment.setdefault('results', {}).setdefault(variant, {})[metric] = value
            break
    _save_experiments(experiments)


def list_experiments() -> List[Dict[str, Any]]:
    return _load_experiments()


__all__ = ["register_experiment", "record_result", "list_experiments"]
