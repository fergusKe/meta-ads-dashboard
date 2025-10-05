import streamlit as st
import pandas as pd
import os
import requests
import json
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image
from utils.data_loader import load_meta_ads_data

st.set_page_config(page_title="AI 圖片生成", page_icon="🎨", layout="wide")

def load_openai_client():
    """載入 OpenAI 客戶端設定"""
    try:
        from openai import OpenAI
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            st.error("❌ 請在 .env 檔案中設定 OPENAI_API_KEY")
            return None
        return OpenAI(api_key=api_key)
    except Exception as e:
        st.error(f"❌ OpenAI 初始化失敗：{str(e)}")
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

def generate_image_prompt(image_type, style_preferences, brand_analysis, user_requirements):
    """生成圖片提示詞"""

    base_context = f"""
品牌：耘初茶食 (台灣茶飲品牌)
產品：高品質茶飲、茶食產品
品牌特色：傳統工藝與現代創新結合，注重健康養生
廣告表現：平均ROAS {brand_analysis.get('avg_roas', 0):.2f}
主要受眾：{', '.join(brand_analysis.get('top_audiences', {}).keys())}

用戶需求：{user_requirements}
"""

    if image_type == "產品展示":
        prompt = f"""
創建一個專業的茶飲產品展示圖片，風格：{style_preferences}

要求：
- 主體：精美的茶飲產品（茶葉、茶具、或包裝茶飲）
- 背景：簡潔優雅，突出產品質感
- 色調：溫暖自然，體現茶文化的寧靜感
- 構圖：產品居中，適合Meta廣告使用
- 解析度：高清晰度，適合社群媒體

{base_context}

創建一個吸引人的茶飲產品圖片，展現品牌的高品質和傳統工藝特色。
"""

    elif image_type == "生活場景":
        prompt = f"""
創建一個溫馨的茶飲生活場景圖片，風格：{style_preferences}

要求：
- 場景：自然舒適的品茶環境（如書房、陽台、咖啡廳）
- 人物：展現享受茶飲時光的愉悅感（可選）
- 氛圍：放鬆、療癒、品味生活
- 元素：茶具、茶葉、自然光線
- 適合：展現品牌生活態度

{base_context}

營造一個讓人嚮往的品茶時光場景，體現耘初茶食帶來的生活美學。
"""

    elif image_type == "品牌識別":
        prompt = f"""
創建品牌識別相關的設計圖片，風格：{style_preferences}

要求：
- 元素：品牌logo、品牌色彩、視覺識別
- 設計：現代簡約，具有識別度
- 應用：適合各種媒體平台使用
- 質感：專業、精緻、具有品牌價值
- 傳達：品牌的專業性和可信度

{base_context}

設計一個具有強烈品牌識別度的圖片，體現耘初茶食的品牌形象。
"""

    elif image_type == "促銷活動":
        prompt = f"""
創建促銷活動廣告圖片，風格：{style_preferences}

要求：
- 主題：限時優惠、新品上市、節慶活動等
- 元素：促銷文字、產品圖片、優惠信息
- 視覺：醒目吸引，具有緊迫感
- 色彩：明亮活潑，刺激購買慾望
- 佈局：信息層次清晰，易於閱讀

{base_context}

創建一個有效的促銷廣告圖片，能夠吸引目標並促進轉換。
"""

    return prompt

def call_dalle_api(prompt, client, size="1024x1024"):
    """呼叫 OpenAI DALL-E 3 API 生成圖片"""
    try:
        # 將尺寸選項映射到 DALL-E 3 支援的尺寸
        size_mapping = {
            "1:1 (1024x1024) - Instagram貼文": "1024x1024",
            "16:9 (1920x1080) - Facebook橫幅": "1792x1024",
            "9:16 (1080x1920) - Stories": "1024x1792"
        }

        dalle_size = size_mapping.get(size, "1024x1024")

        # 呼叫 DALL-E 3 API
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=dalle_size,
            quality="standard",
            n=1,
        )

        # 取得圖片 URL
        image_url = response.data[0].url

        # 下載圖片
        img_response = requests.get(image_url, timeout=30)
        if img_response.status_code == 200:
            return img_response.content
        else:
            st.error(f"❌ 圖片下載失敗：{img_response.status_code}")
            return None

    except Exception as e:
        st.error(f"❌ DALL-E 3 API 呼叫失敗：{str(e)}")
        return None


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

        st.warning("⚠️ Gemini 未回傳圖片內容，將改用 DALL-E 3。")

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
        # DALL-E 3 返回圖片的二進制數據
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

    # 載入數據和 API 客戶端
    df = load_meta_ads_data()
    client = load_openai_client()

    if not client:
        st.stop()

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
    if manual_generate or auto_generate:
        if auto_generate:
            st.info("🎯 正在基於智能推薦的受眾組合生成圖片...")

        with st.spinner("AI 正在創作中，請稍候..."):
            # 準備 requirements_summary
            requirements_summary = f"""
圖片類型：{image_type}
視覺風格：{style_preference}
圖片尺寸：{image_size}
特殊要求：{special_requirements if special_requirements else '無'}
"""

            # 生成提示詞
            prompt = generate_image_prompt(
                image_type,
                style_preference,
                brand_analysis if df is not None else {},
                requirements_summary
            )

            # 呼叫 API
            provider = None
            image_data = call_gemini_image_api(prompt, image_size)
            if image_data:
                provider = "Gemini nano-banana"
            else:
                image_data = call_dalle_api(prompt, client, image_size)
                if image_data:
                    provider = "OpenAI DALL-E 3"

            if image_data:
                if auto_generate:
                    st.success(f"✅ 基於智能推薦的圖片生成完成！（{provider}）")
                else:
                    st.success(f"✅ 圖片生成完成！（{provider}）")

                # 儲存歷史
                save_generation_history(
                    image_type,
                    style_preference,
                    requirements_summary,
                    prompt,
                    True
                )

                # 顯示結果
                display_generated_image(
                    image_data,
                    {"prompt": prompt, "type": image_type, "style": style_preference},
                    provider
                )

            else:
                # 儲存失敗記錄
                save_generation_history(
                    image_type,
                    style_preference,
                    requirements_summary,
                    prompt,
                    False
                )

                # 顯示備選方案
                st.error("❌ 圖片生成失敗")
                st.info("💡 您可以嘗試：\n- 調整需求描述\n- 選擇不同的風格\n- 簡化特殊要求")

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
