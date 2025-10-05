import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import sys
from pathlib import Path
from datetime import datetime, timedelta
import io

# 添加父目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import load_meta_ads_data

def show_detailed_data_table():
    """顯示詳細數據表格頁面 - 升級版"""
    st.markdown("# 📋 詳細數據表格")
    st.markdown("完整數據檢視，支援多維度篩選、欄位自訂與進階匯出")

    # 載入數據
    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 多維度篩選器移到主要區域
    st.markdown("## 🔍 多維度篩選器")

    # 第一行：日期、活動、年齡
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        # 日期範圍篩選
        if '開始' in df.columns and df['開始'].notna().any():
            min_date = df['開始'].min().date()
            max_date = df['開始'].max().date()

            st.markdown("### 📅 日期範圍")
            date_range = st.date_input(
                "選擇日期範圍",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )

            if len(date_range) == 2:
                start_date, end_date = date_range
                df = df[(df['開始'].dt.date >= start_date) & (df['開始'].dt.date <= end_date)]

    with filter_col2:
        # 行銷活動篩選
        st.markdown("### 🎯 行銷活動")
        all_campaigns = sorted(df['行銷活動名稱'].unique().tolist())
        selected_campaigns = st.multiselect(
            "選擇活動（可多選）",
            all_campaigns,
            default=all_campaigns if len(all_campaigns) <= 10 else all_campaigns[:10]
        )

        if selected_campaigns:
            df = df[df['行銷活動名稱'].isin(selected_campaigns)]

    with filter_col3:
        # 年齡篩選
        if '年齡' in df.columns:
            st.markdown("### 👥 年齡")
            all_ages = sorted([age for age in df['年齡'].unique() if age != '未知'])
            selected_ages = st.multiselect(
                "選擇年齡層",
                all_ages,
                default=all_ages
            )

            if selected_ages:
                df = df[df['年齡'].isin(selected_ages)]

    # 第二行：性別、品質、狀態
    filter_col4, filter_col5, filter_col6 = st.columns(3)

    with filter_col4:
        # 性別篩選
        if '性別' in df.columns:
            st.markdown("### 👤 性別")
            all_genders = [g for g in df['性別'].unique() if g != '未知']
            selected_genders = st.multiselect(
                "選擇性別",
                all_genders,
                default=all_genders
            )

            if selected_genders:
                df = df[df['性別'].isin(selected_genders)]

    with filter_col5:
        # 品質排名篩選
        if '品質排名' in df.columns:
            st.markdown("### 🏆 品質排名")
            quality_options = ['全部'] + sorted([q for q in df['品質排名'].unique() if q != '未知'])
            selected_quality = st.selectbox(
                "品質排名",
                quality_options
            )

            if selected_quality != '全部':
                df = df[df['品質排名'] == selected_quality]

    with filter_col6:
        # 投遞狀態篩選
        if '投遞狀態' in df.columns:
            st.markdown("### 📡 投遞狀態")
            all_status = df['投遞狀態'].unique().tolist()
            selected_status = st.multiselect(
                "選擇狀態",
                all_status,
                default=all_status
            )

            if selected_status:
                df = df[df['投遞狀態'].isin(selected_status)]

    # 第三行：ROAS 和花費範圍
    filter_col7, filter_col8 = st.columns(2)

    with filter_col7:
        # ROAS 範圍篩選
        st.markdown("### 💰 ROAS 範圍")
        roas_col1, roas_col2 = st.columns(2)
        with roas_col1:
            roas_min = st.number_input("最小 ROAS", value=0.0, step=0.5)
        with roas_col2:
            roas_max = st.number_input("最大 ROAS", value=100.0, step=0.5)

        df = df[
            (df['購買 ROAS（廣告投資報酬率）'] >= roas_min) &
            (df['購買 ROAS（廣告投資報酬率）'] <= roas_max)
        ]

    with filter_col8:
        # 花費範圍篩選
        st.markdown("### 💵 花費範圍")
        spend_col1, spend_col2 = st.columns(2)
        with spend_col1:
            spend_min = st.number_input("最小花費 (TWD)", value=0, step=100)
        with spend_col2:
            spend_max = st.number_input("最大花費 (TWD)", value=int(df['花費金額 (TWD)'].max()) if not df.empty else 100000, step=100)

        df = df[
            (df['花費金額 (TWD)'] >= spend_min) &
            (df['花費金額 (TWD)'] <= spend_max)
        ]

    # 顯示篩選結果摘要
    st.success(f"✅ 篩選結果：共 {len(df)} 筆記錄")

    st.markdown("---")

    # ========== 欄位自訂顯示 ==========
    st.markdown("## ⚙️ 欄位自訂設定")

    # 定義核心欄位（預設顯示）
    core_columns = [
        '行銷活動名稱', '廣告組合名稱', '廣告名稱',
        '花費金額 (TWD)', '購買次數', '購買 ROAS（廣告投資報酬率）',
        'CTR（全部）', '每次購買的成本', '觸及人數',
        '曝光次數', '投遞狀態', '年齡', '性別',
        '品質排名', '互動率排名', '轉換率排名'
    ]

    # 篩選實際存在的核心欄位
    core_columns = [col for col in core_columns if col in df.columns]

    # 其他可選欄位
    all_columns = df.columns.tolist()
    optional_columns = [col for col in all_columns if col not in core_columns]

    # 欄位選擇
    view_mode = st.radio(
        "選擇檢視模式",
        ['核心欄位（預設20個）', '全部欄位', '自訂欄位'],
        horizontal=True
    )

    if view_mode == '核心欄位（預設20個）':
        display_columns = core_columns
    elif view_mode == '全部欄位':
        display_columns = all_columns
    else:  # 自訂欄位
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**核心欄位**（預設包含）")
            selected_core = st.multiselect(
                "選擇核心欄位",
                core_columns,
                default=core_columns[:10],
                key='core_cols'
            )

        with col2:
            st.markdown("**其他欄位**（可選）")
            selected_optional = st.multiselect(
                "選擇其他欄位",
                optional_columns,
                key='optional_cols'
            )

        display_columns = selected_core + selected_optional

    st.success(f"✅ 已選擇 {len(display_columns)} 個欄位")

    st.markdown("---")

    # ========== 進階排序與搜尋 ==========
    st.markdown("## 🔎 進階排序與搜尋")

    search_col1, search_col2 = st.columns(2)

    with search_col1:
        # 文字搜尋
        search_term = st.text_input(
            "🔍 搜尋關鍵字（活動名稱、廣告組合名稱、廣告名稱）",
            placeholder="輸入關鍵字..."
        )

        if search_term:
            mask = (
                df['行銷活動名稱'].str.contains(search_term, case=False, na=False) |
                df['廣告組合名稱'].str.contains(search_term, case=False, na=False) |
                df['廣告名稱'].str.contains(search_term, case=False, na=False)
            )
            df = df[mask]
            st.info(f"找到 {len(df)} 筆包含「{search_term}」的記錄")

    with search_col2:
        # 排序
        sort_column = st.selectbox(
            "排序欄位",
            display_columns
        )

        sort_order = st.radio(
            "排序方式",
            ['降序（高到低）', '升序（低到高）'],
            horizontal=True
        )

        if sort_column:
            ascending = (sort_order == '升序（低到高）')
            df = df.sort_values(sort_column, ascending=ascending)

    st.markdown("---")

    # ========== 數據表格顯示 ==========
    st.markdown("## 📊 數據表格")

    if df.empty:
        st.warning("⚠️ 當前篩選條件下沒有數據")
        return

    # 顯示摘要統計
    with st.expander("📈 摘要統計", expanded=False):
        summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

        with summary_col1:
            st.metric("總花費", f"{df['花費金額 (TWD)'].sum():,.0f} TWD")
            st.metric("平均 ROAS", f"{df['購買 ROAS（廣告投資報酬率）'].mean():.2f}")

        with summary_col2:
            st.metric("總購買次數", f"{df['購買次數'].sum():,.0f}")
            st.metric("平均 CPA", f"{df['每次購買的成本'].mean():,.0f} TWD")

        with summary_col3:
            st.metric("總觸及", f"{df['觸及人數'].sum():,.0f}")
            st.metric("平均 CTR", f"{df['CTR（全部）'].mean():.2f}%")

        with summary_col4:
            st.metric("總曝光", f"{df['曝光次數'].sum():,.0f}")
            st.metric("總轉換率", f"{(df['購買次數'].sum() / df['觸及人數'].sum() * 100):.2f}%" if df['觸及人數'].sum() > 0 else "0%")

    # 分頁設定
    page_size = st.selectbox(
        "每頁顯示筆數",
        [10, 25, 50, 100, 500, 1000],
        index=2
    )

    total_pages = (len(df) - 1) // page_size + 1
    page_number = st.number_input(
        f"頁碼（共 {total_pages} 頁）",
        min_value=1,
        max_value=total_pages,
        value=1
    )

    # 計算分頁範圍
    start_idx = (page_number - 1) * page_size
    end_idx = min(start_idx + page_size, len(df))

    # 顯示當前頁數據
    display_df = df[display_columns].iloc[start_idx:end_idx].copy()

    # 配置欄位格式
    column_config = {}

    for col in display_columns:
        if 'TWD' in col or '成本' in col or '金額' in col or '花費' in col:
            column_config[col] = st.column_config.NumberColumn(
                col,
                format="%.0f TWD"
            )
        elif 'ROAS' in col or '比率' in col:
            column_config[col] = st.column_config.NumberColumn(
                col,
                format="%.2f"
            )
        elif 'CTR' in col or 'CPM' in col or '轉換率' in col or '率' in col:
            column_config[col] = st.column_config.NumberColumn(
                col,
                format="%.2f%%"
            )
        elif '次數' in col or '人數' in col:
            column_config[col] = st.column_config.NumberColumn(
                col,
                format="%d"
            )

    st.dataframe(
        display_df,
        use_container_width=True,
        column_config=column_config,
        height=600
    )

    st.caption(f"顯示第 {start_idx + 1} - {end_idx} 筆，共 {len(df)} 筆記錄")

    st.markdown("---")

    # ========== 匯出功能增強 ==========
    st.markdown("## 📥 資料匯出")

    export_col1, export_col2, export_col3 = st.columns(3)

    with export_col1:
        # CSV 匯出
        st.markdown("### 📄 匯出 CSV")

        csv_export_options = st.radio(
            "匯出範圍",
            ['當前頁', '當前篩選結果', '全部數據'],
            key='csv_export'
        )

        if csv_export_options == '當前頁':
            export_df = display_df
        elif csv_export_options == '當前篩選結果':
            export_df = df[display_columns]
        else:
            export_df = load_meta_ads_data()[display_columns]

        csv = export_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

        st.download_button(
            label="📥 下載 CSV",
            data=csv,
            file_name=f"meta_ads_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    with export_col2:
        # Excel 匯出
        st.markdown("### 📊 匯出 Excel")

        excel_export_options = st.radio(
            "匯出範圍",
            ['當前篩選結果', '全部數據 + 統計'],
            key='excel_export'
        )

        # 創建 Excel
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if excel_export_options == '當前篩選結果':
                df[display_columns].to_excel(writer, sheet_name='數據', index=False)
            else:
                # 匯出多個工作表
                load_meta_ads_data().to_excel(writer, sheet_name='完整數據', index=False)

                # 摘要統計表
                summary_data = {
                    '指標': [
                        '總花費', '總購買次數', '平均 ROAS', '平均 CPA',
                        '總觸及', '總曝光', '平均 CTR'
                    ],
                    '數值': [
                        df['花費金額 (TWD)'].sum(),
                        df['購買次數'].sum(),
                        df['購買 ROAS（廣告投資報酬率）'].mean(),
                        df['每次購買的成本'].mean(),
                        df['觸及人數'].sum(),
                        df['曝光次數'].sum(),
                        df['CTR（全部）'].mean()
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='摘要統計', index=False)

        excel_data = output.getvalue()

        st.download_button(
            label="📥 下載 Excel",
            data=excel_data,
            file_name=f"meta_ads_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with export_col3:
        # 匯出篩選條件
        st.markdown("### 🔖 匯出篩選設定")

        filter_settings = {
            '篩選條件': [
                '活動數量', '年齡層', '性別', 'ROAS範圍',
                '花費範圍', '品質排名', '投遞狀態'
            ],
            '設定值': [
                f"{len(selected_campaigns)} 個活動",
                f"{len(selected_ages) if '年齡' in df.columns else 0} 個年齡層",
                f"{len(selected_genders) if '性別' in df.columns else 0} 個性別",
                f"{roas_min} - {roas_max}",
                f"{spend_min} - {spend_max} TWD",
                selected_quality,
                f"{len(selected_status) if '投遞狀態' in df.columns else 0} 個狀態"
            ]
        }

        filter_df = pd.DataFrame(filter_settings)
        filter_csv = filter_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

        st.download_button(
            label="📥 下載篩選設定",
            data=filter_csv,
            file_name=f"filter_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    st.markdown("---")

    # ========== 快速洞察 ==========
    st.markdown("## 💡 快速洞察")

    insight_col1, insight_col2 = st.columns(2)

    with insight_col1:
        # Top 表現
        st.markdown("### 🏆 Top 5 表現")

        top_performers = df.nlargest(5, '購買 ROAS（廣告投資報酬率）')[
            ['廣告名稱', '購買 ROAS（廣告投資報酬率）', '花費金額 (TWD)', '購買次數']
        ]

        st.dataframe(
            top_performers,
            use_container_width=True,
            column_config={
                "廣告名稱": "廣告",
                "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%d"),
                "購買次數": st.column_config.NumberColumn("購買", format="%d")
            }
        )

    with insight_col2:
        # Bottom 表現
        st.markdown("### ⚠️ 需改善廣告 Top 5")

        bottom_performers = df[df['購買 ROAS（廣告投資報酬率）'] < 1.5].nlargest(5, '花費金額 (TWD)')[
            ['廣告名稱', '購買 ROAS（廣告投資報酬率）', '花費金額 (TWD)', '購買次數']
        ]

        if not bottom_performers.empty:
            st.dataframe(
                bottom_performers,
                use_container_width=True,
                column_config={
                    "廣告名稱": "廣告",
                    "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                    "花費金額 (TWD)": st.column_config.NumberColumn("花費", format="%d"),
                    "購買次數": st.column_config.NumberColumn("購買", format="%d")
                }
            )
        else:
            st.success("✅ 沒有 ROAS < 1.5 的廣告")

    # 趨勢圖
    if '年月' in df.columns:
        st.markdown("### 📈 月度趨勢")

        monthly_trend = df.groupby('年月').agg({
            '花費金額 (TWD)': 'sum',
            '購買次數': 'sum',
            '購買 ROAS（廣告投資報酬率）': 'mean'
        }).reset_index()

        fig_trend = make_subplots(specs=[[{"secondary_y": True}]])

        fig_trend.add_trace(
            go.Bar(
                name='花費',
                x=monthly_trend['年月'],
                y=monthly_trend['花費金額 (TWD)'],
                marker_color='#3498db'
            ),
            secondary_y=False
        )

        fig_trend.add_trace(
            go.Scatter(
                name='平均 ROAS',
                x=monthly_trend['年月'],
                y=monthly_trend['購買 ROAS（廣告投資報酬率）'],
                mode='lines+markers',
                marker=dict(size=10, color='#e74c3c'),
                line=dict(width=3)
            ),
            secondary_y=True
        )

        fig_trend.update_layout(
            title="月度花費 vs ROAS 趨勢",
            xaxis_title="月份",
            hovermode='x unified',
            height=400
        )
        fig_trend.update_yaxes(title_text="花費 (TWD)", secondary_y=False)
        fig_trend.update_yaxes(title_text="平均 ROAS", secondary_y=True)

        st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")

    # ========== 使用提示 ==========
    with st.expander("💡 使用提示"):
        st.markdown("""
### 📚 功能說明

**多維度篩選**：
- 使用左側邊欄進行多條件篩選
- 支援日期、活動、受眾、品質、狀態、ROAS、花費等維度
- 篩選條件即時生效

**欄位自訂**：
- 核心欄位模式：顯示最重要的 20 個欄位
- 全部欄位模式：顯示所有 106 個欄位
- 自訂模式：自由選擇想要顯示的欄位

**排序與搜尋**：
- 關鍵字搜尋：可搜尋活動、廣告組合、廣告名稱
- 排序功能：按任意欄位升序或降序排列

**資料匯出**：
- CSV：輕量級格式，適合快速分析
- Excel：支援多工作表，包含統計資訊
- 篩選設定：記錄當前篩選條件

**快速洞察**：
- 自動顯示 Top 5 表現廣告
- 標示需改善的廣告
- 月度趨勢一目了然
        """)

if __name__ == "__main__":
    show_detailed_data_table()
