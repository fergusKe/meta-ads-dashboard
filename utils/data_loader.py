import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv


DEFAULT_DATA_FILE = "耘初茶食.xlsx"

# 確保在匯入時就載入 .env 參數，便於 CLI 腳本與 Streamlit 共用
load_dotenv()


def _resolve_data_path(file_path: str | None) -> Path:
    """根據參數與環境變數取得實際資料路徑"""
    candidate = file_path or os.getenv("DATA_FILE_PATH") or DEFAULT_DATA_FILE
    return Path(candidate).expanduser()


def _noop_cache(*args, **kwargs):
    def decorator(func):
        return func

    return decorator


cache_data = getattr(st, "cache_data", None) or _noop_cache


def _ui_call(method: str, *args, **kwargs):
    fn = getattr(st, method, None)
    if callable(fn):
        return fn(*args, **kwargs)
    return None


def _sidebar_call(method: str, *args, **kwargs):
    sidebar = getattr(st, "sidebar", None)
    fn = getattr(sidebar, method, None) if sidebar else None
    if callable(fn):
        return fn(*args, **kwargs)
    return None


@cache_data(show_spinner=False)
def _load_and_preprocess_data(resolved_path: str) -> pd.DataFrame:
    """載入 Excel 並套用預處理（供 Streamlit 快取使用）"""
    df = pd.read_excel(resolved_path)
    return preprocess_data(df)


def load_meta_ads_data(
    file_path: str | None = None,
    show_sidebar_info: bool = True,
    sync_creative_store: bool = False,
) -> pd.DataFrame | None:
    """載入並預處理 Meta 廣告數據，供各頁面共用

    Args:
        file_path: 指定資料路徑，未提供則依序取環境變數與預設檔名
        show_sidebar_info: 是否於側欄顯示資料來源與筆數

    Returns:
        預處理後的數據框架，若載入失敗則回傳 None
    """
    resolved_path = _resolve_data_path(file_path)

    try:
        df = _load_and_preprocess_data(str(resolved_path))
    except FileNotFoundError:
        _ui_call("error", f"❌ 找不到檔案：{resolved_path}")
        return None
    except Exception as exc:
        _ui_call("error", f"❌ 數據載入失敗：{exc}")
        return None

    if show_sidebar_info:
        _sidebar_call("success", f"✅ 數據載入成功：{len(df)} 筆記錄")
        display_path = resolved_path.resolve().as_posix() if resolved_path.exists() else resolved_path.as_posix()
        _sidebar_call("caption", f"📂 數據來源：{display_path}")

    if sync_creative_store:
        try:
            from utils import creative_store

            creative_store.sync_from_meta_ads(df)
        except Exception as exc:
            _ui_call("warning", f"⚠️ 素材成效資料同步失敗：{exc}")

    return df

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

    # 從月份欄位提取年月
    if '月' in df.columns:
        df['月份'] = pd.to_datetime(df['月'], errors='coerce')
        df['年月'] = df['月份'].dt.to_period('M').astype(str)

    # 計算投放天數
    if '開始' in df.columns and '結束時間' in df.columns:
        df['投放天數'] = (df['結束時間'] - df['開始']).dt.days + 1
        df['投放天數'] = df['投放天數'].fillna(1)  # 預設至少1天

    # 計算日均花費
    if '花費金額 (TWD)' in df.columns and '投放天數' in df.columns:
        df['日均花費'] = df['花費金額 (TWD)'] / df['投放天數']

    # 處理預算欄位（轉為數值）
    budget_columns = ['廣告組合預算', '行銷活動預算', '日預算']
    for col in budget_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 計算轉換漏斗指標
    df = calculate_funnel_metrics(df)

    # 處理品質排名（轉為數值）
    df = process_quality_rankings(df)

    # 填充數值型欄位的缺失值
    numeric_columns = df.select_dtypes(include=['number']).columns
    df[numeric_columns] = df[numeric_columns].fillna(0)

    # 填充文字型欄位的缺失值
    text_columns = df.select_dtypes(include=['object']).columns
    df[text_columns] = df[text_columns].fillna('未知')

    return df

