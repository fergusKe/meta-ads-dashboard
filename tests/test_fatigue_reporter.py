import pandas as pd

from utils import fatigue_reporter


def test_generate_report_returns_summary():
    data = pd.DataFrame(
        {
            "creative_id": ["C1", "C2", "C3"],
            "campaign_id": ["CampA", "CampA", "CampB"],
            "status": ["active", "active", "paused"],
            "asset_type": ["image", "video", "image"],
            "age_days": [20, 5, 10],
            "spend": [8000, 2000, 1500],
            "roas": [1.2, 3.5, 2.0],
            "ctr": [0.9, 1.8, 1.3],
            "impressions": [10000, 8000, 5000],
            "conversions": [30, 40, 15],
            "fatigue_score": [0.82, 0.35, 0.5],
            "risk_tier": ["高風險", "低風險", "中風險"],
            "reasons": [["ROAS 偏低"], ["觀察中"], ["CTR 下降"]],
        }
    )

    report = fatigue_reporter.generate_report(data, top_n=2)

    assert report["total_creatives"] == 3
    assert report["high_risk"] == 1
    assert len(report["top_creatives"]) == 2
    assert report["recommendations"]


def test_export_report_creates_file(tmp_path):
    report = {"generated_at": "2025-10-01T00:00:00", "total_creatives": 0}
    path = fatigue_reporter.export_report(report, tmp_path / "report.json")
    assert path.exists()
