import streamlit as st
import pandas as pd
import openai
import os
from datetime import datetime
import json
from utils.data_loader import load_meta_ads_data, calculate_summary_metrics

st.set_page_config(page_title="AI 文案生成", page_icon="✍️", layout="wide")

def load_openai_client():
    """載入 OpenAI 客戶端"""
    try:
        openai.api_key = os.getenv('OPENAI_API_KEY')
        if not openai.api_key:
            st.error("❌ 請在 .env 檔案中設定 OPENAI_API_KEY")
            return None
        return openai
    except Exception as e:
        st.error(f"❌ OpenAI 初始化失敗：{str(e)}")
        return None

def analyze_campaign_performance(df):
    """分析活動表現以提供文案建議"""
    if df is None or df.empty:
        return {}

    # 找出表現最好的活動
    best_campaign = df.loc[df['購買 ROAS（廣告投資報酬率）'].idxmax()]

    # 計算平均指標
    avg_roas = df['購買 ROAS（廣告投資報酬率）'].mean()
    avg_ctr = df['CTR（全部）'].mean()
    avg_cpa = df['每次購買的成本'].mean()

    # 主要產品/目標分析
    top_audiences = df['目標'].value_counts().head(3) if '目標' in df.columns else {}

    analysis = {
        'best_campaign_name': best_campaign.get('行銷活動名稱', '未知'),
        'best_roas': best_campaign.get('購買 ROAS（廣告投資報酬率）', 0),
        'avg_roas': avg_roas,
        'avg_ctr': avg_ctr * 100,  # 轉換為百分比
        'avg_cpa': avg_cpa,
        'top_audiences': dict(top_audiences),
        'total_spend': df['花費金額 (TWD)'].sum(),
        'total_purchases': df['購買次數'].sum()
    }

    return analysis

def generate_copywriting_prompt(copy_type, brand_info, performance_data, user_requirements):
    """生成文案提示詞"""

    base_prompt = f"""
你是一位專業的廣告文案撰寫師，專門為茶飲品牌「耘初茶食」撰寫Meta廣告文案。

品牌資訊：
- 品牌名稱：耘初茶食
- 產品類型：茶飲、茶食
- 品牌特色：{brand_info.get('特色', '高品質茶飲，傳統工藝與現代創新結合')}

廣告表現數據參考：
- 平均ROAS：{performance_data.get('avg_roas', 0):.2f}
- 平均點擊率：{performance_data.get('avg_ctr', 0):.2f}%
- 平均購買成本：NT$ {performance_data.get('avg_cpa', 0):.0f}
- 最佳表現活動：{performance_data.get('best_campaign_name', '未知')}

用戶需求：{user_requirements}
"""

    if copy_type == "主標題":
        prompt = base_prompt + """
請創作5個吸引人的Meta廣告主標題（限25字以內），要求：
1. 突出產品特色和價值主張
2. 使用情感化語言激發購買慾望
3. 包含行動呼籲元素
4. 考慮目標心理
5. 符合Meta廣告規範

請以JSON格式回傳：
{
  "titles": [
    {"text": "標題內容", "focus": "重點策略", "target": "目標"},
    ...
  ]
}
"""

    elif copy_type == "內文":
        prompt = base_prompt + """
請創作3段Meta廣告內文（每段限125字以內），要求：
1. 開頭吸引注意力
2. 中段說明產品優勢和價值
3. 結尾強化行動呼籲
4. 語調親切自然，貼近台灣消費者
5. 適當運用社會證明和稀缺性

請以JSON格式回傳：
{
  "copies": [
    {"text": "內文內容", "strategy": "使用策略", "cta": "行動呼籲"},
    ...
  ]
}
"""

    elif copy_type == "CTA按鈕":
        prompt = base_prompt + """
請創作10個有效的CTA按鈕文字（限15字以內），要求：
1. 明確的行動指示
2. 創造急迫感
3. 降低購買阻力
4. 適合茶飲產品特性
5. 提高轉換率

請以JSON格式回傳：
{
  "ctas": [
    {"text": "按鈕文字", "type": "CTA類型", "urgency": "急迫感等級"},
    ...
  ]
}
"""

    elif copy_type == "完整廣告":
        prompt = base_prompt + """
請創作1個完整的Meta廣告文案組合，包含：
1. 主標題（25字以內）
2. 副標題（40字以內）
3. 內文（125字以內）
4. CTA按鈕（15字以內）

要求整體一致性和轉換導向，請以JSON格式回傳：
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

    return prompt

def call_openai_api(prompt):
    """呼叫 OpenAI API"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # 使用可用的模型
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

