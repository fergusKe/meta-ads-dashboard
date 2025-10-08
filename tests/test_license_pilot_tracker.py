import json

import pytest

from utils import license_pilot_tracker


@pytest.fixture()
def temp_pilot_env(tmp_path, monkeypatch):
    log_path = tmp_path / "pilot_logs.parquet"
    monkeypatch.setenv("LICENSE_PILOT_LOG_PATH", str(log_path))
    yield tmp_path


def test_log_and_summarize_pilot_events(temp_pilot_env):
    license_pilot_tracker.log_pilot_event(
        license_id="lic_001",
        brand_code="BR001",
        status="success",
        metrics={"lift": 12.5},
        notes="首週轉換達標",
        recorded_by="pm",
    )
    license_pilot_tracker.log_pilot_event(
        license_id="lic_001",
        brand_code="BR001",
        status="fail",
        metrics={"lift": -3.2},
        notes="第二週下滑",
        recorded_by="pm",
    )

    logs = license_pilot_tracker.load_pilot_logs(license_id="lic_001")
    assert len(logs) == 2

    summary = license_pilot_tracker.summarize_pilots(license_id="lic_001")
    assert len(summary) == 1
    row = summary.iloc[0]
    assert row["success"] == 1
    assert row["fail"] == 1
    latest_metrics = row["latest_metrics"]
    if isinstance(latest_metrics, str):
        latest_metrics = json.loads(latest_metrics)
    assert latest_metrics["lift"] == pytest.approx(-3.2)