def calculate_funnel_metrics(df):
    """
    計算轉換漏斗各階段指標

    Args:
        df (pd.DataFrame): 數據框架

    Returns:
        pd.DataFrame: 新增漏斗指標的數據框架
    """
    # 點擊率
    if '連結點擊次數' in df.columns and '曝光次數' in df.columns:
        df['點擊率'] = (df['連結點擊次數'] / df['曝光次數'] * 100).replace([float('inf'), -float('inf')], 0)

    # 頁面瀏覽率
    if '連結頁面瀏覽次數' in df.columns and '連結點擊次數' in df.columns:
        df['頁面瀏覽率'] = (df['連結頁面瀏覽次數'] / df['連結點擊次數'] * 100).replace([float('inf'), -float('inf')], 0)

    # 內容瀏覽率
    if '內容瀏覽次數' in df.columns and '連結頁面瀏覽次數' in df.columns:
        df['內容瀏覽率'] = (df['內容瀏覽次數'] / df['連結頁面瀏覽次數'] * 100).replace([float('inf'), -float('inf')], 0)

    # 加購率
    if '加到購物車次數' in df.columns and '內容瀏覽次數' in df.columns:
        df['加購率'] = (df['加到購物車次數'] / df['內容瀏覽次數'] * 100).replace([float('inf'), -float('inf')], 0)

    # 結帳率
    if '開始結帳次數' in df.columns and '加到購物車次數' in df.columns:
        df['結帳率'] = (df['開始結帳次數'] / df['加到購物車次數'] * 100).replace([float('inf'), -float('inf')], 0)

    # 購買完成率
    if '購買次數' in df.columns and '開始結帳次數' in df.columns:
        df['購買完成率'] = (df['購買次數'] / df['開始結帳次數'] * 100).replace([float('inf'), -float('inf')], 0)

    # 整體轉換率（從觸及到購買）
    if '購買次數' in df.columns and '觸及人數' in df.columns:
        df['整體轉換率'] = (df['購買次數'] / df['觸及人數'] * 100).replace([float('inf'), -float('inf')], 0)

    return df