def display_copywriting_results(results, copy_type):
    """顯示文案生成結果"""
    if not results:
        return

    try:
        # 嘗試解析 JSON 格式回應
        data = json.loads(results)

        if copy_type == "主標題" and "titles" in data:
            st.subheader("🎯 生成的主標題")
            for i, title in enumerate(data["titles"], 1):
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{i}. {title['text']}**")
                        st.caption(f"策略重點：{title['focus']} | 目標：{title['target']}")
                    with col2:
                        if st.button(f"複製", key=f"copy_title_{i}"):
                            st.success("已複製到剪貼板！")
                    st.divider()

        elif copy_type == "內文" and "copies" in data:
            st.subheader("📝 生成的廣告內文")
            for i, copy in enumerate(data["copies"], 1):
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**版本 {i}：**")
                        st.write(copy['text'])
                        st.caption(f"策略：{copy['strategy']} | CTA：{copy['cta']}")
                    with col2:
                        if st.button(f"複製", key=f"copy_body_{i}"):
                            st.success("已複製到剪貼板！")
                    st.divider()

        elif copy_type == "CTA按鈕" and "ctas" in data:
            st.subheader("🔥 生成的CTA按鈕")
            cols = st.columns(3)
            for i, cta in enumerate(data["ctas"]):
                col_idx = i % 3
                with cols[col_idx]:
                    st.write(f"**{cta['text']}**")
                    st.caption(f"{cta['type']}")
                    st.caption(f"急迫感：{cta['urgency']}")
                    if st.button(f"複製", key=f"copy_cta_{i}"):
                        st.success("已複製！")
                    st.write("")

        elif copy_type == "完整廣告" and "complete_ad" in data:
            st.subheader("🎨 完整廣告文案")
            ad = data["complete_ad"]

            # 廣告預覽
            with st.container():
                st.markdown("### 📱 廣告預覽")

                # 模擬 Meta 廣告格式
                st.markdown(f"""
                <div style="border: 1px solid #ddd; border-radius: 8px; padding: 16px; background: white; margin: 16px 0;">
                    <div style="font-weight: bold; font-size: 18px; margin-bottom: 8px; color: #1c1e21;">
                        {ad['main_title']}
                    </div>
                    <div style="font-size: 16px; margin-bottom: 8px; color: #65676b;">
                        {ad['subtitle']}
                    </div>
                    <div style="font-size: 14px; margin-bottom: 16px; color: #1c1e21; line-height: 1.4;">
                        {ad['body']}
                    </div>
                    <div style="text-align: center;">
                        <button style="background: #1877f2; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-weight: bold; cursor: pointer;">
                            {ad['cta']}
                        </button>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.info(f"💡 策略說明：{ad['strategy_note']}")

                # 複製按鈕
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("複製主標題"):
                        st.success("主標題已複製！")
                with col2:
                    if st.button("複製副標題"):
                        st.success("副標題已複製！")
                with col3:
                    if st.button("複製內文"):
                        st.success("內文已複製！")
                with col4:
                    if st.button("複製CTA"):
                        st.success("CTA已複製！")

    except json.JSONDecodeError:
        # 如果不是 JSON 格式，直接顯示文字
        st.subheader("📝 生成結果")
        st.write(results)
        if st.button("複製全部內容"):
            st.success("內容已複製到剪貼板！")

def save_copywriting_history(copy_type, requirements, results):
    """儲存文案生成歷史"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    history_data = {
        "timestamp": timestamp,
        "type": copy_type,
        "requirements": requirements,
        "results": results
    }

    # 儲存到 session state
    if "copywriting_history" not in st.session_state:
        st.session_state.copywriting_history = []

    st.session_state.copywriting_history.append(history_data)

