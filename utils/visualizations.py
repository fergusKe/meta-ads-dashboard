import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import streamlit as st
import numpy as np

def create_roas_distribution_chart(df):
    """創建 ROAS 分佈直方圖"""
    if df is None or df.empty:
        return None

    roas_data = df['購買 ROAS（廣告投資報酬率）'].dropna()
    if roas_data.empty:
        return None

    fig = px.histogram(
        x=roas_data,
        nbins=20,
        title="ROAS 分佈分析",
        labels={'x': 'ROAS', 'y': '活動數量'},
        color_discrete_sequence=['#1f77b4']
    )

    # 添加平均線
    mean_roas = roas_data.mean()
    fig.add_vline(
        x=mean_roas,
        line_dash="dash",
        line_color="red",
        annotation_text=f"平均 ROAS: {mean_roas:.2f}"
    )

    # 添加目標線
    fig.add_vline(
        x=3.0,
        line_dash="dash",
        line_color="green",
        annotation_text="目標 ROAS: 3.0"
    )

    fig.update_layout(
        showlegend=False,
        height=400,
        xaxis_title="ROAS",
        yaxis_title="活動數量"
    )

    return fig

def create_cpa_vs_purchases_scatter(df):
    """創建 CPA vs 購買次數散點圖"""
    if df is None or df.empty:
        return None

    # 過濾有效數據
    scatter_data = df[
        (df['每次購買的成本'] > 0) &
        (df['購買次數'] > 0) &
        (df['每次購買的成本'] < df['每次購買的成本'].quantile(0.95))  # 移除極端值
    ].copy()

    if scatter_data.empty:
        return None

    fig = px.scatter(
        scatter_data,
        x='每次購買的成本',
        y='購買次數',
        size='花費金額 (TWD)',
        color='購買 ROAS（廣告投資報酬率）',
        hover_data=['行銷活動名稱'],
        title="CPA vs 購買次數關係分析",
        labels={
            '每次購買的成本': 'CPA (每次購買成本)',
            '購買次數': '購買次數',
            '花費金額 (TWD)': '花費金額',
            '購買 ROAS（廣告投資報酬率）': 'ROAS'
        },
        color_continuous_scale='RdYlGn'
    )

    fig.update_layout(height=500)

    return fig

def create_ctr_vs_cpm_chart(df):
    """創建 CTR vs CPM 關係圖"""
    if df is None or df.empty:
        return None

    # 過濾有效數據
    chart_data = df[
        (df['CTR（全部）'] > 0) &
        (df['CPM（每千次廣告曝光成本）'] > 0)
    ].copy()

    if chart_data.empty:
        return None

    fig = px.scatter(
        chart_data,
        x='CPM（每千次廣告曝光成本）',
        y='CTR（全部）',
        size='曝光次數',
        color='購買 ROAS（廣告投資報酬率）',
        hover_data=['行銷活動名稱'],
        title="CTR vs CPM 效率分析",
        labels={
            'CPM（每千次廣告曝光成本）': 'CPM (千次曝光成本)',
            'CTR（全部）': 'CTR (%)',
            '曝光次數': '曝光次數',
            '購買 ROAS（廣告投資報酬率）': 'ROAS'
        },
        color_continuous_scale='RdYlGn'
    )

    fig.update_layout(height=500)

    return fig

def create_spend_vs_efficiency_bubble(df):
    """創建花費 vs 轉換效率氣泡圖"""
    if df is None or df.empty:
        return None

    # 計算轉換效率 (購買次數 / 花費)
    bubble_data = df[df['花費金額 (TWD)'] > 0].copy()
    bubble_data['轉換效率'] = bubble_data['購買次數'] / bubble_data['花費金額 (TWD)'] * 1000  # 每千元花費的轉換次數

    if bubble_data.empty:
        return None

    fig = px.scatter(
        bubble_data,
        x='花費金額 (TWD)',
        y='轉換效率',
        size='觸及人數',
        color='購買 ROAS（廣告投資報酬率）',
        hover_data=['行銷活動名稱'],
        title="花費 vs 轉換效率分析",
        labels={
            '花費金額 (TWD)': '花費金額 (TWD)',
            '轉換效率': '轉換效率 (每千元轉換次數)',
            '觸及人數': '觸及人數',
            '購買 ROAS（廣告投資報酬率）': 'ROAS'
        },
        color_continuous_scale='RdYlGn'
    )

    fig.update_layout(height=500)

    return fig

def create_funnel_chart(df):
    """創建轉換漏斗圖"""
    if df is None or df.empty:
        return None

    # 計算漏斗各階段數據
    total_reach = df['觸及人數'].sum()
    total_impressions = df['曝光次數'].sum()
    total_clicks = df['點擊次數（全部）'].sum()
    total_page_views = df['連結頁面瀏覽次數'].sum()
    total_add_to_cart = df['加到購物車次數'].sum()
    total_checkout = df['開始結帳次數'].sum()
    total_purchases = df['購買次數'].sum()

    # 準備漏斗數據
    funnel_data = [
        ('觸及', total_reach),
        ('曝光', total_impressions),
        ('點擊', total_clicks),
        ('頁面瀏覽', total_page_views),
        ('加入購物車', total_add_to_cart),
        ('開始結帳', total_checkout),
        ('完成購買', total_purchases)
    ]

    # 過濾掉為0的階段
    funnel_data = [(stage, value) for stage, value in funnel_data if value > 0]

    if len(funnel_data) < 2:
        return None

    stages = [item[0] for item in funnel_data]
    values = [item[1] for item in funnel_data]

    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textinfo="value+percent initial+percent previous",
        texttemplate='%{y}<br>%{value:,.0f}<br>(%{percentInitial}) (%{percentPrevious})',
        connector={"line": {"color": "royalblue", "dash": "solid", "width": 3}},
        marker={"color": ["deepskyblue", "lightsalmon", "tan", "teal", "silver", "gold", "lightgreen"][:len(stages)]}
    ))

    fig.update_layout(
        title="轉換漏斗分析",
        height=600,
        font_size=12
    )

    return fig

