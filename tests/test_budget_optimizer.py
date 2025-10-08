import pandas as pd

from utils import budget_optimizer


def test_generate_reallocation_plan_basic():
    data = pd.DataFrame(
        {
            "行銷活動名稱": ["A", "B", "C"],
            "花費金額 (TWD)": [10000, 4000, 6000],
            "購買 ROAS（廣告投資報酬率）": [1.2, 3.5, 4.0],
            "購買次數": [50, 120, 80],
        }
    )
    config = budget_optimizer.BudgetConfig(target_roas=2.0, min_donor_spend=5000, shift_ratio=0.25)
    plan = budget_optimizer.generate_reallocation_plan(data, config=config)
    assert not plan.empty
    donors = plan[plan["role"] == "donor"]
    recipients = plan[plan["role"] == "recipient"]
    assert len(donors) == 1
    assert len(recipients) >= 1
    summary = budget_optimizer.summarize_shift(plan)
    assert summary["freed"] > 0
    assert abs(summary["freed"] - summary["reallocated"]) < 1
