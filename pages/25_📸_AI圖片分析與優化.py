import streamlit as st
import pandas as pd
import os
from datetime import datetime
from io import BytesIO
from PIL import Image
from utils.data_loader import load_meta_ads_data
from utils.agents import ImageAnalysisAgent, ImageAnalysisResult

st.set_page_config(page_title="AI 圖片分析與優化", page_icon="📸", layout="wide")

# 初始化 Agent
@st.cache_resource
def get_image_analysis_agent():
    """取得 ImageAnalysisAgent 實例"""
    try:
        return ImageAnalysisAgent()
    except Exception as e:
        st.error(f"❌ ImageAnalysisAgent 初始化失敗：{str(e)}")
        return None


def call_gemini_image_api(prompt, size="1024x1024"):
    """呼叫 Gemini 生成圖片，若無圖片則回傳 None"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return None

    try:
        from google import genai
    except ImportError:
        st.error("❌ 尚未安裝 google-genai 套件，請執行 `uv add google-genai`（或 `pip install google-genai`）後再試。")
        return None

    try:
        client = genai.Client(api_key=api_key)
        model_name = os.getenv('GEMINI_IMAGE_MODEL', 'gemini-2.5-flash-image')
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt],
        )

        with st.expander("🧪 Gemini raw response (debug)", expanded=False):
            try:
                st.json(response.model_dump())
            except Exception:
                st.write(response)

        for candidate in getattr(response, 'candidates', []):
            content = getattr(candidate, 'content', None)
            if not content:
                continue
            for part in getattr(content, 'parts', []):
                inline_data = getattr(part, 'inline_data', None)
                if inline_data and getattr(inline_data, 'data', None):
                    return inline_data.data

        return None
    except Exception as exc:
        st.error(f"❌ Gemini 生成失敗：{exc}")
        return None
def get_openai_client():
    """依據環境變數初始化 OpenAI 客戶端"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        st.error("❌ 請設定 OPENAI_API_KEY 才能進行圖片分析")
        return None

    try:
        from openai import OpenAI
    except ImportError:
        st.error("❌ 尚未安裝 openai 套件，請執行 `uv add openai`（或 `pip install openai`）後再試。")
        return None

    try:
        return OpenAI(api_key=api_key)
    except Exception as exc:
        st.error(f"❌ 無法初始化 OpenAI 客戶端：{exc}")
        return None



def generate_optimized_image(original_analysis, image_size="1024x1024"):
    """基於分析結果生成優化後的圖片（使用 Gemini）"""
    if isinstance(original_analysis, ImageAnalysisResult):
        weaknesses = original_analysis.weaknesses
        suggestions = original_analysis.optimization_suggestions
    else:
        weaknesses = original_analysis.get('weaknesses', [])
        suggestions = original_analysis.get('optimization_suggestions', [])

    optimization_prompt = f"""
創建一張優化的廣告圖片，改善以下問題：

需要改善的問題：
{chr(10).join([f"- {w}" for w in weaknesses])}

優化建議：
{chr(10).join([f"- {s}" for s in suggestions])}

品牌：耘初茶食（台灣茶飲品牌）
產品：高品質茶飲、茶食產品
品牌特色：傳統工藝與現代創新結合，注重健康養生

請創建一張專業的廣告圖片，確保：
1. 視覺吸引力強，能在動態消息中脫穎而出
2. 構圖清晰，主體明確，視覺層次分明
3. 色彩和諧，符合品牌調性
4. 文字清晰可讀（如有文字）
5. 符合品牌形象，具有識別度
6. 適合 Meta 廣告投放，具有轉換潛力

風格要求：現代簡約、溫暖自然、專業質感
解析度：高清晰度，適合社群媒體使用
"""

    image_data = call_gemini_image_api(optimization_prompt, image_size)
    if image_data:
        st.info("🎨 使用 Gemini 2.5 Flash Image 生成優化結果")
        return image_data, optimization_prompt

    st.error("❌ Gemini 未回傳圖片內容，請調整分析結果或稍後再試。")
    return None, None


