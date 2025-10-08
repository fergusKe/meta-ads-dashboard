from datetime import datetime

import pandas as pd
import pytest

from utils import template_review_scheduler, template_store


@pytest.fixture()
def temp_template_env(tmp_path, monkeypatch):
    meta_path = tmp_path / "templates.parquet"
    review_log = tmp_path / "review_logs.parquet"
    monkeypatch.setenv("TEMPLATE_METADATA_PATH", str(meta_path))
    monkeypatch.setenv("TEMPLATE_STORAGE_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("TEMPLATE_REVIEW_LOG_PATH", str(review_log))
    yield tmp_path


def _seed_templates():
    df = pd.DataFrame(
        [
            {
                "template_id": "tpl_recent",
                "name": "近期模板",
                "category": "新品",
                "status": "approved",
                "created_at": "2025-09-20T00:00:00",
                "updated_at": "2025-09-25T00:00:00",
                "last_reviewed_at": "2025-09-30T00:00:00",
            },
            {
                "template_id": "tpl_old",
                "name": "久未審核模板",
                "category": "節慶",
                "status": "approved",
                "created_at": "2025-07-01T00:00:00",
                "updated_at": "2025-07-10T00:00:00",
                "last_reviewed_at": "2025-07-15T00:00:00",
            },
            {
                "template_id": "tpl_draft",
                "name": "草稿模板",
                "category": "促銷",
                "status": "draft",
                "created_at": "2025-10-01T00:00:00",
                "updated_at": "2025-10-02T00:00:00",
                "last_reviewed_at": None,
            },
        ]
    )
    template_store.save_metadata(df)


def test_generate_schedule_prioritizes_overdue_items(temp_template_env):
    _seed_templates()
    schedule = template_review_scheduler.generate_schedule(
        cycle_days=14,
        reference_date=datetime(2025, 10, 7),
    )

    assert len(schedule) == 3
    first_row = schedule.iloc[0]
    assert first_row["template_id"] == "tpl_draft"
    assert first_row["priority"] == "高"

    second_row = schedule.iloc[1]
    assert second_row["template_id"] == "tpl_old"
    assert second_row["priority"] == "高"


def test_record_review_updates_logs_and_status(temp_template_env):
    _seed_templates()
    template_review_scheduler.record_review(
        template_id="tpl_draft",
        reviewer="QA",
        outcome="pass",
        status="approved",
        notes="流程確認完成",
        metadata={"checks": ["assets_verified"]},
    )

    logs = template_review_scheduler.load_review_logs("tpl_draft")
    assert len(logs) == 1
    assert logs.iloc[0]["reviewer"] == "QA"

    metadata = template_store.load_metadata()
    row = metadata[metadata["template_id"] == "tpl_draft"].iloc[0]
    assert row["status"] == "approved"
