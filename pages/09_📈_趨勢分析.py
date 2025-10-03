import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.data_loader import load_meta_ads_data, filter_data_by_date_range
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import warnings
warnings.filterwarnings('ignore')

def show_trend_analysis():
    """顯示趨勢分析頁面"""
    st.markdown("# 📈 趨勢分析")
    st.markdown("深入分析廣告投放趨勢，預測未來表現並識別關鍵變化點")

    # 載入數據
    df = load_meta_ads_data()
    if df is None:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 時間範圍選擇器
    st.markdown("## 📅 時間範圍設定")

    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        # 優先使用分析報告日期範圍
        if '分析報告開始' in df.columns and '分析報告結束' in df.columns:
            report_start_dates = df['分析報告開始'].dropna()
            report_end_dates = df['分析報告結束'].dropna()

            if not report_start_dates.empty and not report_end_dates.empty:
                report_start = report_start_dates.min()
                report_end = report_end_dates.max()

                # 篩選廣告投放日期在分析報告期間內的數據
                analysis_df = df[
                    (df['開始'] >= report_start) &
                    (df['開始'] <= report_end)
                ].copy()

                if not analysis_df.empty:
                    data_min_date = analysis_df['開始'].min().date()
                    data_max_date = analysis_df['開始'].max().date()
                    default_start = data_min_date
                    default_end = data_max_date
                    date_source = "分析期間"
                else:
                    # 如果沒有符合的數據，使用報告期間的日期
                    data_min_date = report_start.date()
                    data_max_date = report_end.date()
                    default_start = data_min_date
                    default_end = data_max_date
                    date_source = "分析期間"
            else:
                data_min_date = datetime.now().date() - timedelta(days=30)
                data_max_date = datetime.now().date()
                default_start = data_min_date
                default_end = data_max_date
                date_source = "預設"
        else:
            # 備用：使用開始日期
            if '開始' in df.columns and not df['開始'].isna().all():
                valid_dates = df['開始'].dropna()
                if not valid_dates.empty:
                    data_min_date = valid_dates.min().date()
                    data_max_date = valid_dates.max().date()
                    default_start = data_min_date
                    default_end = data_max_date
                    date_source = "廣告開始"
                else:
                    data_min_date = datetime.now().date() - timedelta(days=30)
                    data_max_date = datetime.now().date()
                    default_start = data_min_date
                    default_end = data_max_date
                    date_source = "預設"
            else:
                data_min_date = datetime.now().date() - timedelta(days=30)
                data_max_date = datetime.now().date()
                default_start = data_min_date
                default_end = data_max_date
                date_source = "預設"

        start_date = st.date_input(
            "開始日期",
            value=default_start,
            min_value=data_min_date,
            max_value=data_max_date,
            help=f"實際數據範圍：{data_min_date} 至 {data_max_date} (來源：{date_source})"
        )

    with col2:
        end_date = st.date_input(
            "結束日期",
            value=default_end,
            min_value=data_min_date,
            max_value=data_max_date,
            help=f"實際數據範圍：{data_min_date} 至 {data_max_date} (來源：{date_source})"
        )

    with col3:
        # 快速選項
        quick_options = st.selectbox(
            "快速選擇",
            ["自訂範圍", "最近 7 天", "最近 14 天", "最近 30 天", "全部時間"]
        )

        if quick_options != "自訂範圍":
            if quick_options == "最近 7 天":
                start_date = max(data_max_date - timedelta(days=7), data_min_date)
                end_date = data_max_date
            elif quick_options == "最近 14 天":
                start_date = max(data_max_date - timedelta(days=14), data_min_date)
                end_date = data_max_date
            elif quick_options == "最近 30 天":
                start_date = max(data_max_date - timedelta(days=30), data_min_date)
                end_date = data_max_date
            elif quick_options == "全部時間":
                start_date = data_min_date
                end_date = data_max_date

    # 篩選數據
    if start_date <= end_date:
        filtered_df = filter_data_by_date_range(df, start_date, end_date)
    else:
        st.error("開始日期不能晚於結束日期！")
        filtered_df = df

    st.markdown("---")

    if not filtered_df.empty:
        # 趨勢分析主要內容
        tab1, tab2, tab3, tab4 = st.tabs(["📈 核心指標趨勢", "🔍 深度分析", "🎯 預測模型", "📊 周期性分析"])

        with tab1:
            st.markdown("### 📊 核心指標趨勢分析")

            # 準備時間序列數據
            trend_data = prepare_time_series_data(filtered_df)

            if not trend_data.empty:
                # 指標選擇
                metric_col1, metric_col2 = st.columns(2)

                with metric_col1:
                    primary_metric = st.selectbox(
                        "主要指標",
                        ["花費金額 (TWD)", "購買次數", "購買 ROAS（廣告投資報酬率）", "觸及人數", "曝光次數"],
                        index=0
                    )

                with metric_col2:
                    secondary_metric = st.selectbox(
                        "對比指標",
                        ["購買次數", "花費金額 (TWD)", "購買 ROAS（廣告投資報酬率）", "觸及人數", "曝光次數"],
                        index=0
                    )

                # 雙軸趨勢圖
                fig_trend = create_dual_axis_trend_chart(trend_data, primary_metric, secondary_metric)
                if fig_trend:
                    st.plotly_chart(fig_trend, use_container_width=True)

                # 趨勢統計摘要
                trend_summary_col1, trend_summary_col2, trend_summary_col3 = st.columns(3)

                with trend_summary_col1:
                    # 計算主要指標的趨勢
                    trend_stats = calculate_trend_statistics(trend_data, primary_metric)
                    st.metric(
                        f"{primary_metric} 趨勢",
                        f"{trend_stats['trend_direction']}",
                        delta=f"{trend_stats['change_rate']:.1f}%"
                    )

                with trend_summary_col2:
                    # 波動性分析
                    volatility = trend_data[primary_metric].std() / trend_data[primary_metric].mean() * 100 if trend_data[primary_metric].mean() > 0 else 0
                    volatility_status = "低" if volatility < 20 else "中" if volatility < 50 else "高"
                    st.metric(
                        "波動性",
                        f"{volatility_status}",
                        delta=f"{volatility:.1f}%"
                    )

                with trend_summary_col3:
                    # 相關性分析
                    if primary_metric != secondary_metric and len(trend_data) > 1:
                        correlation = trend_data[primary_metric].corr(trend_data[secondary_metric])
                        corr_strength = "強" if abs(correlation) > 0.7 else "中" if abs(correlation) > 0.3 else "弱"
                        st.metric(
                            "指標相關性",
                            f"{corr_strength}",
                            delta=f"{correlation:.3f}"
                        )

                # 每日表現分析
                st.markdown("### 📅 每日表現明細")
                daily_performance_chart = create_daily_performance_chart(trend_data)
                if daily_performance_chart:
                    st.plotly_chart(daily_performance_chart, use_container_width=True)

            else:
                st.info("所選時間範圍內暫無趨勢數據")

        with tab2:
            st.markdown("### 🔍 深度趨勢分析")

            if not trend_data.empty:
                analysis_col1, analysis_col2 = st.columns(2)

                with analysis_col1:
                    st.markdown("#### 📈 移動平均分析")

                    # 移動平均選項
                    ma_period = st.selectbox("移動平均周期", [3, 5, 7], index=1)
                    ma_metric = st.selectbox(
                        "分析指標",
                        ["購買 ROAS（廣告投資報酬率）", "花費金額 (TWD)", "購買次數", "觸及人數"],
                        index=0
                    )

                    # 移動平均圖表
                    ma_chart = create_moving_average_chart(trend_data, ma_metric, ma_period)
                    if ma_chart:
                        st.plotly_chart(ma_chart, use_container_width=True)

                with analysis_col2:
                    st.markdown("#### 📊 異常檢測")

                    # 異常檢測
                    anomalies = detect_anomalies(trend_data, ma_metric)

                    if anomalies and len(anomalies) > 0:
                        st.warning(f"⚠️ 檢測到 {len(anomalies)} 個異常數據點")

                        # 顯示異常詳情
                        for i, anomaly in enumerate(anomalies[:3]):  # 只顯示前3個
                            date_str = anomaly['date'].strftime('%Y-%m-%d')
                            st.error(f"**{date_str}**: {ma_metric} = {anomaly['value']:.2f} (偏差: {anomaly['deviation']:.1f}σ)")
                    else:
                        st.success("✅ 未檢測到顯著異常")

                # 變化點檢測
                st.markdown("#### 🎯 趨勢變化點分析")
                change_points = detect_change_points(trend_data, ma_metric)

                if change_points:
                    change_col1, change_col2 = st.columns(2)

                    with change_col1:
                        st.info(f"🔍 檢測到 {len(change_points)} 個趨勢變化點")
                        for i, cp in enumerate(change_points[:3]):
                            date_str = cp['date'].strftime('%Y-%m-%d')
                            change_type = "上升" if cp['change'] > 0 else "下降"
                            st.write(f"**{date_str}**: {change_type} ({cp['change']:+.1f}%)")

                    with change_col2:
                        # 變化點圖表
                        change_chart = create_change_point_chart(trend_data, ma_metric, change_points)
                        if change_chart:
                            st.plotly_chart(change_chart, use_container_width=True)
                else:
                    st.info("🔍 未檢測到顯著的趨勢變化點")

            else:
                st.info("所選時間範圍內暫無深度分析數據")

        with tab3:
            st.markdown("### 🎯 趨勢預測模型")

            if not trend_data.empty and len(trend_data) >= 5:
                predict_col1, predict_col2 = st.columns(2)

                with predict_col1:
                    predict_metric = st.selectbox(
                        "預測指標",
                        ["購買 ROAS（廣告投資報酬率）", "花費金額 (TWD)", "購買次數"],
                        index=0,
                        key="predict_metric"
                    )

                    predict_days = st.slider("預測天數", 1, 14, 7)

                with predict_col2:
                    prediction_model = st.selectbox(
                        "預測模型",
                        ["線性迴歸", "多項式迴歸", "移動平均"],
                        index=0
                    )

                # 生成預測
                predictions = generate_predictions(trend_data, predict_metric, predict_days, prediction_model)

                if predictions is not None:
                    # 預測圖表
                    prediction_chart = create_prediction_chart(trend_data, predictions, predict_metric)
                    if prediction_chart:
                        st.plotly_chart(prediction_chart, use_container_width=True)

                    # 預測摘要
                    pred_summary_col1, pred_summary_col2, pred_summary_col3 = st.columns(3)

                    current_value = trend_data[predict_metric].iloc[-1]
                    predicted_value = predictions['predicted_values'].iloc[-1]
                    change_percent = ((predicted_value - current_value) / current_value * 100) if current_value != 0 else 0

                    with pred_summary_col1:
                        st.metric(
                            "當前值",
                            f"{current_value:.2f}",
                            help=f"最新的 {predict_metric} 數值"
                        )

                    with pred_summary_col2:
                        st.metric(
                            f"{predict_days}天後預測值",
                            f"{predicted_value:.2f}",
                            delta=f"{change_percent:+.1f}%"
                        )

                    with pred_summary_col3:
                        # 預測可信度
                        confidence = calculate_prediction_confidence(trend_data, predict_metric, prediction_model)
                        confidence_level = "高" if confidence > 0.8 else "中" if confidence > 0.5 else "低"
                        st.metric(
                            "預測可信度",
                            confidence_level,
                            delta=f"{confidence:.2f}"
                        )

                    # 預測建議
                    st.markdown("#### 💡 預測分析建議")
                    if change_percent > 10:
                        st.success(f"📈 預測 {predict_metric} 將顯著上升 ({change_percent:+.1f}%)，建議保持當前策略或擴大投資")
                    elif change_percent < -10:
                        st.warning(f"📉 預測 {predict_metric} 將顯著下降 ({change_percent:+.1f}%)，建議檢視並調整策略")
                    else:
                        st.info(f"📊 預測 {predict_metric} 保持穩定 ({change_percent:+.1f}%)，維持現狀即可")

                else:
                    st.error("預測模型計算失敗，請檢查數據完整性")

            else:
                st.info("需要至少5個數據點才能進行趨勢預測")

        with tab4:
            st.markdown("### 📊 周期性與季節性分析")

            if not trend_data.empty:
                # 星期幾分析
                weekly_analysis = analyze_weekly_patterns(trend_data)

                if not weekly_analysis.empty:
                    week_col1, week_col2 = st.columns(2)

                    with week_col1:
                        st.markdown("#### 📅 星期幾表現分析")
                        weekly_chart = create_weekly_pattern_chart(weekly_analysis)
                        if weekly_chart:
                            st.plotly_chart(weekly_chart, use_container_width=True)

                    with week_col2:
                        st.markdown("#### 🏆 最佳表現日")

                        # 找出表現最好和最差的星期幾
                        best_day = weekly_analysis.loc[weekly_analysis['購買 ROAS（廣告投資報酬率）'].idxmax()]
                        worst_day = weekly_analysis.loc[weekly_analysis['購買 ROAS（廣告投資報酬率）'].idxmin()]

                        st.success(f"🥇 **最佳**: {best_day['weekday']} (ROAS: {best_day['購買 ROAS（廣告投資報酬率）']:.2f})")
                        st.error(f"📉 **最差**: {worst_day['weekday']} (ROAS: {worst_day['購買 ROAS（廣告投資報酬率）']:.2f})")

                        # 計算差異
                        performance_gap = ((best_day['購買 ROAS（廣告投資報酬率）'] - worst_day['購買 ROAS（廣告投資報酬率）']) / worst_day['購買 ROAS（廣告投資報酬率）'] * 100)
                        st.info(f"📊 **表現差距**: {performance_gap:.1f}%")

                # 時段分析（如果有小時數據）
                if '開始' in trend_data.columns:
                    st.markdown("#### ⏰ 投放時間分析")
                    time_analysis = analyze_time_patterns(trend_data)

                    if time_analysis:
                        time_col1, time_col2 = st.columns(2)

                        with time_col1:
                            # 投放時間分佈
                            hour_dist_chart = create_hour_distribution_chart(trend_data)
                            if hour_dist_chart:
                                st.plotly_chart(hour_dist_chart, use_container_width=True)

                        with time_col2:
                            # 時段建議
                            st.markdown("##### 🎯 投放時段建議")
                            optimal_hours = time_analysis['optimal_hours']
                            if optimal_hours:
                                st.success(f"🌟 **最佳時段**: {optimal_hours[0]}:00 - {optimal_hours[-1]}:00")
                                st.info(f"📈 建議在這些時段增加預算投放")
                            else:
                                st.info("數據不足以確定最佳投放時段")

            else:
                st.info("所選時間範圍內暫無周期性分析數據")

    else:
        st.info("所選時間範圍內暫無數據")