def display_score_card(title, score, max_score=10):
    """顯示評分卡片"""
    percentage = (score / max_score) * 100

    # 根據分數設定顏色
    if percentage >= 80:
        color = "#28a745"  # 綠色
        emoji = "🟢"
    elif percentage >= 60:
        color = "#ffc107"  # 黃色
        emoji = "🟡"
    else:
        color = "#dc3545"  # 紅色
        emoji = "🔴"

    st.markdown(f"""
    <div style="padding: 1rem; border-radius: 0.5rem; background-color: #f8f9fa; margin-bottom: 0.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 600; color: #1c1e21;">{emoji} {title}</span>
            <span style="font-size: 1.5rem; font-weight: 700; color: {color};">{score}/{max_score}</span>
        </div>
        <div style="width: 100%; background-color: #e9ecef; height: 8px; border-radius: 4px; margin-top: 0.5rem;">
            <div style="width: {percentage}%; background-color: {color}; height: 100%; border-radius: 4px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def get_brand_context(df):
    """從數據中獲取品牌背景資訊"""
    if df is None or df.empty:
        return "耘初茶食 - 台灣茶飲品牌，注重品質與傳統工藝"

    # 分析表現最好的廣告
    best_performing = df.nlargest(3, '購買 ROAS（廣告投資報酬率）')

    context = f"""
耘初茶食 - 台灣茶飲品牌

品牌特色：傳統工藝與現代創新結合，注重健康養生

高效廣告特徵：
- 平均 ROAS：{df['購買 ROAS（廣告投資報酬率）'].mean():.2f}
- 表現最佳的廣告活動：{', '.join(best_performing['行銷活動名稱'].dropna().values[:3])}
"""

    if '目標' in df.columns:
        top_audiences = df['目標'].value_counts().head(3)
        context += f"\n- 主要目標受眾：{', '.join(top_audiences.index.tolist())}"

    return context

def main():
    st.title("📸 AI 圖片分析與優化")
    st.markdown("使用 GPT-4o Vision 分析圖片，並透過 Gemini 2.5 Flash Image (nano-banana) 生成優化圖片")

    # 載入數據和 API 客戶端
    df = load_meta_ads_data()
    # 取得品牌背景
    brand_context = get_brand_context(df)

    # 主要內容 - 上傳區域
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📤 上傳廣告圖片")
        uploaded_file = st.file_uploader(
            "選擇圖片檔案",
            type=['jpg', 'jpeg', 'png', 'webp'],
            help="請上傳您想要分析的廣告圖片",
            label_visibility="collapsed"
        )

    with col2:
        st.subheader("📋 使用說明")
        st.info("""
**支援格式**：JPG, PNG, WEBP
**建議尺寸**：1080x1080 以上

**分析內容**：
- 6 大維度專業評分
- 詳細優缺點分析
- 投放適配性評估
- 一鍵優化建議
        """)

    st.divider()

    if uploaded_file is not None:
        image_bytes = uploaded_file.getvalue()
        image = Image.open(BytesIO(image_bytes))
        image.load()
        image_key = f"{getattr(uploaded_file, 'name', 'uploaded')}-{len(image_bytes)}"

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📷 原始圖片")
            st.image(image, use_container_width=True)

            # 圖片資訊
            st.caption(f"尺寸：{image.size[0]} x {image.size[1]} px")
            st.caption(f"格式：{image.format}")

        with col2:
            st.subheader("🔍 執行分析")

            st.write("**AI 分析功能**")
            st.write("使用 GPT-4o Vision 分析圖片的 6 大維度：")
            st.write("• 視覺吸引力")
            st.write("• 構圖設計")
            st.write("• 色彩運用")
            st.write("• 文字可讀性")
            st.write("• 品牌一致性")
            st.write("• 投放適配性")

            st.write("")

            # 分析按鈕
            if st.button("🚀 開始分析圖片", type="primary", use_container_width=True):
                with st.spinner("AI 正在分析圖片，請稍候..."):
                    analysis_agent = get_image_analysis_agent()
                    if not analysis_agent:
                        st.stop()

                    openai_client = get_openai_client()
                    if not openai_client:
                        st.stop()

                    analysis_df = df if df is not None else pd.DataFrame(
                        columns=[
                            '購買 ROAS（廣告投資報酬率）',
                            'CTR（全部）',
                            '每次購買的成本',
                            '花費金額 (TWD)',
                            '購買次數',
                            '觸及人數',
                            '行銷活動名稱',
                            '目標',
                            '年齡',
                            '性別'
                        ]
                    )

                    try:
                        analysis_result = analysis_agent.analyze_image_sync(
                            image=image,
                            df=analysis_df,
                            brand_context=brand_context,
                            openai_client=openai_client
                        )
                    except Exception as exc:
                        st.error(f"❌ 圖片分析失敗：{exc}")
                        import traceback
                        with st.expander("🔍 錯誤詳情"):
                            st.code(traceback.format_exc())
                        st.stop()

                    # 儲存分析結果到 session state
                    st.session_state['image_analysis'] = analysis_result
                    st.session_state['analyzed_image_key'] = image_key
                    st.success("✅ 分析完成！")
                    st.rerun()

        # 顯示分析結果
        if 'image_analysis' in st.session_state and st.session_state.get('analyzed_image_key') == image_key:
            analysis_result: ImageAnalysisResult = st.session_state['image_analysis']
            analysis_dict = analysis_result.model_dump()
            scores = analysis_dict.get('scores', {})
            detailed_analysis = analysis_dict.get('detailed_analysis', {})
            strengths = analysis_result.strengths
            weaknesses = analysis_result.weaknesses

            st.divider()

            # 總體評分
            st.subheader("📊 總體評分")
            overall_score = analysis_result.overall_score

            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                # 總分進度條
                percentage = (overall_score / 10) * 100
                if percentage >= 80:
                    color = "#28a745"
                    grade = "優秀 🌟"
                elif percentage >= 60:
                    color = "#ffc107"
                    grade = "良好 👍"
                else:
                    color = "#dc3545"
                    grade = "需改進 ⚠️"

                st.markdown(f"""
                <div style="padding: 1.5rem; border-radius: 0.5rem; background: linear-gradient(135deg, {color}22 0%, {color}11 100%); border: 2px solid {color};">
                    <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.5rem;">總體評分</div>
                    <div style="font-size: 3rem; font-weight: 700; color: {color};">{overall_score:.1f}/10</div>
                    <div style="font-size: 1.2rem; font-weight: 600; color: {color}; margin-top: 0.5rem;">{grade}</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                is_suitable = analysis_result.is_suitable_for_ads
                st.metric(
                    "投放適配性",
                    "✅ 適合" if is_suitable else "⚠️ 不建議"
                )

            with col3:
                strengths_count = len(strengths)
                weaknesses_count = len(weaknesses)
                st.metric("優點", strengths_count, delta=f"-{weaknesses_count} 缺點", delta_color="inverse")

            # 適配性說明
            st.info(f"💡 {analysis_result.suitability_reason or '無說明'}")

            st.divider()

            # 詳細評分
            st.subheader("📈 詳細評分")

            score_labels = {
                'visual_appeal': '視覺吸引力',
                'composition': '構圖設計',
                'color_usage': '色彩運用',
                'text_readability': '文字可讀性',
                'brand_consistency': '品牌一致性',
                'ad_suitability': '投放適配性'
            }

            col1, col2 = st.columns(2)

            for i, (key, label) in enumerate(score_labels.items()):
                with col1 if i % 2 == 0 else col2:
                    score = scores.get(key, 0)
                    analysis_text = detailed_analysis.get(key, '無詳細分析')

                    # 計算分數和顏色
                    percentage = (score / 10) * 100
                    if percentage >= 80:
                        color = "#28a745"
                        emoji = "🟢"
                    elif percentage >= 60:
                        color = "#ffc107"
                        emoji = "🟡"
                    else:
                        color = "#dc3545"
                        emoji = "🔴"

                    # 合併評分和詳細分析為單一卡片
                    st.markdown(f"""
                    <div style="padding: 1rem; border-radius: 0.5rem; background-color: #f8f9fa; margin-bottom: 1rem; border: 1px solid #dee2e6;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                            <span style="font-weight: 600; color: #1c1e21; font-size: 1rem;">{emoji} {label}</span>
                            <span style="font-size: 1.5rem; font-weight: 700; color: {color};">{score}/10</span>
                        </div>
                        <div style="width: 100%; background-color: #e9ecef; height: 8px; border-radius: 4px; margin-bottom: 0.75rem;">
                            <div style="width: {percentage}%; background-color: {color}; height: 100%; border-radius: 4px;"></div>
                        </div>
                        <div style="font-size: 0.9rem; color: #495057; line-height: 1.6; padding-top: 0.5rem; border-top: 1px solid #dee2e6;">
                            {analysis_text}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            st.divider()

            # 優缺點分析
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("✅ 優點")
                if strengths:
                    for strength in strengths:
                        st.success(f"✓ {strength}")
                else:
                    st.info("無明顯優點")

            with col2:
                st.subheader("⚠️ 缺點")
                if weaknesses:
                    for weakness in weaknesses:
                        st.warning(f"• {weakness}")
                else:
                    st.success("無明顯缺點")

            st.divider()

            # 優化建議
            st.subheader("💡 優化建議")
            suggestions = analysis_result.optimization_suggestions

            if suggestions:
                for i, suggestion in enumerate(suggestions, 1):
                    st.markdown(f"**{i}.** {suggestion}")
            else:
                st.info("無需優化")

            # 目標受眾建議
            if analysis_result.target_audience_recommendation:
                st.info(f"🎯 **建議目標受眾**：{analysis_result.target_audience_recommendation}")

            if analysis_result.optimization_prompt:
                with st.expander("🪄 AI 建議的優化提示詞", expanded=False):
                    st.text_area(
                        "優化提示詞",
                        analysis_result.optimization_prompt,
                        height=200,
                        disabled=True,
                        label_visibility="collapsed"
                    )

            st.divider()

            # 一鍵優化功能
            st.subheader("🎨 一鍵生成優化圖片")

            st.write("基於 AI 分析結果，自動生成優化後的廣告圖片")

            # 圖片尺寸選擇
            image_size_option = st.selectbox(
                "選擇圖片尺寸",
                ["1024x1024", "1792x1024", "1024x1792"]
            )

            if st.button("🚀 生成優化圖片", type="primary", use_container_width=True):
                with st.spinner("AI 正在生成優化圖片，請稍候（約 10-30 秒）..."):
                    optimized_image_data, optimization_prompt = generate_optimized_image(
                        analysis_result,
                        image_size_option
                    )

                    if optimized_image_data:
                        st.success("✅ 優化圖片生成完成！")

                        # 顯示優化後的圖片
                        optimized_image = Image.open(BytesIO(optimized_image_data))

                        col1, col2 = st.columns(2)

                        with col1:
                            st.write("**原始圖片**")
                            st.image(image, use_container_width=True)

                        with col2:
                            st.write("**優化圖片**")
                            st.image(optimized_image, use_container_width=True)

                        # 下載按鈕
                        img_buffer = BytesIO()
                        optimized_image.save(img_buffer, format='PNG')
                        img_buffer.seek(0)

                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"optimized_ad_image_{timestamp}.png"

                        st.download_button(
                            label="💾 下載優化圖片",
                            data=img_buffer.getvalue(),
                            file_name=filename,
                            mime="image/png",
                            use_container_width=True
                        )

                        # 顯示優化提示詞
                        with st.expander("🎯 查看優化提示詞"):
                            st.text_area("優化提示詞", optimization_prompt, height=200, disabled=True, label_visibility="collapsed")

    else:
        # 顯示範例和說明
        st.info("👆 請上傳圖片開始分析")

        st.subheader("🎯 為什麼要分析圖片？")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            ### 📊 數據驅動

            透過 AI 分析，了解圖片的：
            - 視覺吸引力
            - 構圖優劣
            - 色彩搭配
            - 文字可讀性
            """)

        with col2:
            st.markdown("""
            ### 🎯 精準優化

            獲得具體建議：
            - 明確的改善方向
            - 專業的優化建議
            - 目標受眾匹配
            - 投放適配性評估
            """)

        with col3:
            st.markdown("""
            ### 🚀 效率提升

            一鍵生成優化圖：
            - 自動套用建議
            - 快速產出優化版本
            - 節省設計時間
            - 提高廣告效果
            """)

        st.divider()

        st.subheader("💡 使用技巧")

        tips = [
            "📱 **確保圖片清晰**：上傳高解析度圖片（建議 1080x1080 以上）",
            "🎯 **明確投放目標**：分析時會考慮圖片是否符合廣告目標",
            "🔄 **多次測試**：可以上傳多張圖片進行比較分析",
            "📊 **結合數據**：將分析結果與實際廣告數據對照",
            "🎨 **善用優化功能**：根據建議生成優化圖片，進行 A/B 測試"
        ]

        for tip in tips:
            st.markdown(f"- {tip}")

if __name__ == "__main__":
    main()
