"""
廣告顯示工具
提供統一的廣告列表顯示格式，包含完整階層、關鍵指標、排序等功能
"""

import pandas as pd
import streamlit as st


def format_ad_display_name(row, max_length=60):
    """
    格式化廣告顯示名稱，包含完整階層

    Args:
        row: DataFrame 的一行資料
        max_length: 每個階層名稱的最大長度

    Returns:
        格式化的廣告名稱（行銷活動 > 廣告組合 > 廣告）
    """
    hierarchy_parts = []

    # 行銷活動名稱
    campaign_name = row.get('行銷活動名稱', '')
    if campaign_name:
        hierarchy_parts.append(str(campaign_name)[:max_length])

    # 廣告組合名稱
    ad_set_name = row.get('廣告組合名稱', '')
    if ad_set_name and ad_set_name != campaign_name:
        hierarchy_parts.append(str(ad_set_name)[:max_length])

    # 廣告名稱
    ad_name = row.get('廣告名稱', '')
    if ad_name and ad_name != campaign_name and ad_name != ad_set_name:
        hierarchy_parts.append(str(ad_name)[:max_length])

    if hierarchy_parts:
        return " > ".join(hierarchy_parts)
    else:
        return "未知廣告"


def format_ad_option_label(row, include_metrics=True, include_problem=False):
    """
    格式化廣告選項標籤（用於下拉選單或列表）

    Args:
        row: DataFrame 的一行資料
        include_metrics: 是否包含指標（花費、ROAS）
        include_problem: 是否包含問題類型

    Returns:
        格式化的標籤字串
    """
    parts = []

    if include_metrics:
        # 花費
        spend = row.get('花費金額 (TWD)', 0)
        parts.append(f"💰${spend:,.0f}")

        # ROAS
        roas = row.get('購買 ROAS（廣告投資報酬率）', 0)
        if pd.notna(roas):
            parts.append(f"ROAS {roas:.2f}")
        else:
            parts.append("ROAS N/A")

    if include_problem and '問題類型' in row:
        parts.append(row['問題類型'])

    # 廣告階層名稱
    display_name = format_ad_display_name(row)
    parts.append(display_name)

    return " | ".join(parts)


def create_ad_dataframe_with_hierarchy(df):
    """
    為 DataFrame 新增廣告階層顯示欄位

    Args:
        df: 原始 DataFrame

    Returns:
        新增「廣告階層」欄位的 DataFrame
    """
    df_with_hierarchy = df.copy()
    df_with_hierarchy['廣告階層'] = df_with_hierarchy.apply(format_ad_display_name, axis=1)
    return df_with_hierarchy


def get_sorted_ad_options(df, sort_by='spend', top_n=None, filters=None):
    """
    取得排序後的廣告選項列表

    Args:
        df: DataFrame
        sort_by: 排序依據 ('spend', 'roas', 'cpa', 'ctr')
        top_n: 只取前 N 個（None = 全部）
        filters: 篩選條件字典 {'column': value}

    Returns:
        (option_labels, data_map) - 選項列表和資料映射
    """
    # 應用篩選
    filtered_df = df.copy()
    if filters:
        for col, value in filters.items():
            if col in filtered_df.columns:
                filtered_df = filtered_df[filtered_df[col] == value]

    # 排序
    if sort_by == 'spend':
        sorted_df = filtered_df.sort_values('花費金額 (TWD)', ascending=False)
    elif sort_by == 'roas':
        sorted_df = filtered_df.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False)
    elif sort_by == 'cpa':
        sorted_df = filtered_df.sort_values('每次購買的成本', ascending=True)
    elif sort_by == 'ctr':
        sorted_df = filtered_df.sort_values('CTR（全部）', ascending=False)
    else:
        sorted_df = filtered_df

    # 限制數量
    if top_n:
        sorted_df = sorted_df.head(top_n)

    # 建立選項列表和映射
    option_labels = []
    data_map = {}

    for idx, row in sorted_df.iterrows():
        label = format_ad_option_label(row, include_metrics=True, include_problem=('問題類型' in row))
        option_labels.append(label)
        data_map[label] = row.to_dict()

    return option_labels, data_map