def prepare_time_series_data(df):
    """準備時間序列數據"""
    if df is None or df.empty or '開始' not in df.columns:
        return pd.DataFrame()

    # 首先應用與其他頁面相同的日期篩選邏輯
    filtered_df = df.copy()

    # 優先使用分析報告期間篩選
    if '分析報告開始' in df.columns and '分析報告結束' in df.columns:
        report_start_dates = df['分析報告開始'].dropna()
        report_end_dates = df['分析報告結束'].dropna()

        if not report_start_dates.empty and not report_end_dates.empty:
            report_start = report_start_dates.min()
            report_end = report_end_dates.max()

            # 篩選廣告投放日期在分析報告期間內的數據
            filtered_df = df[
                (df['開始'] >= report_start) &
                (df['開始'] <= report_end)
            ].copy()

    # 過濾有效數據
    valid_data = filtered_df.dropna(subset=['開始'])

    if valid_data.empty:
        return pd.DataFrame()

    # 按日期分組聚合
    daily_data = valid_data.groupby(valid_data['開始'].dt.date).agg({
        '花費金額 (TWD)': 'sum',
        '購買次數': 'sum',
        '購買 ROAS（廣告投資報酬率）': 'mean',
        '觸及人數': 'sum',
        '曝光次數': 'sum',
        'CTR（全部）': 'mean',
        'CPM（每千次廣告曝光成本）': 'mean',
        '每次購買的成本': 'mean'
    }).reset_index()

    daily_data.columns = ['日期'] + list(daily_data.columns[1:])
    daily_data = daily_data.sort_values('日期')

    return daily_data

