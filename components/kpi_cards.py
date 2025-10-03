"""
KPI 卡片元件 - Meta 廣告儀表板
"""

import streamlit as st
import sys
from pathlib import Path

# 添加父目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.chart_config import KPI_CARD_STYLE, KPI_COLORS, format_number

def render_kpi_card(label, value, delta=None, color='primary', format_type='number'):
    """
    渲染 KPI 卡片

    Args:
        label: 標籤
        value: 數值
        delta: 變化值（可選）
        color: 顏色主題（primary, success, warning, danger, purple, info）
        format_type: 格式類型（number, currency, percent, decimal, integer）
    """
    # 格式化數值
    formatted_value = format_number(value, format_type)

    # 格式化變化值
    delta_text = ''
    if delta is not None:
        delta_sign = '+' if delta > 0 else ''
        delta_text = f"{delta_sign}{delta:.1f}%" if isinstance(delta, (int, float)) else str(delta)

    # 取得顏色配置
    colors = KPI_COLORS.get(color, KPI_COLORS['primary'])

    # 渲染 HTML
    html = KPI_CARD_STYLE.format(
        bg_color_start=colors['start'],
        bg_color_end=colors['end'],
        label=label,
        value=formatted_value,
        delta=delta_text
    )

    st.markdown(html, unsafe_allow_html=True)

def render_kpi_row(kpis):
    """
    渲染一行 KPI 卡片

    Args:
        kpis: KPI 配置列表
            每個 KPI 為字典：{
                'label': 標籤,
                'value': 數值,
                'delta': 變化值（可選）,
                'color': 顏色（可選，預設 primary）,
                'format': 格式類型（可選，預設 number）
            }

    Example:
        kpis = [
            {'label': '總花費', 'value': 50000, 'format': 'currency', 'color': 'primary'},
            {'label': '平均 ROAS', 'value': 3.5, 'delta': 15.2, 'format': 'decimal', 'color': 'success'},
            {'label': '總購買', 'value': 150, 'format': 'integer', 'color': 'success'}
        ]
        render_kpi_row(kpis)
    """
    cols = st.columns(len(kpis))

    for col, kpi in zip(cols, kpis):
        with col:
            render_kpi_card(
                label=kpi['label'],
                value=kpi['value'],
                delta=kpi.get('delta'),
                color=kpi.get('color', 'primary'),
                format_type=kpi.get('format', 'number')
            )

def render_metric_card(label, value, delta=None, delta_color='normal'):
    """
    使用 Streamlit 原生 metric 渲染指標卡片

    Args:
        label: 標籤
        value: 數值
        delta: 變化值
        delta_color: 變化值顏色（normal, inverse, off）
    """
    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color
    )

def render_metric_row(metrics):
    """
    渲染一行原生 metric 卡片

    Args:
        metrics: 指標配置列表
            每個指標為字典：{
                'label': 標籤,
                'value': 數值,
                'delta': 變化值（可選）,
                'delta_color': 變化值顏色（可選）
            }

    Example:
        metrics = [
            {'label': '總花費', 'value': 'NT$ 50,000'},
            {'label': '平均 ROAS', 'value': 3.5, 'delta': '15.2%', 'delta_color': 'normal'},
            {'label': '總購買', 'value': 150, 'delta': 20}
        ]
        render_metric_row(metrics)
    """
    cols = st.columns(len(metrics))

    for col, metric in zip(cols, metrics):
        with col:
            render_metric_card(
                label=metric['label'],
                value=metric['value'],
                delta=metric.get('delta'),
                delta_color=metric.get('delta_color', 'normal')
            )
