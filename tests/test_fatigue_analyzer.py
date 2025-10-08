import pandas as pd

from utils import fatigue_analyzer


def test_calculate_fatigue_scores_basic():
    data = pd.DataFrame(
        {
            "creative_id": ["A", "B"],
            "campaign_id": ["C1", "C1"],
            "status": ["deployed", "deployed"],
            "asset_type": ["image", "video"],
            "deployed_at": ["2025-09-20", "2025-10-05"],
            "spend": [6000, 1000],
            "roas": [1.2, 3.0],
            "ctr": [0.9, 2.0],
            "impressions": [50000, 10000],
            "conversions": [40, 25],
        }
    )

    scores = fatigue_analyzer.calculate_fatigue_scores(
        data,
        config={
            "age_threshold_days": 14,
            "roas_target": 2.5,
            "ctr_target": 1.5,
            "spend_threshold": 5000,
        },
        reference_datetime=pd.Timestamp("2025-10-10"),
    )

    assert len(scores) == 2
    assert set(scores["risk_tier"]) == {"高風險", "低風險"}
    assert scores.iloc[0]["creative_id"] == "A"
    assert scores.iloc[0]["risk_tier"] == "高風險"
    assert isinstance(scores.iloc[0]["reasons"], list)

    summary = fatigue_analyzer.summarize_by_campaign(scores)
    assert list(summary.columns) == ["campaign_id", "creatives", "high_risk", "medium_risk", "avg_score", "avg_roas"]
    assert summary.iloc[0]["high_risk"] == 1
