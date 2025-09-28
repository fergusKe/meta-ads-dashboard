import pandas as pd
import streamlit as st
from datetime import datetime
import os

@st.cache_data
def load_meta_ads_data(file_path="耘初茶食.xlsx"):
    """
    載入並預處理 Meta 廣告數據

    Args:
        file_path (str): Excel 檔案路徑

    Returns:
        pd.DataFrame: 處理後的數據框架
    """
    try:
        # 載入 Excel 檔案
        df = pd.read_excel(file_path)

        # 基本資訊顯示
        st.sidebar.success(f"✅ 數據載入成功：{len(df)} 筆記錄")

        # 數據預處理
        df = preprocess_data(df)

        return df

    except FileNotFoundError:
        st.error(f"❌ 找不到檔案：{file_path}")
        return None
    except Exception as e:
        st.error(f"❌ 數據載入失敗：{str(e)}")
        return None

def preprocess_data(df):
    """
    數據預處理

    Args:
        df (pd.DataFrame): 原始數據框架

    Returns:
        pd.DataFrame: 處理後的數據框架
    """
    # 處理日期欄位
    date_columns = ['開始', '結束時間', '分析報告開始', '分析報告結束']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # 計算投放天數
    if '開始' in df.columns and '結束時間' in df.columns:
        df['投放天數'] = (df['結束時間'] - df['開始']).dt.days + 1
        df['投放天數'] = df['投放天數'].fillna(1)  # 預設至少1天

    # 計算日均花費
    if '花費金額 (TWD)' in df.columns and '投放天數' in df.columns:
        df['日均花費'] = df['花費金額 (TWD)'] / df['投放天數']

    # 填充數值型欄位的缺失值
    numeric_columns = df.select_dtypes(include=['number']).columns
    df[numeric_columns] = df[numeric_columns].fillna(0)

    # 填充文字型欄位的缺失值
    text_columns = df.select_dtypes(include=['object']).columns
    df[text_columns] = df[text_columns].fillna('未知')

    return df

def calculate_summary_metrics(df):
    """
    計算摘要指標

    Args:
        df (pd.DataFrame): 數據框架

    Returns:
        dict: 摘要指標字典
    """
    if df is None or df.empty:
        return {}

    metrics = {
        'total_spend': df['花費金額 (TWD)'].sum(),
        'total_purchases': df['購買次數'].sum(),
        'total_reach': df['觸及人數'].sum(),
        'total_impressions': df['曝光次數'].sum(),
        'avg_roas': df['購買 ROAS（廣告投資報酬率）'].mean(),
        'avg_cpa': df['每次購買的成本'].mean(),
        'avg_ctr': df['CTR（全部）'].mean(),
        'avg_cpm': df['CPM（每千次廣告曝光成本）'].mean(),
        'conversion_rate': (df['購買次數'].sum() / df['觸及人數'].sum() * 100) if df['觸及人數'].sum() > 0 else 0,
        'total_records': len(df),
        'date_range': {
            'start': df['開始'].min() if '開始' in df.columns and not df['開始'].isna().all() else None,
            'end': df['結束時間'].max() if '結束時間' in df.columns and not df['結束時間'].isna().all() else None
        }
    }

    return metrics

def get_campaign_status_counts(df):
    """
    獲取活動狀態統計

    Args:
        df (pd.DataFrame): 數據框架

    Returns:
        dict: 狀態統計字典
    """
    if df is None or df.empty:
        return {'good': 0, 'warning': 0, 'poor': 0}

    # 根據 ROAS 分類活動表現
    good_campaigns = len(df[df['購買 ROAS（廣告投資報酬率）'] >= 3.0])
    warning_campaigns = len(df[(df['購買 ROAS（廣告投資報酬率）'] >= 1.0) &
                                (df['購買 ROAS（廣告投資報酬率）'] < 3.0)])
    poor_campaigns = len(df[df['購買 ROAS（廣告投資報酬率）'] < 1.0])

    return {
        'good': good_campaigns,
        'warning': warning_campaigns,
        'poor': poor_campaigns
    }

