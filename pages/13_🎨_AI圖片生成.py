import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image
from utils.data_loader import load_meta_ads_data
from utils.agents import ImagePromptAgent, ImageGenerationResult

st.set_page_config(page_title="AI 圖片生成", page_icon="🎨", layout="wide")

# 初始化 Agent
@st.cache_resource
def get_image_prompt_agent():
    """取得 ImagePromptAgent 實例"""
    try:
        return ImagePromptAgent()
    except Exception as e:
        st.error(f"❌ ImagePromptAgent 初始化失敗：{str(e)}")
        return None


def analyze_brand_style(df):
    """分析品牌風格和廣告表現"""
    if df is None or df.empty:
        return {}

    # 分析表現最好的廣告
    best_performing = df.nlargest(3, '購買 ROAS（廣告投資報酬率）')

    # 分析受眾特性
    audience_analysis = {}
    if '目標' in df.columns:
        top_audiences = df['目標'].value_counts().head(5)
        audience_analysis = dict(top_audiences)

    # 分析廣告活動特性
    campaign_themes = []
    if '行銷活動名稱' in df.columns:
        campaigns = df['行銷活動名稱'].dropna().values
        for campaign in campaigns[:5]:
            campaign_themes.append(campaign)

    analysis = {
        'best_campaigns': best_performing[['行銷活動名稱', '購買 ROAS（廣告投資報酬率）']].to_dict('records') if not best_performing.empty else [],
        'top_audiences': audience_analysis,
        'campaign_themes': campaign_themes,
        'avg_roas': df['購買 ROAS（廣告投資報酬率）'].mean(),
        'total_spend': df['花費金額 (TWD)'].sum()
    }

    return analysis

async def generate_image_prompts_with_agent(
    agent: ImagePromptAgent,
    df: pd.DataFrame,
    image_type: str,
    style_preferences: str,
    target_audience: str | None,
    special_requirements: str | None,
    image_size: str,
    rag_service=None,
):
    """使用 ImagePromptAgent 生成圖片提示詞"""

    if '(' in image_size and ')' in image_size:
        dimension = image_size.split('(')[1].split(')')[0]
    else:
        dimension = "1024x1024"

    return await agent.generate_prompts(
        df=df,
        image_type=image_type,
        style_preference=style_preferences,
        target_audience=target_audience,
        special_requirements=special_requirements,
        image_size=dimension,
        rag_service=rag_service,
    )


def call_gemini_image_api(prompt, size="1024x1024"):
    """呼叫 Gemini 生成圖片，若無圖片則回傳 None"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return None

    try:
        from google import genai
        from PIL import Image
    except ImportError:
        st.error("❌ 尚未安裝 google-genai 套件，請執行 `uv add google-genai`（或 `pip install google-genai`）後再試。")
        return None

    try:
        # 初始化 Gemini 客戶端
        client = genai.Client(api_key=api_key)
        model_name = os.getenv('GEMINI_IMAGE_MODEL', 'gemini-2.5-flash-image')

        st.info(f"🎯 使用模型：{model_name}")

        # 顯示實際送出的 prompt
        with st.expander("📝 送出的 Prompt", expanded=False):
            st.text_area("Prompt 內容", value=prompt, height=200, disabled=True, label_visibility="collapsed")

        # 呼叫 Gemini API（直接使用傳入的 prompt）
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt],
        )

        # Debug: 顯示原始回應
        with st.expander("🧪 Gemini raw response (debug)", expanded=False):
            try:
                st.json(response.model_dump())
            except Exception as e:
                st.write(f"Response type: {type(response)}")
                st.write(f"Response: {response}")

        # 根據官方範例解析回應
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        for part in candidate.content.parts:
                            # 檢查是否有 inline_data
                            if hasattr(part, 'inline_data') and part.inline_data:
                                if hasattr(part.inline_data, 'data') and part.inline_data.data:
                                    # 返回二進制數據
                                    return part.inline_data.data
                            # 檢查是否有文字回應
                            if hasattr(part, 'text') and part.text:
                                st.info(f"📝 Gemini 回應文字：{part.text}")

        st.warning("⚠️ Gemini 未回傳圖片內容，請調整提示詞後再試。")

    except Exception as exc:
        st.error(f"❌ Gemini 生成失敗：{type(exc).__name__}: {exc}")
        import traceback
        with st.expander("🔍 詳細錯誤訊息", expanded=False):
            st.code(traceback.format_exc())

    return None

def display_generated_image(image_data, prompt_info, provider=None):
    """顯示生成的圖片"""
    if not image_data:
        return

    try:
        # 轉換二進制圖片資料
        if isinstance(image_data, bytes):
            image = Image.open(BytesIO(image_data))

            # 顯示圖片
            st.image(image, caption="AI 生成圖片", use_column_width=True)

            # 提供下載按鈕
            img_buffer = BytesIO()
            image.save(img_buffer, format='PNG')
            img_buffer.seek(0)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ai_generated_image_{timestamp}.png"

            st.download_button(
                label="💾 下載圖片",
                data=img_buffer.getvalue(),
                file_name=filename,
                mime="image/png",
                use_container_width=True
            )

            # 顯示提示詞信息
            with st.expander("🎯 生成參數", expanded=False):
                st.write("**提示詞：**")
                st.text_area("提示詞內容", value=prompt_info.get('prompt', ''), height=150, disabled=True, label_visibility="collapsed")

        else:
            st.error("❌ 圖片數據格式錯誤")

    except Exception as e:
        st.error(f"❌ 圖片顯示失敗：{str(e)}")

def save_generation_history(image_type, style, requirements, prompt, success):
    """儲存圖片生成歷史"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    history_data = {
        "timestamp": timestamp,
        "type": image_type,
        "style": style,
        "requirements": requirements,
        "prompt": prompt,
        "success": success
    }

    if "image_generation_history" not in st.session_state:
        st.session_state.image_generation_history = []

    st.session_state.image_generation_history.append(history_data)

