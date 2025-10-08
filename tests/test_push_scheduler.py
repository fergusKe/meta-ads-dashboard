import pandas as pd

from utils import push_scheduler


def test_generate_push_plan_and_digest():
    scores = pd.DataFrame(
        {
            "campaign_id": ["C1", "C1", "C2"],
            "creative_id": ["A", "B", "C"],
            "risk_tier": ["高風險", "中風險", "低風險"],
            "fatigue_score": [0.8, 0.6, 0.2],
            "roas": [0.9, 1.5, 3.0],
            "ctr": [0.5, 1.2, 3.0],
            "reasons": [["ROAS 低"], ["CTR 低"], ["觀察"]],
        }
    )

    plan = push_scheduler.generate_push_plan(scores, per_campaign=1)
    assert len(plan) == 1
    assert set(plan["campaign_id"]) == {"C1"}
    assert plan.iloc[0]["channel"] == push_scheduler.DEFAULT_CHANNEL
    assert plan.iloc[0]["cta"]
    assert plan.iloc[0]["message"].startswith("【疲勞預警】活動 ")

    digest = push_scheduler.compile_digest(plan)
    assert len(digest) == 1
    assert digest[0].startswith("活動 C1 → 素材")