def process_quality_rankings(df):
    """
    處理品質排名欄位，轉換為數值分數

    Args:
        df (pd.DataFrame): 數據框架

    Returns:
        pd.DataFrame: 處理後的數據框架
    """
    ranking_map = {
        '平均以上': 3,
        'Above Average': 3,
        '平均': 2,
        'Average': 2,
        '平均以下': 1,
        'Below Average': 1,
        '未知': 0,
        '-': 0,  # 處理破折號
        '': 0
    }

    ranking_columns = ['品質排名', '互動率排名', '轉換率排名']

    for col in ranking_columns:
        if col in df.columns:
            # 先將 NaN 轉為字串，再處理破折號
            df[col] = df[col].fillna('-')
            # 創建數值版本
            df[f'{col}_分數'] = df[col].map(ranking_map).fillna(0)
            # 將破折號統一為「未知」以便圖表顯示
            df[col] = df[col].replace('-', '未知')

    # 計算綜合品質分數（轉換率權重最高）
    if all(f'{col}_分數' in df.columns for col in ranking_columns):
        df['綜合品質分數'] = (
            df['品質排名_分數'] * 0.25 +
            df['互動率排名_分數'] * 0.25 +
            df['轉換率排名_分數'] * 0.5
        )

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

    # 基本成效指標
    metrics = {
        'total_spend': df['花費金額 (TWD)'].sum(),
        'total_reach': df['觸及人數'].sum(),
        'total_impressions': df['曝光次數'].sum(),
        'total_clicks': df['連結點擊次數'].sum() if '連結點擊次數' in df.columns else 0,
        'total_page_views': df['連結頁面瀏覽次數'].sum() if '連結頁面瀏覽次數' in df.columns else 0,
        'total_content_views': df['內容瀏覽次數'].sum() if '內容瀏覽次數' in df.columns else 0,
        'total_add_to_cart': df['加到購物車次數'].sum() if '加到購物車次數' in df.columns else 0,
        'total_checkout': df['開始結帳次數'].sum() if '開始結帳次數' in df.columns else 0,
        'total_purchases': df['購買次數'].sum() if '購買次數' in df.columns else 0,

        # 平均指標
        'avg_frequency': df['頻率'].mean() if '頻率' in df.columns else 0,
        'avg_ctr': df['CTR（全部）'].mean() if 'CTR（全部）' in df.columns else 0,
        'avg_cpm': df['CPM（每千次廣告曝光成本）'].mean() if 'CPM（每千次廣告曝光成本）' in df.columns else 0,
        'avg_cpc': df['CPC（單次連結點擊成本）'].mean() if 'CPC（單次連結點擊成本）' in df.columns else 0,
        'avg_cpa': df['每次購買的成本'].mean() if '每次購買的成本' in df.columns else 0,
        'avg_roas': df['購買 ROAS（廣告投資報酬率）'].mean() if '購買 ROAS（廣告投資報酬率）' in df.columns else 0,

        # 轉換率指標
        'click_rate': (df['連結點擊次數'].sum() / df['曝光次數'].sum() * 100) if df['曝光次數'].sum() > 0 else 0,
        'page_view_rate': (df['連結頁面瀏覽次數'].sum() / df['連結點擊次數'].sum() * 100) if df['連結點擊次數'].sum() > 0 and '連結頁面瀏覽次數' in df.columns else 0,
        'add_to_cart_rate': (df['加到購物車次數'].sum() / df['內容瀏覽次數'].sum() * 100) if df['內容瀏覽次數'].sum() > 0 and '加到購物車次數' in df.columns else 0,
        'checkout_rate': (df['開始結帳次數'].sum() / df['加到購物車次數'].sum() * 100) if df['加到購物車次數'].sum() > 0 and '開始結帳次數' in df.columns else 0,
        'purchase_rate': (df['購買次數'].sum() / df['開始結帳次數'].sum() * 100) if df['開始結帳次數'].sum() > 0 and '購買次數' in df.columns else 0,
        'overall_conversion_rate': (df['購買次數'].sum() / df['觸及人數'].sum() * 100) if df['觸及人數'].sum() > 0 and '購買次數' in df.columns else 0,

        # 其他資訊
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
            _ui_call("warning", "⚠️ 所有記錄的廣告開始日期都為空")
            return pd.DataFrame()

        # 使用廣告投放日期進行篩選
        mask = (df_with_dates[date_column] >= pd.Timestamp(start_date)) & (df_with_dates[date_column] <= pd.Timestamp(end_date))
        filtered_df = df_with_dates[mask]

        if filtered_df.empty:
            _ui_call(
                "warning",
                f"⚠️ 在 {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')} 期間沒有廣告投放數據",
            )
        else:
            _ui_call(
                "info",
                f"📅 已篩選廣告投放期間 {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')} 的數據，共 {len(filtered_df)} 筆記錄",
            )

        return filtered_df

    # 備用：如果沒有開始日期，嘗試使用分析報告日期
    elif '分析報告開始' in df.columns:
        # 先移除日期為空的記錄
        df_with_dates = df.dropna(subset=['分析報告開始'])

        if df_with_dates.empty:
            _ui_call("warning", "⚠️ 所有記錄的分析報告日期都為空")
            return pd.DataFrame()

        # 檢查篩選範圍是否與分析報告期間重疊
        report_start = df_with_dates['分析報告開始'].iloc[0].date()
        report_end = df_with_dates['分析報告結束'].iloc[0].date() if '分析報告結束' in df_with_dates.columns else report_start

        # 如果選擇的範圍與報告期間有重疊，返回所有數據
        if start_date <= report_end and end_date >= report_start:
            filtered_df = df_with_dates
            _ui_call(
                "info",
                f"📅 分析報告期間 ({report_start} 至 {report_end}) 與選擇範圍重疊，顯示所有 {len(filtered_df)} 筆記錄",
            )
        else:
            filtered_df = pd.DataFrame()
            _ui_call(
                "warning",
                f"⚠️ 選擇的時間範圍與分析報告期間 ({report_start} 至 {report_end}) 不重疊",
            )

        return filtered_df

    else:
        _ui_call("warning", "⚠️ 數據中缺少日期欄位，無法進行日期篩選")
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