def create_performance_comparison_table(df):
    """創建效能對比表格"""
    if df is None or df.empty:
        return None

    # 計算關鍵指標
    metrics = {
        '總花費 (TWD)': df['花費金額 (TWD)'].sum(),
        '總購買次數': df['購買次數'].sum(),
        '平均 ROAS': df['購買 ROAS（廣告投資報酬率）'].mean(),
        '平均 CPA (TWD)': df['每次購買的成本'].mean(),
        '平均 CTR (%)': df['CTR（全部）'].mean(),
        '平均 CPM (TWD)': df['CPM（每千次廣告曝光成本）'].mean(),
        '總觸及人數': df['觸及人數'].sum(),
        '轉換率 (%)': (df['購買次數'].sum() / df['觸及人數'].sum() * 100) if df['觸及人數'].sum() > 0 else 0
    }

    # 設定目標值
    targets = {
        '總花費 (TWD)': None,
        '總購買次數': None,
        '平均 ROAS': 3.0,
        '平均 CPA (TWD)': 300,
        '平均 CTR (%)': 2.0,
        '平均 CPM (TWD)': 100,
        '總觸及人數': None,
        '轉換率 (%)': 1.0
    }

    # 創建比較表格
    comparison_data = []
    for metric, actual_value in metrics.items():
        target_value = targets.get(metric)

        if actual_value is None or pd.isna(actual_value):
            achievement_rate = None
            status = "無數據"
        elif target_value is None:
            achievement_rate = None
            status = "無目標"
        else:
            if metric in ['平均 CPA (TWD)', '平均 CPM (TWD)']:  # 越低越好的指標
                achievement_rate = (target_value / actual_value * 100) if actual_value > 0 else 0
            else:  # 越高越好的指標
                achievement_rate = (actual_value / target_value * 100) if target_value > 0 else 0

            if achievement_rate >= 100:
                status = "✅ 達標"
            elif achievement_rate >= 80:
                status = "⚠️ 接近"
            else:
                status = "❌ 未達標"

        comparison_data.append({
            '指標': metric,
            '實際值': f"{actual_value:,.2f}" if actual_value is not None and not pd.isna(actual_value) else "N/A",
            '目標值': f"{target_value:,.2f}" if target_value is not None else "無設定",
            '達成率': f"{achievement_rate:.1f}%" if achievement_rate is not None else "N/A",
            '狀態': status
        })

    return pd.DataFrame(comparison_data)

def create_time_series_chart(df, date_column='開始', metric_column='購買 ROAS（廣告投資報酬率）', title="時間序列分析"):
    """創建時間序列圖表"""
    if df is None or df.empty or date_column not in df.columns:
        return None

    # 只使用有效的日期和指標數據
    valid_data = df.dropna(subset=[date_column, metric_column])

    if valid_data.empty:
        return None

    # 按日期分組，只保留有數據的日期
    time_data = valid_data.groupby(valid_data[date_column].dt.date)[metric_column].mean().reset_index()
    time_data.columns = ['日期', metric_column]

    # 過濾掉異常值（如 ROAS 為 0 或負數）
    if 'ROAS' in metric_column:
        time_data = time_data[time_data[metric_column] > 0]
    elif '花費' in metric_column or '購買' in metric_column:
        time_data = time_data[time_data[metric_column] >= 0]

    if time_data.empty or len(time_data) < 2:
        return None

    fig = px.line(
        time_data,
        x='日期',
        y=metric_column,
        title=title,
        markers=True
    )

    # 設定 X 軸範圍為實際數據範圍
    if not time_data.empty:
        fig.update_layout(
            height=400,
            xaxis_title="日期",
            yaxis_title=metric_column,
            xaxis=dict(
                range=[time_data['日期'].min(), time_data['日期'].max()]
            )
        )

    return fig

def create_campaign_performance_chart(df, top_n=10):
    """創建活動效能條狀圖"""
    if df is None or df.empty:
        return None

    # 按活動分組並計算 ROAS
    campaign_performance = df.groupby('行銷活動名稱').agg({
        '購買 ROAS（廣告投資報酬率）': 'mean',
        '花費金額 (TWD)': 'sum',
        '購買次數': 'sum'
    }).reset_index()

    # 排序並取前 N 名
    top_campaigns = campaign_performance.nlargest(top_n, '購買 ROAS（廣告投資報酬率）')

    if top_campaigns.empty:
        return None

    fig = px.bar(
        top_campaigns,
        x='購買 ROAS（廣告投資報酬率）',
        y='行銷活動名稱',
        orientation='h',
        title=f"Top {top_n} 活動 ROAS 表現",
        labels={'購買 ROAS（廣告投資報酬率）': 'ROAS', '行銷活動名稱': '活動名稱'},
        color='購買 ROAS（廣告投資報酬率）',
        color_continuous_scale='RdYlGn'
    )

    fig.update_layout(
        height=400,
        yaxis={'categoryorder': 'total ascending'}
    )

    return fig