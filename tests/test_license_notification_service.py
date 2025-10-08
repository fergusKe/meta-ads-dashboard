import json
from datetime import datetime

import pandas as pd
import pytest

from utils import brand_license_store, license_notification_service


@pytest.fixture()
def temp_license_env(tmp_path, monkeypatch):
    meta_path = tmp_path / "licenses.parquet"
    log_path = tmp_path / "notifications.parquet"
    monkeypatch.setenv("BRAND_LICENSE_METADATA_PATH", str(meta_path))
    monkeypatch.setenv("LICENSE_NOTIFICATION_LOG_PATH", str(log_path))
    yield tmp_path


def _write_metadata(records: list[dict]):
    df = pd.DataFrame(records)
    brand_license_store.save_metadata(df)


def test_build_notification_plan_detects_expiring_licenses(temp_license_env):
    applied_brands = [
        {
            "brand_code": "BR001",
            "applied_at": "2025-09-20",
            "expires_at": "2025-10-10",
            "contacts": [{"channel": "email", "target": "pm@example.com"}],
        },
        {
            "brand_code": "BR002",
            "applied_at": "2025-08-01",
            "expires_at": "2025-11-20",
            "contacts": ["ops@example.com"],
        },
    ]
    record = {
        "license_id": "lic_001",
        "name": "品牌語氣授權",
        "brand": "DemoBrand",
        "status": "active",
        "applied_brands": json.dumps(applied_brands, ensure_ascii=False),
        "extra": json.dumps({"contacts": [{"channel": "slack", "target": "#marketing-alert"}]}, ensure_ascii=False),
    }
    _write_metadata([record])

    plan = license_notification_service.build_notification_plan(
        within_days=14,
        reference_date=datetime(2025, 10, 1),
        channels=["email", "slack"],
    )

    assert len(plan) == 2  # email + slack contact for BR001
    assert set(plan["channel"]) == {"email", "slack"}
    assert all(plan["license_id"] == "lic_001")
    assert all(plan["brand_code"] == "BR001")


def test_record_notifications_appends_log(temp_license_env):
    plan = pd.DataFrame(
        [
            {
                "license_id": "lic_001",
                "brand_code": "BR001",
                "license_name": "授權方案",
                "brand": "Demo",
                "channel": "email",
                "recipient": "pm@example.com",
                "send_on": "2025-10-07",
                "days_until_expiry": 3,
                "message": "提醒",
            }
        ]
    )

    log_df = license_notification_service.record_notifications(plan, status="scheduled")
    assert len(log_df) == 1
    loaded = license_notification_service.load_notification_log()
    assert len(loaded) == 1
    assert loaded.iloc[0]["status"] == "scheduled"