def display_ad_performance_table(df, columns=None, title="廣告效能列表", sort_by='spend'):
    """
    顯示廣告效能表格（含廣告階層）

    Args:
        df: DataFrame
        columns: 要顯示的欄位列表（None = 自動選擇核心欄位）
        title: 表格標題
        sort_by: 排序依據
    """
    if df.empty:
        st.info("目前沒有資料")
        return

    # 新增廣告階層欄位
    df_display = create_ad_dataframe_with_hierarchy(df)

    # 排序
    if sort_by == 'spend':
        df_display = df_display.sort_values('花費金額 (TWD)', ascending=False)
    elif sort_by == 'roas':
        df_display = df_display.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False)

    # 選擇要顯示的欄位
    if columns is None:
        columns = [
            '廣告階層',
            '購買 ROAS（廣告投資報酬率）',
            '花費金額 (TWD)',
            '每次購買的成本',
            'CTR（全部）',
            '購買次數',
            '觸及人數'
        ]

    # 篩選存在的欄位
    available_columns = [col for col in columns if col in df_display.columns]

    st.markdown(f"### {title}")
    st.dataframe(
        df_display[available_columns],
        use_container_width=True,
        column_config={
            "廣告階層": st.column_config.TextColumn("廣告", width="large"),
            "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
            "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="$%.0f"),
            "每次購買的成本": st.column_config.NumberColumn("CPA", format="$%.0f"),
            "CTR（全部）": st.column_config.NumberColumn("CTR", format="%.2f%%"),
            "購買次數": st.column_config.NumberColumn("購買數", format="%.0f"),
            "觸及人數": st.column_config.NumberColumn("觸及", format="%d"),
        }
    )


def create_ad_comparison_view(df, metric='購買 ROAS（廣告投資報酬率）', top_n=10):
    """
    建立廣告對比檢視（Top N vs Bottom N）

    Args:
        df: DataFrame
        metric: 對比的指標
        top_n: 取前/後 N 個

    Returns:
        (top_performers, bottom_performers) - 高效和低效廣告的 DataFrame
    """
    if df.empty or metric not in df.columns:
        return pd.DataFrame(), pd.DataFrame()

    # 新增廣告階層
    df_with_hierarchy = create_ad_dataframe_with_hierarchy(df)

    # 過濾有效數據
    valid_df = df_with_hierarchy[df_with_hierarchy[metric].notna()].copy()

    # Top performers
    top_performers = valid_df.nlargest(top_n, metric)

    # Bottom performers
    bottom_performers = valid_df.nsmallest(top_n, metric)

    return top_performers, bottom_performers


def get_ad_details_for_analysis(row):
    """
    取得廣告的詳細資訊（用於 AI 分析）

    Args:
        row: DataFrame 的一行資料

    Returns:
        包含廣告詳細資訊的字典
    """
    details = {
        "廣告階層": format_ad_display_name(row),
        "行銷活動": row.get('行銷活動名稱', '未知'),
        "廣告組合": row.get('廣告組合名稱', '未知'),
        "廣告名稱": row.get('廣告名稱', '未知'),
        "表現數據": {
            "ROAS": f"{row.get('購買 ROAS（廣告投資報酬率）', 0):.2f}",
            "CPA": f"${row.get('每次購買的成本', 0):.0f}",
            "花費": f"${row.get('花費金額 (TWD)', 0):,.0f}",
            "CTR": f"{row.get('CTR（全部）', 0):.2f}%",
            "購買次數": f"{row.get('購買次數', 0):.0f}",
            "觸及人數": f"{row.get('觸及人數', 0):,.0f}",
            "點擊次數": f"{row.get('連結點擊次數', 0):,.0f}",
        },
        "受眾資訊": {
            "目標受眾": row.get('目標', '未知'),
            "年齡": row.get('年齡', '未知'),
            "性別": row.get('性別', '未知'),
        },
        "廣告素材": {
            "標題": str(row.get('標題', ''))[:100] if pd.notna(row.get('標題')) else '未知',
            "內文": str(row.get('內文', ''))[:200] if pd.notna(row.get('內文')) else '未知',
        },
        "品質評分": {
            "品質排名": row.get('品質排名', '未知'),
            "互動率排名": row.get('互動率排名', '未知'),
            "轉換率排名": row.get('轉換率排名', '未知'),
        }
    }

    return details


def display_top_bottom_ads(df, metric='購買 ROAS（廣告投資報酬率）', top_n=5):
    """
    並排顯示 Top N 和 Bottom N 廣告

    Args:
        df: DataFrame
        metric: 對比的指標
        top_n: 取前/後 N 個
    """
    top_performers, bottom_performers = create_ad_comparison_view(df, metric, top_n)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"#### 🏆 Top {top_n} 表現最好")
        if not top_performers.empty:
            display_columns = ['廣告階層', metric, '花費金額 (TWD)', '購買次數']
            available_columns = [col for col in display_columns if col in top_performers.columns]
            st.dataframe(
                top_performers[available_columns],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("無資料")

    with col2:
        st.markdown(f"#### ⚠️ Bottom {top_n} 需要優化")
        if not bottom_performers.empty:
            display_columns = ['廣告階層', metric, '花費金額 (TWD)', '購買次數']
            available_columns = [col for col in display_columns if col in bottom_performers.columns]
            st.dataframe(
                bottom_performers[available_columns],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("無資料")
