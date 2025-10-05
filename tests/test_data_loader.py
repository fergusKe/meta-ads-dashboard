import numpy as np
import pandas as pd
import pytest

from utils.data_loader import (
    preprocess_data,
    calculate_funnel_metrics,
    process_quality_rankings,
)


def _base_dataframe() -> pd.DataFrame:
    """建構測試用的基本資料框架"""
    return pd.DataFrame(
        {
            "開始": ["2024-01-01"],
            "結束時間": ["2024-01-03"],
            "分析報告開始": ["2024-01-01"],
            "分析報告結束": ["2024-01-31"],
            "月": ["2024-01"],
            "花費金額 (TWD)": [1000],
            "觸及人數": [500],
            "曝光次數": [2000],
            "連結點擊次數": [200],
            "連結頁面瀏覽次數": [150],
            "內容瀏覽次數": [120],
            "加到購物車次數": [60],
            "開始結帳次數": [40],
            "購買次數": [20],
            "廣告組合預算": ["1500"],
            "行銷活動預算": [np.nan],
            "日預算": [""],
            "品質排名": ["平均以上"],
            "互動率排名": ["平均"],
            "轉換率排名": [np.nan],
            "投遞狀態": [None],
        }
    )


def test_preprocess_data_handles_dates_and_missing_values():
    df = preprocess_data(_base_dataframe())

    assert pd.api.types.is_datetime64_any_dtype(df["開始"])
    assert pd.api.types.is_datetime64_any_dtype(df["結束時間"])
    assert pd.api.types.is_datetime64_any_dtype(df["分析報告開始"])
    assert df["投放天數"].iloc[0] == 3
    assert pytest.approx(df["日均花費"].iloc[0]) == pytest.approx(333.3333, rel=1e-2)

    numeric_cols = ["廣告組合預算", "行銷活動預算", "日預算"]
    for col in numeric_cols:
        assert col in df.columns
        assert pd.api.types.is_numeric_dtype(df[col])

    assert df["投遞狀態"].iloc[0] == "未知"
    assert df["月份"].iloc[0].month == 1

    assert "點擊率" in df.columns
    assert pytest.approx(df["點擊率"].iloc[0]) == pytest.approx(200 / 2000 * 100, rel=1e-6)


def test_calculate_funnel_metrics_returns_expected_rates():
    df = calculate_funnel_metrics(_base_dataframe().copy())

    assert pytest.approx(df["購買完成率"].iloc[0]) == pytest.approx(20 / 40 * 100, rel=1e-6)
    assert pytest.approx(df["整體轉換率"].iloc[0]) == pytest.approx(20 / 500 * 100, rel=1e-6)


def test_process_quality_rankings_maps_scores():
    df = process_quality_rankings(_base_dataframe().copy())

    assert df["品質排名_分數"].iloc[0] == 3
    assert df["互動率排名_分數"].iloc[0] == 2
    assert df["轉換率排名_分數"].iloc[0] == 0
    assert "綜合品質分數" in df.columns