def filter_data_by_date_range(df, start_date, end_date):
    """
    根據日期範圍篩選數據

    Args:
        df (pd.DataFrame): 數據框架
        start_date (datetime): 開始日期
        end_date (datetime): 結束日期

    Returns:
        pd.DataFrame: 篩選後的數據框架
    """
    if df is None or df.empty:
        return df

    # 優先使用廣告投放日期('開始')進行篩選
    if '開始' in df.columns:
        date_column = '開始'

        # 先移除日期為空的記錄
        df_with_dates = df.dropna(subset=[date_column])

        if df_with_dates.empty:
            st.warning("⚠️ 所有記錄的廣告開始日期都為空")
            return pd.DataFrame()

        # 使用廣告投放日期進行篩選
        mask = (df_with_dates[date_column] >= pd.Timestamp(start_date)) & (df_with_dates[date_column] <= pd.Timestamp(end_date))
        filtered_df = df_with_dates[mask]

        if filtered_df.empty:
            st.warning(f"⚠️ 在 {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')} 期間沒有廣告投放數據")
        else:
            st.info(f"📅 已篩選廣告投放期間 {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')} 的數據，共 {len(filtered_df)} 筆記錄")

        return filtered_df

    # 備用：如果沒有開始日期，嘗試使用分析報告日期
    elif '分析報告開始' in df.columns:
        # 先移除日期為空的記錄
        df_with_dates = df.dropna(subset=['分析報告開始'])

        if df_with_dates.empty:
            st.warning("⚠️ 所有記錄的分析報告日期都為空")
            return pd.DataFrame()

        # 檢查篩選範圍是否與分析報告期間重疊
        report_start = df_with_dates['分析報告開始'].iloc[0].date()
        report_end = df_with_dates['分析報告結束'].iloc[0].date() if '分析報告結束' in df_with_dates.columns else report_start

        # 如果選擇的範圍與報告期間有重疊，返回所有數據
        if start_date <= report_end and end_date >= report_start:
            filtered_df = df_with_dates
            st.info(f"📅 分析報告期間 ({report_start} 至 {report_end}) 與選擇範圍重疊，顯示所有 {len(filtered_df)} 筆記錄")
        else:
            filtered_df = pd.DataFrame()
            st.warning(f"⚠️ 選擇的時間範圍與分析報告期間 ({report_start} 至 {report_end}) 不重疊")

        return filtered_df

    else:
        st.warning("⚠️ 數據中缺少日期欄位，無法進行日期篩選")
        return df

def export_data_to_csv(df, filename_prefix="meta_ads_export"):
    """
    匯出數據為 CSV 格式

    Args:
        df (pd.DataFrame): 要匯出的數據框架
        filename_prefix (str): 檔案名前綴

    Returns:
        str: CSV 字串
    """
    if df is None or df.empty:
        return ""

    # 生成檔案名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.csv"

    # 轉換為 CSV
    csv_string = df.to_csv(index=False, encoding='utf-8-sig')

    return csv_string, filename

def validate_data_quality(df):
    """
    檢查數據品質

    Args:
        df (pd.DataFrame): 數據框架

    Returns:
        dict: 數據品質報告
    """
    if df is None or df.empty:
        return {"status": "error", "message": "數據為空"}

    quality_report = {
        "status": "good",
        "total_records": len(df),
        "missing_data": {},
        "warnings": [],
        "errors": []
    }

    # 檢查關鍵欄位的缺失情況
    key_columns = ['花費金額 (TWD)', '購買次數', '購買 ROAS（廣告投資報酬率）', '觸及人數']

    for col in key_columns:
        if col in df.columns:
            missing_count = df[col].isna().sum()
            missing_percentage = (missing_count / len(df)) * 100

            quality_report["missing_data"][col] = {
                "count": missing_count,
                "percentage": missing_percentage
            }

            if missing_percentage > 50:
                quality_report["errors"].append(f"{col} 缺失率過高：{missing_percentage:.1f}%")
                quality_report["status"] = "error"
            elif missing_percentage > 20:
                quality_report["warnings"].append(f"{col} 缺失率較高：{missing_percentage:.1f}%")
                if quality_report["status"] == "good":
                    quality_report["status"] = "warning"
        else:
            quality_report["errors"].append(f"缺少關鍵欄位：{col}")
            quality_report["status"] = "error"

    return quality_report