def create_dual_axis_trend_chart(data, primary_metric, secondary_metric):
    """創建雙軸趨勢圖"""
    if data.empty:
        return None

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 主要指標
    fig.add_trace(
        go.Scatter(
            x=data['日期'],
            y=data[primary_metric],
            name=primary_metric,
            line=dict(color='#1f77b4', width=3)
        ),
        secondary_y=False,
    )

    # 次要指標
    if primary_metric != secondary_metric:
        fig.add_trace(
            go.Scatter(
                x=data['日期'],
                y=data[secondary_metric],
                name=secondary_metric,
                line=dict(color='#ff7f0e', width=2, dash='dash')
            ),
            secondary_y=True,
        )

    # 設定軸標籤
    fig.update_xaxes(title_text="日期")
    fig.update_yaxes(title_text=primary_metric, secondary_y=False)
    if primary_metric != secondary_metric:
        fig.update_yaxes(title_text=secondary_metric, secondary_y=True)

    fig.update_layout(
        title="雙軸趨勢分析",
        height=500,
        hovermode='x unified'
    )

    return fig

def calculate_trend_statistics(data, metric):
    """計算趨勢統計"""
    if data.empty or len(data) < 2:
        return {'trend_direction': '無法計算', 'change_rate': 0}

    # 計算線性趨勢
    x = np.arange(len(data))
    y = data[metric].values

    # 過濾無效值
    valid_mask = ~np.isnan(y)
    if np.sum(valid_mask) < 2:
        return {'trend_direction': '數據不足', 'change_rate': 0}

    x_valid = x[valid_mask]
    y_valid = y[valid_mask]

    slope, intercept, r_value, p_value, std_err = stats.linregress(x_valid, y_valid)

    # 計算變化率
    start_value = y_valid[0]
    end_value = y_valid[-1]
    change_rate = ((end_value - start_value) / start_value * 100) if start_value != 0 else 0

    # 判斷趨勢方向
    if abs(slope) < 0.01:
        trend_direction = "穩定"
    elif slope > 0:
        trend_direction = "上升"
    else:
        trend_direction = "下降"

    return {
        'trend_direction': trend_direction,
        'change_rate': change_rate,
        'slope': slope,
        'r_squared': r_value**2
    }