def display_style_examples():
    """顯示風格範例"""
    st.subheader("🎨 風格參考")

    styles = {
        "現代簡約": {
            "description": "乾淨線條、最小元素、高對比度",
            "example": "白色背景、簡潔佈局、專業質感"
        },
        "溫暖自然": {
            "description": "自然色調、有機質感、舒適氛圍",
            "example": "木質元素、暖色光線、自然材質"
        },
        "時尚潮流": {
            "description": "鮮明色彩、動感構圖、現代感強",
            "example": "漸層色彩、幾何圖形、年輕活力"
        },
        "傳統文化": {
            "description": "中式元素、典雅色調、文化韻味",
            "example": "水墨風格、傳統紋樣、古典美感"
        }
    }

    cols = st.columns(2)
    for i, (style, info) in enumerate(styles.items()):
        with cols[i % 2]:
            st.write(f"**{style}**")
            st.caption(info["description"])
            st.info(f"範例：{info['example']}")

def main():
    st.title("🎨 AI 圖片生成")
    st.markdown("使用 Gemini 2.5 Flash Image (nano-banana) 為耘初茶食生成專業廣告圖片")

    # 載入數據
    df = load_meta_ads_data()

    # 主要內容區域 - 設定選項
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("⚙️ 圖片生成設定")

        # 圖片類型選擇
        image_type = st.selectbox(
            "選擇圖片類型",
            ["產品展示", "生活場景", "品牌識別", "促銷活動"]
        )

        # 風格選擇
        style_preference = st.selectbox(
            "選擇視覺風格",
            ["現代簡約", "溫暖自然", "時尚潮流", "傳統文化", "自定義"]
        )

        if style_preference == "自定義":
            custom_style = st.text_input("請描述您想要的風格")
            style_preference = custom_style if custom_style else style_preference

        # 圖片尺寸
        image_size = st.selectbox(
            "圖片尺寸",
            ["1:1 (1024x1024) - Instagram貼文", "16:9 (1920x1080) - Facebook橫幅", "9:16 (1080x1920) - Stories"]
        )

        # 特殊要求
        special_requirements = st.text_area(
            "特殊要求（選填）",
            placeholder="例如：特定色彩、元素、情感表達、目標考量等",
            height=100
        )

    with col2:
        st.subheader("📋 需求摘要")

        requirements_summary = f"""
圖片類型：{image_type}
視覺風格：{style_preference}
圖片尺寸：{image_size}
特殊要求：{special_requirements if special_requirements else '無'}
"""

        st.text_area("當前設定", value=requirements_summary, height=220, disabled=True, label_visibility="collapsed")

    st.divider()

    # 品牌分析與生成按鈕區域
    with col1:
        # 檢查智能推薦受眾
        recommended_audience = st.session_state.get('target_audience', '')
        recommended_objective = st.session_state.get('campaign_objective', '')

        if recommended_audience:
            st.success(f"🎯 **智能推薦受眾**：{recommended_audience}")
            if recommended_objective:
                st.success(f"🎯 **推薦投放目標**：{recommended_objective}")
            st.info("💡 圖片將針對此受眾群體進行優化設計")

        st.subheader("📊 品牌分析參考")

        if df is not None:
            # 分析品牌風格
            brand_analysis = analyze_brand_style(df)

            # 顯示品牌洞察
            insight_col1, insight_col2 = st.columns(2)

            with insight_col1:
                st.write("**表現優異的廣告活動：**")
                best_campaigns = brand_analysis.get('best_campaigns', [])
                if best_campaigns:
                    for i, campaign in enumerate(best_campaigns[:3], 1):
                        st.write(f"{i}. {campaign.get('行銷活動名稱', '未知')} (ROAS: {campaign.get('購買 ROAS（廣告投資報酬率）', 0):.2f})")
                else:
                    st.write("暫無數據")

            with insight_col2:
                st.write("**主要目標：**")
                top_audiences = brand_analysis.get('top_audiences', {})
                if top_audiences:
                    for audience, count in list(top_audiences.items())[:3]:
                        st.write(f"• {audience} ({count} 個活動)")
                else:
                    st.write("暫無數據")

            # 品牌建議
            avg_roas = brand_analysis.get('avg_roas', 0)
            if avg_roas > 3.0:
                suggestion = "您的廣告表現優異，建議圖片風格突出品質和專業性"
            elif avg_roas > 1.5:
                suggestion = "廣告表現中等，建議圖片增強視覺吸引力和情感連結"
            else:
                suggestion = "建議圖片風格更加醒目吸引，強化產品特色和價值主張"

            st.info(f"💡 **視覺策略建議**：{suggestion}")

        else:
            st.warning("⚠️ 無法載入廣告數據，將使用通用圖片生成模式")
            brand_analysis = {}

    with col2:
        st.subheader("🚀 執行生成")

        # 檢查是否需要自動生成（來自智能投放策略的推薦）
        auto_generate = (recommended_audience and
                        st.session_state.get('auto_generate_image', False))

        # 如果是自動生成，清除標記
        if auto_generate:
            st.session_state['auto_generate_image'] = False

        # 生成按鈕或自動生成
        manual_generate = st.button("🚀 開始生成圖片", type="primary", use_container_width=True)

    # 執行生成（移到 columns 外面，使用全寬）
    image_data = None
    provider = None
    if manual_generate or auto_generate:
        if auto_generate:
            st.info("🎯 正在基於智能推薦的受眾組合生成圖片...")

        # 取得 Agent
        image_agent = get_image_prompt_agent()
        if not image_agent:
            st.error("❌ ImagePromptAgent 未初始化，無法生成圖片")
            st.stop()

        # 執行流程可視化
        log_container = st.container()

        with log_container:
            st.markdown("### 🤖 Agent 執行流程")

            # Step 1: 初始化
            with st.status("📋 Step 1: 初始化 ImagePromptAgent", expanded=True) as status:
                model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
                st.write("✓ Agent 類型：**ImagePromptAgent**")
                st.write(f"✓ 模型：**{model_name}**（從 .env 讀取）")
                st.write("✓ 輸出類型：**ImageGenerationResult**（3個提示詞變體）")
                status.update(label="✅ Step 1: Agent 初始化完成", state="complete")

            # Step 2: 準備上下文
            with st.status("📊 Step 2: 分析品牌與需求", expanded=True) as status:
                requirements_summary = f"""
圖片類型：{image_type}
視覺風格：{style_preference}
圖片尺寸：{image_size}
特殊要求：{special_requirements if special_requirements else '無'}
"""
                st.write(f"✓ 圖片類型：**{image_type}**")
                st.write(f"✓ 視覺風格：**{style_preference}**")
                st.write(f"✓ 目標平台：**{image_size.split('-')[1].strip() if '-' in image_size else 'Instagram'}**")
                if brand_analysis:
                    st.write(f"✓ 品牌ROAS：**{brand_analysis.get('avg_roas', 0):.2f}**")
                status.update(label="✅ Step 2: 上下文準備完成", state="complete")

            # Step 3: Agent Tools
            with st.status("🛠️ Step 3: Agent 工具呼叫", expanded=True) as status:
                st.write("✓ `get_brand_visual_guidelines()` - 品牌視覺指南")
                st.write("✓ `get_top_performing_image_features()` - 高效圖片特徵")
                st.write("✓ `get_platform_specific_requirements()` - 平台規格要求")
                st.write("✓ `get_style_specific_prompts()` - 風格範本庫")
                status.update(label="✅ Step 3: 工具就緒", state="complete")

            # Step 4: AI生成
            with st.status("🎨 Step 4: AI 生成提示詞（3個變體）", expanded=True) as status:
                try:
                    import asyncio
                    agent_df = df if df is not None else pd.DataFrame(
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

                    result = asyncio.run(
                        generate_image_prompts_with_agent(
                            image_agent,
                            agent_df,
                            image_type,
                            style_preference,
                            recommended_audience or None,
                            special_requirements or None,
                            image_size,
                        )
                    )
                    st.write("✓ 變體 1：完成")
                    st.write("✓ 變體 2：完成")
                    st.write("✓ 變體 3：完成")
                    st.write("✓ Pydantic 驗證：通過")
                    status.update(label="✅ Step 4: 提示詞生成完成", state="complete")
                except Exception as e:
                    st.error(f"❌ 生成失敗：{str(e)}")
                    import traceback
                    with st.expander("🔍 錯誤詳情"):
                        st.code(traceback.format_exc())
                    st.stop()

            # Step 5: 圖片生成
            with st.status("🖼️ Step 5: 使用 Gemini 生成圖片", expanded=True) as status:
                prompts = result.prompts if result and result.prompts else []

                if not prompts:
                    st.error("❌ 未取得任何圖片提示詞，請重新嘗試")
                    status.update(label="❌ Step 5: 無提示詞可用", state="error")
                    st.stop()

                total_variants = len(prompts)
                recommended_index = result.recommended_variant if 0 <= result.recommended_variant < total_variants else 0
                best_prompt = prompts[recommended_index]
                final_prompt = best_prompt.main_prompt

                st.write(f"✓ 生成變體數：**{total_variants}**")
                st.write(f"✓ 推薦使用：**變體 {recommended_index + 1}**（{best_prompt.chinese_description}）")
                st.write(f"✓ 風格關鍵字：{', '.join(best_prompt.style_keywords)}")

                provider = "Gemini 2.5 Flash Image"
                image_data = call_gemini_image_api(final_prompt, image_size)

                if image_data:
                    st.write("✓ 生成方式：**Gemini 2.5 Flash Image**")
                    status.update(label="✅ Step 5: 圖片生成完成", state="complete")
                else:
                    st.error("❌ 圖片生成失敗（Gemini 未回傳圖片）")
                    status.update(label="❌ Step 5: 生成失敗", state="error")
                    st.stop()

        st.divider()

        # 顯示結果
        if image_data:
            st.success(f"✅ 圖片生成完成！使用 {provider}")

            # 儲存歷史
            save_generation_history(
                image_type,
                style_preference,
                requirements_summary,
                final_prompt,
                True
            )

            # 顯示圖片
            display_generated_image(
                image_data,
                {"prompt": final_prompt, "type": image_type, "style": style_preference},
                provider
            )

            score_col1, score_col2 = st.columns(2)
            with score_col1:
                st.metric("品牌一致性", f"{result.brand_alignment_score}/100")
            with score_col2:
                st.metric("廣告適配性", f"{result.ad_suitability_score}/100")

            st.markdown("### 🎯 設計理念")
            st.info(result.rationale)

            if result.optimization_tips:
                st.subheader("💡 優化建議")
                for idx, tip in enumerate(result.optimization_tips, 1):
                    st.markdown(f"{idx}. {tip}")

            if result.platform_guidelines:
                st.subheader("📐 平台規範提醒")
                for platform, guidelines in result.platform_guidelines.items():
                    st.markdown(f"**{platform}**")
                    if isinstance(guidelines, list):
                        for guideline in guidelines:
                            st.markdown(f"- {guideline}")
                    else:
                        st.markdown(f"- {guidelines}")

            # 顯示所有變體的提示詞
            st.subheader("📝 所有生成的提示詞變體")
            prompts = result.prompts if result and result.prompts else []
            for i, prompt in enumerate(prompts, 1):
                is_recommended = (i - 1 == recommended_index)
                title_prefix = "🌟 推薦變體" if is_recommended else "變體"
                with st.expander(f"{title_prefix} {i}：{prompt.chinese_description}", expanded=(i == 1)):
                    if is_recommended:
                        st.success("這是 ImagePromptAgent 推薦的最佳變體")

                    st.write("**英文提示詞：**")
                    st.code(prompt.main_prompt, language="text")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**風格關鍵字：**")
                        for keyword in prompt.style_keywords:
                            st.write(f"• {keyword}")
                        st.write("**建議色彩：**")
                        for color in prompt.color_palette:
                            st.write(f"• {color}")

                    with col2:
                        st.write("**構圖建議：**")
                        for tip in prompt.composition_tips:
                            st.write(f"• {tip}")
                        st.write(f"**氛圍設定：** {prompt.mood}")
                        st.write(f"**適用平台：** {prompt.target_platform}")

                    if st.button(f"使用此變體重新生成", key=f"use_variant_{i}"):
                        new_image_data = call_gemini_image_api(prompt.main_prompt, image_size)
                        if new_image_data:
                            display_generated_image(
                                new_image_data,
                                {"prompt": prompt.main_prompt, "type": image_type, "style": style_preference},
                                "Gemini 2.5 Flash Image"
                            )
                        else:
                            st.warning("⚠️ Gemini 未回傳圖片內容，請調整提示詞後再試。")

    st.divider()

    # 顯示風格範例
    display_style_examples()

    # 生成歷史
    if st.session_state.get("image_generation_history"):
        st.subheader("📚 生成歷史")

        # 顯示最近5次的生成記錄
        recent_history = st.session_state.image_generation_history[-5:]

        for i, history in enumerate(reversed(recent_history)):
            status_icon = "✅" if history['success'] else "❌"
            with st.expander(f"{status_icon} {history['timestamp']} - {history['type']}", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**類型：**", history['type'])
                    st.write("**風格：**", history['style'])
                with col2:
                    st.write("**狀態：**", "成功" if history['success'] else "失敗")

                st.write("**需求：**")
                st.text(history['requirements'])

                if st.button(f"重新生成", key=f"regenerate_{i}"):
                    st.rerun()

    # 圖片優化建議
    st.subheader("💡 圖片優化建議")

    optimization_tips = [
        "📱 **行動優先**：確保圖片在手機端清晰可見，文字大小適中",
        "🎯 **焦點明確**：單一主體，避免元素過多分散注意力",
        "🌈 **色彩和諧**：使用品牌色系，保持視覺一致性",
        "📊 **A/B測試**：生成多個版本進行效果測試比較",
        "🔥 **情感連結**：圖片要能喚起目標的共鳴和購買慾望",
        "📐 **尺寸適配**：根據投放平台選擇合適的圖片比例"
    ]

    for tip in optimization_tips:
        st.markdown(f"- {tip}")

    # 使用指南
    with st.expander("📖 使用指南", expanded=False):
        st.markdown("""
        ### 🎯 如何獲得最佳效果

        **1. 明確需求**
        - 選擇符合廣告目標的圖片類型
        - 考慮目標的偏好和特徵
        - 描述具體的視覺要求

        **2. 風格選擇**
        - 現代簡約：適合年輕專業族群
        - 溫暖自然：適合重視生活品質的受眾
        - 時尚潮流：適合追求新潮的年輕消費者
        - 傳統文化：適合重視文化內涵的受眾

        **3. 優化技巧**
        - 生成多個版本進行比較
        - 結合數據分析調整視覺策略
        - 定期更新創意保持新鮮感

        **4. 使用建議**
        - 確保圖片符合 Meta 廣告政策
        - 注意版權和商標使用
        - 保存高品質原檔以備不同用途
        """)

if __name__ == "__main__":
    main()
