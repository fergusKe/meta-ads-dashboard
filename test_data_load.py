#!/usr/bin/env python3
"""測試數據載入"""
from utils.data_loader import load_meta_ads_data

df = load_meta_ads_data()
if df is not None:
    print('✅ 數據載入成功')
    print(f'📊 總行數: {len(df):,}')
    print(f'📋 欄位數: {len(df.columns)}')
    print(f'📅 日期範圍: {df["開始"].min()} 到 {df["開始"].max()}')
    print(f'\n關鍵欄位檢查:')
    print(f'  - 行銷活動數: {df["行銷活動名稱"].nunique()}')
    print(f'  - 廣告組合數: {df["廣告組合名稱"].nunique()}')
    print(f'  - 廣告數: {df["廣告名稱"].nunique()}')
    print(f'  - 平均 ROAS: {df["購買 ROAS（廣告投資報酬率）"].mean():.2f}')
    print(f'  - 總花費: ${df["花費金額 (TWD)"].sum():,.0f}')
else:
    print('❌ 數據載入失敗')