def main():
    st.title("✍️ AI 文案生成")
    st.markdown("利用 AI 技術為耘初茶食生成高效廣告文案")

    # 載入數據
    df = load_meta_ads_data()

    # 載入 OpenAI 客戶端
    openai_client = load_openai_client()

    if not openai_client:
        st.stop()

    # 側邊欄設定
    st.sidebar.header("🎯 文案生成設定")

    # 文案類型選擇
    copy_type = st.sidebar.selectbox(
        "選擇文案類型",
        ["主標題", "內文", "CTA按鈕", "完整廣告"]
    )

    # 品牌資訊設定
    st.sidebar.subheader("🏷️ 品牌資訊")
    brand_features = st.sidebar.text_area(
        "品牌特色描述",
        value="高品質台灣茶，傳統工藝與現代創新結合，注重健康養生",
        height=100
    )

    # 目標
    target_audience = st.sidebar.selectbox(
        "主要目標",
        ["茶飲愛好者", "健康養生族群", "上班族", "年輕消費者", "高端消費者", "自定義"]
    )

    if target_audience == "自定義":
        custom_audience = st.sidebar.text_input("請描述目標")
        target_audience = custom_audience

    # 文案風格
    copy_style = st.sidebar.selectbox(
        "文案風格",
        ["親切溫暖", "專業權威", "年輕活潑", "簡約直接", "情感豐富"]
    )

    # 特殊要求
    special_requirements = st.sidebar.text_area(
        "特殊要求（選填）",
        placeholder="例如：強調限時優惠、突出新品特色、包含特定關鍵字等",
        height=80
    )

    # 主要內容區域
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📊 當前廣告表現分析")

        if df is not None:
            # 分析廣告表現
            performance_data = analyze_campaign_performance(df)

            # 顯示關鍵指標
            metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

            with metrics_col1:
                st.metric(
                    "平均 ROAS",
                    f"{performance_data.get('avg_roas', 0):.2f}",
                    delta=f"最佳: {performance_data.get('best_roas', 0):.2f}"
                )

            with metrics_col2:
                st.metric(
                    "平均點擊率",
                    f"{performance_data.get('avg_ctr', 0):.2f}%"
                )

            with metrics_col3:
                st.metric(
                    "平均 CPA",
                    f"NT$ {performance_data.get('avg_cpa', 0):.0f}"
                )

            with metrics_col4:
                st.metric(
                    "總購買次數",
                    f"{performance_data.get('total_purchases', 0):.0f}"
                )

            # 顯示表現洞察
            st.info(f"💡 **文案建議方向**：根據您的廣告數據，平均ROAS為 {performance_data.get('avg_roas', 0):.2f}，建議文案可以強調產品價值和轉換效果。")

        else:
            st.warning("⚠️ 無法載入廣告數據，將使用通用文案生成模式")
            performance_data = {}

    with col2:
        st.subheader("🎯 文案生成需求")

        # 用戶需求摘要
        user_requirements = f"""
        目標：{target_audience}
        文案風格：{copy_style}
        特殊要求：{special_requirements if special_requirements else '無'}
        """

        st.text_area("需求摘要", value=user_requirements, height=150, disabled=True)

        # 生成按鈕
        if st.button("🚀 開始生成文案", type="primary", use_container_width=True):
            with st.spinner("AI 正在創作中..."):
                # 準備品牌資訊
                brand_info = {"特色": brand_features}

                # 生成提示詞
                prompt = generate_copywriting_prompt(
                    copy_type,
                    brand_info,
                    performance_data if df is not None else {},
                    user_requirements
                )

                # 呼叫 API
                results = call_openai_api(prompt)

                if results:
                    # 儲存歷史
                    save_copywriting_history(copy_type, user_requirements, results)

                    # 顯示結果
                    st.success("✅ 文案生成完成！")
                    display_copywriting_results(results, copy_type)
                else:
                    st.error("❌ 文案生成失敗，請稍後再試")

    # 文案生成歷史
    if st.session_state.get("copywriting_history"):
        st.subheader("📚 文案生成歷史")

        # 顯示最近5次的生成記錄
        recent_history = st.session_state.copywriting_history[-5:]

        for i, history in enumerate(reversed(recent_history)):
            with st.expander(f"{history['timestamp']} - {history['type']}", expanded=False):
                st.write("**需求：**")
                st.text(history['requirements'])
                st.write("**生成結果：**")
                st.text(history['results'])

    # 文案優化建議
    st.subheader("💡 文案優化建議")

    optimization_tips = [
        "📈 **數據驅動**：根據現有廣告的 CTR 和轉換率調整文案重點",
        "🎯 **受眾分析**：針對不同受眾群體調整語調和訴求點",
        "🔥 **情感連結**：使用情感化語言增強用戶共鳴",
        "⏰ **急迫感**：適當運用限時、限量等元素提升轉換",
        "📱 **平台適配**：確保文案在手機端顯示效果良好",
        "🔄 **A/B測試**：生成多個版本進行測試比較"
    ]

    for tip in optimization_tips:
        st.markdown(f"- {tip}")

if __name__ == "__main__":
    main()