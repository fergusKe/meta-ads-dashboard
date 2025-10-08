import json

import pytest

from utils import fatigue_pilot_manager


@pytest.fixture()
def temp_fatigue_env(tmp_path, monkeypatch):
    log_path = tmp_path / "fatigue_pilot.parquet"
    monkeypatch.setenv("FATIGUE_PILOT_LOG_PATH", str(log_path))
    yield tmp_path


def test_log_and_summarize_fatigue_pilots(temp_fatigue_env):
    fatigue_pilot_manager.log_pilot_result(
        creative_id="creative_1",
        campaign_id="campaign_A",
        action_taken="refresh_creative",
        outcome="success",
        metrics={"lift": 18.2},
        recorded_by="analyst",
    )
    fatigue_pilot_manager.log_pilot_result(
        creative_id="creative_1",
        campaign_id="campaign_A",
        action_taken="pause",
        outcome="monitor",
        metrics={"lift": 5.0},
        recorded_by="analyst",
    )

    results = fatigue_pilot_manager.load_pilot_results("campaign_A")
    assert len(results) == 2

    summary = fatigue_pilot_manager.summarize_results()
    assert len(summary) == 1
    row = summary.iloc[0]
    assert row["last_outcome"] == "monitor"
    metrics = row["last_metrics"]
    if isinstance(metrics, str):
        metrics = json.loads(metrics)
    assert metrics["lift"] == pytest.approx(5.0)