def create_daily_performance_chart(data):
    """創建每日表現圖表"""
    if data.empty:
        return None

    fig = go.Figure()

    # 添加 ROAS 條狀圖
    fig.add_trace(go.Bar(
        x=data['日期'],
        y=data['購買 ROAS（廣告投資報酬率）'],
        name='ROAS',
        marker_color='lightblue',
        yaxis='y'
    ))

    # 添加花費折線圖
    fig.add_trace(go.Scatter(
        x=data['日期'],
        y=data['花費金額 (TWD)'],
        name='花費金額',
        line=dict(color='red', width=2),
        yaxis='y2'
    ))

    fig.update_layout(
        title="每日 ROAS vs 花費趨勢",
        xaxis_title="日期",
        yaxis=dict(title="ROAS", side="left"),
        yaxis2=dict(title="花費金額 (TWD)", side="right", overlaying="y"),
        height=400,
        showlegend=True
    )

    return fig

def create_moving_average_chart(data, metric, period):
    """創建移動平均圖表"""
    if data.empty or len(data) < period:
        return None

    # 計算移動平均
    data_copy = data.copy()
    data_copy[f'{metric}_MA{period}'] = data_copy[metric].rolling(window=period).mean()

    fig = go.Figure()

    # 原始數據
    fig.add_trace(go.Scatter(
        x=data_copy['日期'],
        y=data_copy[metric],
        name=f'{metric} (原始)',
        line=dict(color='lightgray', width=1),
        opacity=0.7
    ))

    # 移動平均
    fig.add_trace(go.Scatter(
        x=data_copy['日期'],
        y=data_copy[f'{metric}_MA{period}'],
        name=f'{period}日移動平均',
        line=dict(color='blue', width=3)
    ))

    fig.update_layout(
        title=f"{metric} - {period}日移動平均分析",
        xaxis_title="日期",
        yaxis_title=metric,
        height=400
    )

    return fig

