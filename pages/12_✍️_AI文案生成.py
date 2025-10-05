import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import json
from utils.data_loader import load_meta_ads_data, calculate_summary_metrics
from utils.rag_service import RAGService

st.set_page_config(page_title="AI 文案生成", page_icon="✍️", layout="wide")

def load_openai_client():
    """載入 OpenAI 客戶端"""
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            st.error("❌ 請在 .env 檔案中設定 OPENAI_API_KEY")
            return None
        return OpenAI(api_key=api_key)
    except Exception as e:
        st.error(f"❌ OpenAI 初始化失敗：{str(e)}")
        return None

def call_openai_api(prompt):
    """呼叫 OpenAI API"""
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            st.error("❌ 請在 .env 檔案中設定 OPENAI_API_KEY")
            return None

        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一位專業的廣告文案撰寫師，專精於Meta廣告文案創作。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.8
        )

        return response.choices[0].message.content

    except Exception as e:
        st.error(f"❌ API 呼叫失敗：{str(e)}")
        return None

def main():
    st.title("✍️ AI 文案生成")
    st.markdown("利用 AI 技術為耘初茶食生成高效廣告文案")

    # 載入數據
    df = load_meta_ads_data()

    # 載入 OpenAI 客戶端
    openai_client = load_openai_client()

    if not openai_client:
        st.stop()

    # ========== 使用 Tab 分頁，所有選項都在主要內容區域 ==========
    tab1, tab2 = st.tabs(["🆕 生成新文案", "🔍 分析現有文案"])

    # ========== Tab 1: 生成新文案 ==========
    with tab1:
        st.subheader("🆕 AI 生成全新廣告文案")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("#### 📝 設定文案參數")

            # 文案類型
            copy_type = st.selectbox(
                "文案類型",
                ["主標題", "內文", "CTA按鈕", "完整廣告"],
                help="選擇您要生成的文案類型"
            )

            # 目標受眾
            target_audience = st.selectbox(
                "目標受眾",
                ["茶飲愛好者", "健康養生族群", "上班族", "年輕消費者", "高端消費者", "自定義"]
            )

            if target_audience == "自定義":
                target_audience = st.text_input("請描述目標受眾", placeholder="例如：25-35歲注重生活品質的女性")

            # 文案風格
            copy_style = st.selectbox(
                "文案風格",
                ["親切溫暖", "專業權威", "年輕活潑", "簡約直接", "情感豐富"]
            )

            # 特殊要求
            special_requirements = st.text_area(
                "特殊要求（選填）",
                placeholder="例如：強調限時優惠、突出新品特色、包含特定關鍵字等",
                height=80
            )

            # RAG 開關
            use_rag = st.checkbox(
                "📚 參考歷史高效案例（建議開啟）",
                value=True,
                help="啟用後將從歷史 ROAS >= 3.0 的高效廣告中學習成功模式"
            )

        with col2:
            st.markdown("#### 📊 參考數據")

            if df is not None:
                avg_roas = df['購買 ROAS（廣告投資報酬率）'].mean()
                avg_ctr = df['CTR（全部）'].mean() * 100
                total_purchases = df['購買次數'].sum()

                st.metric("平均 ROAS", f"{avg_roas:.2f}")
                st.metric("平均點擊率", f"{avg_ctr:.2f}%")
                st.metric("總購買次數", f"{total_purchases:.0f}")

                st.info(f"💡 平均ROAS為 {avg_roas:.2f}，建議文案強調產品價值和轉換效果")
            else:
                st.warning("無法載入數據")

        # 生成按鈕
        st.divider()

        if st.button("🚀 開始生成文案", type="primary", use_container_width=True):
            with st.spinner("AI 正在創作中..."):
                # 構建提示詞
                rag_context = ""
                if use_rag:
                    try:
                        rag = RAGService()
                        if rag.load_knowledge_base("ad_creatives"):
                            query = f"高效{copy_type}，受眾：{target_audience}，風格：{copy_style}"
                            rag_context = rag.get_context_for_generation(query, k=3)
                            st.success("✅ 已載入 3 個歷史高效案例作為參考")
                    except:
                        pass

                prompt = f"""
你是專業的廣告文案撰寫師，為「耘初茶食」（台灣茶飲品牌）撰寫Meta廣告文案。

品牌特色：高品質台灣茶，傳統工藝與現代創新結合，注重健康養生
目標受眾：{target_audience}
文案風格：{copy_style}
特殊要求：{special_requirements if special_requirements else '無'}

{rag_context}

請創作 {copy_type}，以 JSON 格式回傳：
"""

                if copy_type == "主標題":
                    prompt += """
{
  "titles": [
    {"text": "標題內容", "focus": "重點策略"},
    ...（共5個）
  ]
}
"""
                elif copy_type == "內文":
                    prompt += """
{
  "copies": [
    {"text": "內文內容", "strategy": "使用策略"},
    ...（共3個）
  ]
}
"""
                elif copy_type == "CTA按鈕":
                    prompt += """
{
  "ctas": [
    {"text": "按鈕文字", "type": "CTA類型"},
    ...（共10個）
  ]
}
"""
                else:  # 完整廣告
                    prompt += """
{
  "complete_ad": {
    "main_title": "主標題",
    "subtitle": "副標題",
    "body": "內文",
    "cta": "CTA按鈕",
    "strategy_note": "整體策略說明"
  }
}
"""

                # 呼叫 API
                results = call_openai_api(prompt)

                if results:
                    st.success("✅ 文案生成完成！")

                    try:
                        # 解析 JSON
                        if "```json" in results:
                            results = results.split("```json")[1].split("```")[0]
                        elif "```" in results:
                            results = results.split("```")[1].split("```")[0]

                        data = json.loads(results.strip())

                        # 顯示結果
                        st.divider()

                        if copy_type == "主標題" and "titles" in data:
                            st.subheader("🎯 生成的主標題")
                            for i, title in enumerate(data["titles"], 1):
                                st.markdown(f"**{i}. {title['text']}**")
                                st.caption(f"策略：{title.get('focus', '無')}")
                                st.divider()

                        elif copy_type == "內文" and "copies" in data:
                            st.subheader("📝 生成的廣告內文")
                            for i, copy in enumerate(data["copies"], 1):
                                st.markdown(f"**版本 {i}：**")
                                st.write(copy['text'])
                                st.caption(f"策略：{copy.get('strategy', '無')}")
                                st.divider()

                        elif copy_type == "CTA按鈕" and "ctas" in data:
                            st.subheader("🔥 生成的CTA按鈕")
                            cols = st.columns(3)
                            for i, cta in enumerate(data["ctas"]):
                                with cols[i % 3]:
                                    st.info(f"**{cta['text']}**\n\n{cta.get('type', '')}")

                        elif copy_type == "完整廣告" and "complete_ad" in data:
                            st.subheader("🎨 完整廣告文案")
                            ad = data["complete_ad"]

                            st.markdown(f"""
                            <div style="border: 1px solid #ddd; border-radius: 8px; padding: 16px; background: white; margin: 16px 0;">
                                <div style="font-weight: bold; font-size: 18px; margin-bottom: 8px; color: #1c1e21;">
                                    {ad['main_title']}
                                </div>
                                <div style="font-size: 16px; margin-bottom: 8px; color: #65676b;">
                                    {ad.get('subtitle', '')}
                                </div>
                                <div style="font-size: 14px; margin-bottom: 16px; color: #1c1e21; line-height: 1.4;">
                                    {ad['body']}
                                </div>
                                <div style="text-align: center;">
                                    <button style="background: #1877f2; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-weight: bold;">
                                        {ad['cta']}
                                    </button>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            st.info(f"💡 策略：{ad.get('strategy_note', '無')}")

                    except json.JSONDecodeError:
                        st.subheader("📝 生成結果")
                        st.write(results)

    # ========== Tab 2: 分析現有文案 ==========
    with tab2:
        st.subheader("🔍 分析現有文案並獲得優化建議")

        col1, col2 = st.columns([3, 1])

        with col1:
            user_copy = st.text_area(
                "📝 貼上您的廣告文案",
                placeholder="請貼上您想要分析的廣告文案（標題、內文、或完整文案）...",
                height=200,
                help="可以貼上標題、內文、或完整廣告文案"
            )

            if user_copy:
                st.caption(f"字數：{len(user_copy)} 字")

        with col2:
            st.markdown("**分析項目**")
            st.markdown("""
            - ✅ 吸引力評估
            - ✅ 受眾匹配度
            - ✅ 情感訴求
            - ✅ CTA 效果
            - ✅ 優化建議
            - ✅ 生成優化版本
            """)

        st.divider()

        if st.button("🚀 開始分析文案", type="primary", use_container_width=True, disabled=not user_copy):
            with st.spinner("AI 正在分析您的文案..."):
                analysis_prompt = f"""
你是專業的廣告文案分析師，請分析以下廣告文案的優缺點。

品牌：耘初茶食（台灣茶飲品牌）

待分析文案：
{user_copy}

請以 JSON 格式回傳：
{{
    "overall_score": <總分 1-10>,
    "attractiveness": {{"score": <1-10>, "analysis": "分析..."}},
    "audience_match": {{"score": <1-10>, "analysis": "分析...", "target_audience": "適合受眾"}},
    "emotional_appeal": {{"score": <1-10>, "analysis": "分析..."}},
    "cta_effectiveness": {{"score": <1-10>, "analysis": "分析..."}},
    "strengths": ["優點1", "優點2", "優點3"],
    "weaknesses": ["缺點1", "缺點2", "缺點3"],
    "optimization_suggestions": ["建議1", "建議2", "建議3"],
    "optimized_copy": "優化後的文案"
}}
"""

                results = call_openai_api(analysis_prompt)

                if results:
                    try:
                        if "```json" in results:
                            results = results.split("```json")[1].split("```")[0]
                        elif "```" in results:
                            results = results.split("```")[1].split("```")[0]

                        data = json.loads(results.strip())

                        st.success("✅ 分析完成！")

                        # 總分
                        overall_score = data.get('overall_score', 0)
                        percentage = (overall_score / 10) * 100

                        if percentage >= 80:
                            grade = "優秀 🌟"
                            color = "#28a745"
                        elif percentage >= 60:
                            grade = "良好 👍"
                            color = "#ffc107"
                        else:
                            grade = "需改進 ⚠️"
                            color = "#dc3545"

                        col1, col2, col3 = st.columns([2, 1, 1])

                        with col1:
                            st.markdown(f"""
                            <div style="padding: 1.5rem; border-radius: 0.5rem; background: linear-gradient(135deg, {color}22 0%, {color}11 100%); border: 2px solid {color};">
                                <div style="font-size: 0.9rem; color: #666;">文案總分</div>
                                <div style="font-size: 3rem; font-weight: 700; color: {color};">{overall_score}/10</div>
                                <div style="font-size: 1.2rem; font-weight: 600; color: {color};">{grade}</div>
                            </div>
                            """, unsafe_allow_html=True)

                        with col2:
                            st.metric("優點", len(data.get('strengths', [])))

                        with col3:
                            st.metric("待改進", len(data.get('weaknesses', [])))

                        st.divider()

                        # 詳細評分
                        st.subheader("📊 詳細評分")

                        score_items = [
                            ('attractiveness', '吸引力'),
                            ('audience_match', '受眾匹配度'),
                            ('emotional_appeal', '情感訴求'),
                            ('cta_effectiveness', 'CTA 效果')
                        ]

                        col1, col2 = st.columns(2)

                        for i, (key, label) in enumerate(score_items):
                            item = data.get(key, {})
                            score = item.get('score', 0)
                            analysis = item.get('analysis', '無分析')

                            percentage = (score / 10) * 100
                            if percentage >= 80:
                                color = "#28a745"
                            elif percentage >= 60:
                                color = "#ffc107"
                            else:
                                color = "#dc3545"

                            with col1 if i % 2 == 0 else col2:
                                st.markdown(f"""
                                <div style="padding: 1rem; border-radius: 0.5rem; background-color: #f8f9fa; margin-bottom: 1rem;">
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                        <span style="font-weight: 600; color: #1c1e21;">{label}</span>
                                        <span style="font-size: 1.5rem; font-weight: 700; color: {color};">{score}/10</span>
                                    </div>
                                    <div style="width: 100%; background-color: #e9ecef; height: 8px; border-radius: 4px; margin-bottom: 0.75rem;">
                                        <div style="width: {percentage}%; background-color: {color}; height: 100%; border-radius: 4px;"></div>
                                    </div>
                                    <div style="font-size: 0.9rem; color: #495057; line-height: 1.5; padding-top: 0.5rem; border-top: 1px solid #dee2e6;">
                                        {analysis}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                        # 建議受眾
                        if 'audience_match' in data and 'target_audience' in data['audience_match']:
                            st.info(f"🎯 **建議目標受眾**：{data['audience_match']['target_audience']}")

                        st.divider()

                        # 優缺點
                        col1, col2 = st.columns(2)

                        with col1:
                            st.subheader("✅ 優點")
                            for strength in data.get('strengths', []):
                                st.success(f"✓ {strength}")

                        with col2:
                            st.subheader("⚠️ 待改進")
                            for weakness in data.get('weaknesses', []):
                                st.warning(f"• {weakness}")

                        st.divider()

                        # 優化建議
                        st.subheader("💡 優化建議")
                        for i, suggestion in enumerate(data.get('optimization_suggestions', []), 1):
                            st.markdown(f"**{i}.** {suggestion}")

                        st.divider()

                        # 優化版本
                        st.subheader("✨ 優化後的文案")
                        optimized = data.get('optimized_copy', '')
                        if optimized:
                            st.markdown(f"""
                            <div style="padding: 1.5rem; border-radius: 0.5rem; background-color: #e8f5e9; border-left: 4px solid #28a745;">
                                <div style="font-size: 1.1rem; line-height: 1.6; color: #1c1e21;">{optimized}</div>
                            </div>
                            """, unsafe_allow_html=True)

                    except json.JSONDecodeError:
                        st.error("❌ 無法解析分析結果")
                        st.text_area("原始回應", results, height=300)

if __name__ == "__main__":
    main()
