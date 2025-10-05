import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
from utils.llm_service import get_llm_service
from utils.data_loader import load_meta_ads_data
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="競爭對手分析", page_icon="🌐", layout="wide")

def search_ad_library(search_terms, access_token, limit=10):
    """
    使用 Meta Ad Library API 搜尋廣告

    Args:
        search_terms: 搜尋關鍵字
        access_token: Meta API Access Token
        limit: 返回數量

    Returns:
        廣告列表
    """
    base_url = "https://graph.facebook.com/v18.0/ads_archive"

    params = {
        'access_token': access_token,
        'search_terms': search_terms,
        'ad_reached_countries': 'TW',
        'ad_active_status': 'ALL',
        'limit': limit,
        'fields': 'id,ad_creative_body,ad_creative_link_caption,ad_creative_link_title,page_name,ad_delivery_start_time,impressions,spend'
    }

    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if 'data' in data:
            return data['data']
        else:
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"API 請求失敗：{str(e)}")
        return []
    except Exception as e:
        st.error(f"發生錯誤：{str(e)}")
        return []

def analyze_competitor_ads_with_ai(our_ads, competitor_ads):
    """使用 AI 分析競品廣告與我們廣告的差異"""
    llm_service = get_llm_service()

    if not llm_service.is_available():
        return "❌ AI 功能目前無法使用，請設定 OPENAI_API_KEY"

    # 準備我們的廣告摘要
    our_headlines = our_ads['標題'].value_counts().head(10).to_dict() if '標題' in our_ads.columns else {}
    our_avg_roas = our_ads['購買 ROAS（廣告投資報酬率）'].mean() if '購買 ROAS（廣告投資報酬率）' in our_ads.columns else 0

    # 準備競品廣告摘要
    competitor_summary = []
    for ad in competitor_ads[:10]:
        competitor_summary.append({
            "品牌": ad.get('page_name', '未知'),
            "標題": ad.get('ad_creative_link_title', ''),
            "內文": ad.get('ad_creative_body', '')[:200] if ad.get('ad_creative_body') else '',
            "曝光": ad.get('impressions', {}).get('lower_bound', 'N/A')
        })

    # 構建 Prompt
    prompt = f"""
請分析以下競品廣告與我們的廣告，找出差異化機會。

## 我們的廣告表現
- **平均 ROAS**：{our_avg_roas:.2f}
- **熱門標題（前 10）**：
{json.dumps(our_headlines, ensure_ascii=False, indent=2)}

## 競品廣告分析
{json.dumps(competitor_summary, ensure_ascii=False, indent=2)}

## 請提供以下分析：

### 1. 🎯 競品強項分析（3-5 點）
分析競品廣告為什麼吸引人：
- 標題策略
- 文案風格
- 訴求重點
- 視覺呈現（如可判斷）

### 2. 🔍 我們的差異點（3-5 點）
找出我們與競品的差異：
- 我們做得更好的地方
- 我們的獨特優勢
- 可以強化的特色

### 3. 💡 差異化文案建議（5 個）
基於競品分析，提供差異化的廣告文案建議：
- **標題範例**：具體文案 + 為什麼有效
- 確保與競品有明確區隔

格式範例：
```
標題：「XXX - 您的專屬 YYY」
策略：強調個性化服務，區別於競品的大眾化訴求
預期效果：提升 CTR 15-20%
```

### 4. 🚫 避免同質化策略（3-5 個）
如何避免與競品廣告太相似：
- 不該模仿的點
- 要避開的文案套路
- 獨特定位建議

### 5. 📊 市場洞察
基於競品廣告趨勢，提供市場洞察：
- 目前市場主流訴求
- 未被滿足的需求
- 新興趨勢機會
- 下一波廣告方向建議

### 6. ⚡ 立即行動計畫
3 個可立即執行的優化建議：
- 🔴 高優先級（本週執行）
- 🟡 中優先級（2 週內執行）
- 🟢 低優先級（持續觀察）

請用繁體中文回答，語氣專業但易懂，提供可執行的具體建議，使用 Markdown 格式。
"""

    return llm_service.generate_insights(
        prompt=prompt,
        model="gpt-4o-mini",
        max_tokens=2500,
        temperature=0.7
    )