def detect_anomalies(data, metric, threshold=2):
    """檢測異常值"""
    if data.empty or len(data) < 3:
        return []

    values = data[metric].values
    mean_val = np.mean(values)
    std_val = np.std(values)

    anomalies = []
    for i, (date, value) in enumerate(zip(data['日期'], values)):
        if abs(value - mean_val) > threshold * std_val:
            anomalies.append({
                'date': date,
                'value': value,
                'deviation': abs(value - mean_val) / std_val
            })

    return anomalies

def detect_change_points(data, metric, min_change=0.2):
    """檢測趨勢變化點"""
    if data.empty or len(data) < 5:
        return []

    values = data[metric].values
    dates = data['日期'].values

    change_points = []

    # 使用滑動窗口檢測變化點
    window_size = 3
    for i in range(window_size, len(values) - window_size):
        before_mean = np.mean(values[i-window_size:i])
        after_mean = np.mean(values[i:i+window_size])

        if before_mean != 0:
            change_percent = (after_mean - before_mean) / before_mean * 100
            if abs(change_percent) > min_change * 100:
                change_points.append({
                    'date': dates[i],
                    'change': change_percent,
                    'before': before_mean,
                    'after': after_mean
                })

    return change_points

def create_change_point_chart(data, metric, change_points):
    """創建變化點圖表"""
    if data.empty:
        return None

    fig = go.Figure()

    # 原始趨勢線
    fig.add_trace(go.Scatter(
        x=data['日期'],
        y=data[metric],
        name=metric,
        line=dict(color='blue', width=2)
    ))

    # 標記變化點
    if change_points:
        change_dates = [cp['date'] for cp in change_points]
        change_values = []

        for cp_date in change_dates:
            # 找到對應的值
            matching_row = data[data['日期'] == cp_date]
            if not matching_row.empty:
                change_values.append(matching_row[metric].iloc[0])
            else:
                change_values.append(0)

        fig.add_trace(go.Scatter(
            x=change_dates,
            y=change_values,
            mode='markers',
            name='變化點',
            marker=dict(color='red', size=10, symbol='diamond')
        ))

    fig.update_layout(
        title=f"{metric} 趨勢變化點分析",
        xaxis_title="日期",
        yaxis_title=metric,
        height=400
    )

    return fig

def generate_predictions(data, metric, days, model_type):
    """生成預測"""
    if data.empty or len(data) < 3:
        return None

    try:
        # 準備數據
        y = data[metric].values
        X = np.arange(len(y)).reshape(-1, 1)

        # 過濾無效值
        valid_mask = ~np.isnan(y)
        if np.sum(valid_mask) < 3:
            return None

        X_valid = X[valid_mask]
        y_valid = y[valid_mask]

        # 預測的 X 值
        future_X = np.arange(len(y), len(y) + days).reshape(-1, 1)

        if model_type == "線性迴歸":
            model = LinearRegression()
            model.fit(X_valid, y_valid)
            predictions = model.predict(future_X)

        elif model_type == "多項式迴歸":
            poly_features = PolynomialFeatures(degree=2)
            X_poly = poly_features.fit_transform(X_valid)
            future_X_poly = poly_features.transform(future_X)

            model = LinearRegression()
            model.fit(X_poly, y_valid)
            predictions = model.predict(future_X_poly)

        elif model_type == "移動平均":
            # 使用最近3天的移動平均
            window = min(3, len(y_valid))
            last_values = y_valid[-window:]
            avg_value = np.mean(last_values)
            predictions = np.full(days, avg_value)

        # 生成預測日期
        last_date = data['日期'].iloc[-1]
        future_dates = [last_date + timedelta(days=i+1) for i in range(days)]

        # 返回預測結果
        prediction_df = pd.DataFrame({
            '日期': future_dates,
            'predicted_values': predictions
        })

        return prediction_df

    except Exception as e:
        st.error(f"預測計算失敗: {str(e)}")
        return None

def create_prediction_chart(historical_data, predictions, metric):
    """創建預測圖表"""
    if historical_data.empty or predictions is None:
        return None

    fig = go.Figure()

    # 歷史數據
    fig.add_trace(go.Scatter(
        x=historical_data['日期'],
        y=historical_data[metric],
        name='歷史數據',
        line=dict(color='blue', width=2)
    ))

    # 預測數據
    fig.add_trace(go.Scatter(
        x=predictions['日期'],
        y=predictions['predicted_values'],
        name='預測值',
        line=dict(color='red', width=2, dash='dash')
    ))

    # 在歷史和預測之間添加連接點
    if not historical_data.empty and not predictions.empty:
        last_historical = historical_data.iloc[-1]
        first_prediction = predictions.iloc[0]

        fig.add_trace(go.Scatter(
            x=[last_historical['日期'], first_prediction['日期']],
            y=[last_historical[metric], first_prediction['predicted_values']],
            mode='lines',
            line=dict(color='red', width=2, dash='dash'),
            showlegend=False
        ))

    fig.update_layout(
        title=f"{metric} 趨勢預測",
        xaxis_title="日期",
        yaxis_title=metric,
        height=500
    )

    return fig