def compare_ad_performance(our_ads, competitor_count):
    """比較我們的廣告與競品數量"""
    our_active_count = len(our_ads)

    comparison_data = pd.DataFrame({
        '類別': ['我們的廣告', '競品廣告'],
        '數量': [our_active_count, competitor_count],
        '狀態': ['活躍', '活躍']
    })

    return comparison_data

def main():
    st.title("🌐 競爭對手廣告分析")
    st.markdown("""
    使用 **Meta Ad Library API** 分析競品廣告，找出差異化機會。

    **功能**：
    - 🔍 搜尋競品廣告
    - 📊 分析競品策略
    - 💡 生成差異化文案
    - 🎯 避免同質化競爭
    """)

    # 載入我們的廣告數據
    our_ads = load_meta_ads_data()
    if our_ads is None:
        st.error("無法載入廣告數據，請檢查數據檔案。")
        return

    # 主要內容 - 搜尋設定
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("⚙️ 搜尋設定")

        # API Token 輸入
        api_token = st.text_input(
            "Meta Ad Library API Token",
            type="password",
            help="請輸入您的 Meta Ad Library API Access Token"
        )

        # 搜尋關鍵字
        search_keywords = st.text_input(
            "競品關鍵字",
            placeholder="例如：茶葉、有機茶",
            help="輸入競品相關關鍵字"
        )

        # 搜尋數量
        result_limit = st.slider(
            "搜尋數量",
            min_value=5,
            max_value=50,
            value=10,
            step=5
        )

    with col2:
        st.subheader("📌 如何取得 API Token")

        st.info("""
1. 前往 [Meta for Developers](https://developers.facebook.com/)
2. 建立應用程式
3. 啟用 Ad Library API
4. 取得 Access Token

**注意**：需要驗證身分
        """)

    st.divider()

    # 主要內容
    tab1, tab2, tab3 = st.tabs(["🔍 搜尋競品", "📊 AI 分析", "💡 差異化策略"])

    with tab1:
        st.markdown("## 🔍 搜尋競品廣告")

        if not api_token:
            st.warning("⚠️ 請在側邊欄輸入 Meta Ad Library API Token")
            st.markdown("""
            ### 🆓 無 API Token 的替代方案

            您可以手動前往 [Meta Ad Library](https://www.facebook.com/ads/library/) 搜尋競品廣告：

            1. 輸入競品品牌名稱或關鍵字
            2. 選擇「台灣」作為地區
            3. 篩選「所有廣告」
            4. 手動記錄競品廣告的標題、文案
            5. 將資料整理後，使用「AI 分析」功能

            **或者**：您可以在下方「手動輸入」區塊直接貼上競品廣告內容進行分析。
            """)

            # 手動輸入區
            st.markdown("---")
            st.markdown("### ✍️ 手動輸入競品廣告")

            manual_input = st.text_area(
                "貼上競品廣告內容（每行一個，格式：品牌 | 標題 | 內文）",
                height=200,
                placeholder="範例：\n品牌A | 100% 有機茶葉 限時優惠 | 精選台灣高山茶...\n品牌B | 健康好茶 送禮首選 | 來自阿里山的...",
                help="格式：品牌名稱 | 廣告標題 | 廣告內文"
            )

            if manual_input and st.button("🚀 分析手動輸入的廣告", type="primary"):
                # 解析手動輸入
                manual_ads = []
                for line in manual_input.strip().split('\n'):
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 3:
                            manual_ads.append({
                                'page_name': parts[0].strip(),
                                'ad_creative_link_title': parts[1].strip(),
                                'ad_creative_body': parts[2].strip()
                            })

                if manual_ads:
                    st.session_state['competitor_ads'] = manual_ads
                    st.success(f"✅ 已載入 {len(manual_ads)} 個競品廣告")

                    # 顯示競品廣告
                    st.markdown("### 📋 已載入的競品廣告")
                    for i, ad in enumerate(manual_ads, 1):
                        with st.expander(f"廣告 {i} - {ad['page_name']}"):
                            st.markdown(f"**標題**：{ad['ad_creative_link_title']}")
                            st.markdown(f"**內文**：{ad['ad_creative_body']}")
                else:
                    st.error("❌ 無法解析輸入，請確認格式正確")

        else:
            # 有 API Token，使用 API 搜尋
            if search_keywords:
                if st.button("🔍 搜尋競品廣告", type="primary"):
                    with st.spinner("正在搜尋 Meta Ad Library..."):
                        competitor_ads = search_ad_library(search_keywords, api_token, result_limit)

                        if competitor_ads:
                            st.session_state['competitor_ads'] = competitor_ads
                            st.success(f"✅ 找到 {len(competitor_ads)} 個競品廣告")

                            # 顯示搜尋結果
                            st.markdown("### 📊 搜尋結果")

                            for i, ad in enumerate(competitor_ads, 1):
                                with st.expander(f"廣告 {i} - {ad.get('page_name', '未知品牌')}"):
                                    col1, col2 = st.columns([2, 1])

                                    with col1:
                                        st.markdown(f"**品牌**：{ad.get('page_name', '未知')}")
                                        st.markdown(f"**標題**：{ad.get('ad_creative_link_title', '無標題')}")
                                        st.markdown(f"**內文**：{ad.get('ad_creative_body', '無內文')[:200]}...")

                                    with col2:
                                        impressions = ad.get('impressions', {})
                                        if isinstance(impressions, dict):
                                            st.metric("曝光數（估計）", f"{impressions.get('lower_bound', 'N/A'):,}")

                                        start_time = ad.get('ad_delivery_start_time', '')
                                        if start_time:
                                            st.caption(f"開始時間：{start_time}")

                            # 數量比較
                            st.markdown("---")
                            st.markdown("### 📊 廣告數量比較")

                            comparison = compare_ad_performance(our_ads, len(competitor_ads))

                            fig = px.bar(
                                comparison,
                                x='類別',
                                y='數量',
                                title='我們 vs 競品廣告數量',
                                color='類別',
                                color_discrete_map={'我們的廣告': '#3498db', '競品廣告': '#e74c3c'}
                            )
                            fig.update_layout(height=400)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("未找到相關廣告，請嘗試其他關鍵字")
            else:
                st.info("請在側邊欄輸入競品關鍵字後，點擊「搜尋」")

    with tab2:
        st.markdown("## 📊 AI 競品分析")

        if 'competitor_ads' not in st.session_state:
            st.warning("請先在「搜尋競品」標籤中搜尋或輸入競品廣告")
        else:
            competitor_ads = st.session_state['competitor_ads']

            st.info(f"✅ 已載入 {len(competitor_ads)} 個競品廣告，準備進行 AI 分析")

            # 顯示競品廣告摘要
            st.markdown("### 📋 競品廣告摘要")

            competitor_df = pd.DataFrame([
                {
                    '品牌': ad.get('page_name', '未知'),
                    '標題': ad.get('ad_creative_link_title', '')[:50] + '...' if len(ad.get('ad_creative_link_title', '')) > 50 else ad.get('ad_creative_link_title', ''),
                    '內文長度': len(ad.get('ad_creative_body', ''))
                }
                for ad in competitor_ads
            ])

            st.dataframe(competitor_df, use_container_width=True)

            # AI 分析按鈕
            if st.button("🤖 開始 AI 競品分析", type="primary"):
                with st.spinner("AI 正在分析競品廣告與差異化機會..."):
                    analysis = analyze_competitor_ads_with_ai(our_ads, competitor_ads)

                    if analysis and not analysis.startswith("❌"):
                        st.markdown("---")
                        st.markdown("### 🎯 AI 分析結果")
                        st.markdown(analysis)

                        # 儲存分析結果
                        st.session_state['competitor_analysis'] = analysis
                        st.session_state['analysis_time'] = pd.Timestamp.now()
                    else:
                        st.error(analysis if analysis else "AI 分析失敗")

            # 顯示歷史分析
            if 'competitor_analysis' in st.session_state:
                st.markdown("---")
                st.markdown("### 📚 最近的分析結果")

                if 'analysis_time' in st.session_state:
                    st.caption(f"生成時間：{st.session_state['analysis_time'].strftime('%Y-%m-%d %H:%M:%S')}")

                with st.expander("查看完整分析", expanded=False):
                    st.markdown(st.session_state['competitor_analysis'])

    with tab3:
        st.markdown("## 💡 差異化策略執行")

        if 'competitor_analysis' not in st.session_state:
            st.warning("請先在「AI 分析」標籤中生成分析結果")
        else:
            st.success("✅ 已完成競品分析，可以開始執行差異化策略")

            st.markdown("### 📋 執行檢查清單")

            st.markdown("""
            **競品監控（持續進行）**：
            - [ ] 每月搜尋競品新廣告
            - [ ] 記錄競品廣告變化趨勢
            - [ ] 追蹤競品促銷活動
            - [ ] 分析競品受眾策略

            **差異化執行（本週開始）**：
            - [ ] 根據 AI 建議調整廣告文案
            - [ ] 測試差異化標題（A/B 測試）
            - [ ] 強化獨特賣點
            - [ ] 避免使用競品常見套路

            **效果追蹤（2 週後檢視）**：
            - [ ] 比較差異化廣告 vs 原廣告表現
            - [ ] 檢視 CTR 是否提升
            - [ ] 評估 ROAS 變化
            - [ ] 決定是否擴大差異化策略
            """)

            st.markdown("---")

            # 下載分析報告
            st.markdown("### 💾 匯出分析報告")

            if st.session_state.get('competitor_analysis'):
                report_content = f"""# 競品分析報告

**生成時間**：{st.session_state.get('analysis_time', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}
**分析競品數**：{len(st.session_state.get('competitor_ads', []))}

---

{st.session_state['competitor_analysis']}

---

**報告說明**：
- 本報告由 AI 自動生成，基於 Meta Ad Library 數據
- 建議結合實際業務情況進行判斷
- 生成工具：Meta 廣告智能分析儀表板
"""

                st.download_button(
                    label="📥 下載競品分析報告（Markdown）",
                    data=report_content,
                    file_name=f"競品分析報告_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown"
                )

            st.markdown("---")

            # 使用建議
            st.markdown("""
            ### 💡 競品分析最佳實踐

            **定期監控**：
            - 🗓️ **每月一次**：搜尋競品新廣告，追蹤趨勢
            - 📊 **每季分析**：深度分析競品策略變化

            **差異化原則**：
            - ✅ **學習優點**：參考競品成功元素，但要改良
            - ❌ **避免抄襲**：不直接複製競品文案
            - 🎯 **強化特色**：放大自己的獨特優勢

            **執行建議**：
            - 🔴 **高優先級**：立即測試差異化文案
            - 🟡 **中優先級**：調整受眾策略避開競品
            - 🟢 **低優先級**：長期建立品牌差異化
            """)

    # 頁面底部
    st.markdown("---")
    st.markdown("""
    ### 📌 Meta Ad Library 使用須知

    **法規遵循**：
    - Meta Ad Library 是公開透明工具，符合廣告透明度規範
    - 僅用於市場研究，不得用於惡意競爭

    **數據限制**：
    - 曝光數為估計範圍，非精確值
    - 部分廣告可能未顯示完整資訊
    - 搜尋結果受 API 限制影響

    **倫理守則**：
    - 參考競品是為了差異化，不是抄襲
    - 尊重競品智慧財產權
    - 專注於提升自身競爭力
    """)

if __name__ == "__main__":
    main()