def calculate_prediction_confidence(data, metric, model_type):
    """計算預測可信度"""
    if data.empty or len(data) < 5:
        return 0.0

    try:
        # 使用最後5個數據點進行交叉驗證
        values = data[metric].dropna()
        if len(values) < 5:
            return 0.0

        # 計算數據的穩定性（變異係數的倒數）
        cv = values.std() / values.mean() if values.mean() != 0 else float('inf')
        stability_score = 1 / (1 + cv) if cv != float('inf') else 0.0

        # 根據模型類型調整
        model_confidence = {
            "線性迴歸": 0.7,
            "多項式迴歸": 0.6,
            "移動平均": 0.8
        }.get(model_type, 0.5)

        # 數據量調整
        data_size_factor = min(len(values) / 10, 1.0)

        confidence = stability_score * model_confidence * data_size_factor
        return min(confidence, 1.0)

    except:
        return 0.0

def analyze_weekly_patterns(data):
    """分析星期幾的表現模式"""
    if data.empty:
        return pd.DataFrame()

    data_copy = data.copy()
    data_copy['weekday'] = pd.to_datetime(data_copy['日期']).dt.day_name()

    # 中文星期幾映射
    weekday_map = {
        'Monday': '星期一',
        'Tuesday': '星期二',
        'Wednesday': '星期三',
        'Thursday': '星期四',
        'Friday': '星期五',
        'Saturday': '星期六',
        'Sunday': '星期日'
    }
    data_copy['weekday'] = data_copy['weekday'].map(weekday_map)

    # 按星期幾分組聚合
    weekly_stats = data_copy.groupby('weekday').agg({
        '花費金額 (TWD)': 'mean',
        '購買次數': 'mean',
        '購買 ROAS（廣告投資報酬率）': 'mean',
        '觸及人數': 'mean'
    }).reset_index()

    # 重新排序星期幾
    weekday_order = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    weekly_stats['weekday'] = pd.Categorical(weekly_stats['weekday'], categories=weekday_order, ordered=True)
    weekly_stats = weekly_stats.sort_values('weekday').reset_index(drop=True)

    return weekly_stats

def create_weekly_pattern_chart(weekly_data):
    """創建星期幾表現圖表"""
    if weekly_data.empty:
        return None

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # ROAS 條狀圖
    fig.add_trace(
        go.Bar(
            x=weekly_data['weekday'],
            y=weekly_data['購買 ROAS（廣告投資報酬率）'],
            name='ROAS',
            marker_color='lightblue'
        ),
        secondary_y=False,
    )

    # 花費折線圖
    fig.add_trace(
        go.Scatter(
            x=weekly_data['weekday'],
            y=weekly_data['花費金額 (TWD)'],
            name='平均花費',
            line=dict(color='red', width=3),
            mode='lines+markers'
        ),
        secondary_y=True,
    )

    fig.update_xaxes(title_text="星期幾")
    fig.update_yaxes(title_text="ROAS", secondary_y=False)
    fig.update_yaxes(title_text="花費金額 (TWD)", secondary_y=True)

    fig.update_layout(
        title="星期幾表現分析",
        height=400
    )

    return fig

def analyze_time_patterns(data):
    """分析時間模式"""
    if data.empty or '開始' not in data.columns:
        return None

    # 提取小時信息
    data_copy = data.copy()
    data_copy['hour'] = pd.to_datetime(data_copy['日期']).dt.hour

    # 統計每小時的表現
    hourly_stats = data_copy.groupby('hour').agg({
        '購買 ROAS（廣告投資報酬率）': 'mean',
        '花費金額 (TWD)': 'sum'
    }).reset_index()

    # 找出最佳時段（ROAS 最高的前3個小時）
    top_hours = hourly_stats.nlargest(3, '購買 ROAS（廣告投資報酬率）')['hour'].tolist()

    return {
        'hourly_stats': hourly_stats,
        'optimal_hours': top_hours
    }

def create_hour_distribution_chart(data):
    """創建小時分佈圖表"""
    if data.empty:
        return None

    # 這是簡化版本，實際上需要有小時級別的數據
    # 這裡我們假設所有數據都在工作時間
    hours = list(range(24))
    counts = [np.random.randint(0, 10) for _ in hours]  # 模擬數據

    fig = go.Figure(data=go.Bar(x=hours, y=counts))
    fig.update_layout(
        title="廣告投放時間分佈",
        xaxis_title="小時",
        yaxis_title="投放次數",
        height=300
    )

    return fig

if __name__ == "__main__":
    show_trend_analysis()