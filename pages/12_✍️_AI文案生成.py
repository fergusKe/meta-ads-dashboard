import streamlit as st
import pandas as pd
import os
from datetime import datetime
from utils.data_loader import load_meta_ads_data
from utils.rag_service import RAGService
from utils.agents import CopywritingAgent

st.set_page_config(page_title="AI 文案生成", page_icon="✍️", layout="wide")

def main():
    st.title("✍️ AI 文案生成")
    st.markdown("使用 Pydantic AI Agent 為耘初茶食生成高效廣告文案")

    # 載入數據
    df = load_meta_ads_data()

    if df is None:
        st.error("❌ 無法載入廣告數據")
        st.stop()

    # 初始化 Agent
    try:
        copywriting_agent = CopywritingAgent()
    except Exception as e:
        st.error(f"❌ Agent 初始化失敗：{str(e)}")
        st.stop()

    # ========== 主要內容區域 ==========
    st.subheader("🆕 AI 生成全新廣告文案")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("#### 📝 設定文案參數")

        # 目標受眾
        target_audience_preset = st.selectbox(
            "目標受眾",
            ["茶飲愛好者", "健康養生族群", "上班族", "年輕消費者（18-34歲）", "中年消費者（35-54歲）", "高端消費者", "自定義"]
        )

        if target_audience_preset == "自定義":
            target_audience = st.text_input("請描述目標受眾", placeholder="例如：25-35歲注重生活品質的女性")
        else:
            target_audience = target_audience_preset

        # 廣告目標
        campaign_objective = st.selectbox(
            "廣告目標",
            ["提升品牌知名度", "促進產品銷售", "推廣新品上市", "增加網站流量", "提升顧客互動", "自定義"]
        )

        if campaign_objective == "自定義":
            campaign_objective = st.text_input("請描述廣告目標", placeholder="例如：推廣限時優惠活動")

        # 特殊要求
        special_requirements = st.text_area(
            "特殊要求（選填）",
            placeholder="例如：強調限時優惠、突出新品特色、包含特定關鍵字、避免使用某些詞彙等",
            height=100
        )

        # RAG 開關
        use_rag = st.checkbox(
            "📚 參考歷史高效案例（建議開啟）",
            value=True,
            help="啟用後將從歷史 ROAS >= 3.0 的高效廣告中學習成功模式"
        )

    with col2:
        st.markdown("#### 📊 參考數據")

        avg_roas = df['購買 ROAS（廣告投資報酬率）'].mean()
        avg_ctr = df['CTR（全部）'].mean() * 100
        total_purchases = df['購買次數'].sum()

        st.metric("平均 ROAS", f"{avg_roas:.2f}")
        st.metric("平均點擊率", f"{avg_ctr:.2f}%")
        st.metric("總購買次數", f"{total_purchases:.0f}")

        st.info(f"💡 平均ROAS為 {avg_roas:.2f}，建議文案強調產品價值和轉換效果")

    # 生成按鈕
    st.divider()

    if st.button("🚀 開始生成文案（Pydantic AI Agent）", type="primary", use_container_width=True):
        # 創建執行日誌容器
        log_container = st.container()

        with log_container:
            st.markdown("### 🤖 Agent 執行流程")

            # Step 1: 初始化
            with st.status("📋 Step 1: 初始化 CopywritingAgent", expanded=True) as status:
                model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
                st.write("✓ Agent 類型：**CopywritingAgent**")
                st.write(f"✓ 模型：**{model_name}**（從 .env 讀取）")
                st.write("✓ 輸出類型：**CopywritingResult**（型別安全）")
                status.update(label="✅ Step 1: Agent 初始化完成", state="complete")

            # Step 2: 載入 RAG
            rag_service = None
            if use_rag:
                with st.status("📚 Step 2: 載入 RAG 知識庫", expanded=True) as status:
                    try:
                        rag_service = RAGService()
                        if rag_service.load_knowledge_base("ad_creatives"):
                            st.write("✓ 知識庫：**ad_creatives**")
                            st.write("✓ 檢索方法：**語義搜尋**（向量相似度）")
                            st.write("✓ 參考案例：**Top 3 高 ROAS 廣告**")
                            status.update(label="✅ Step 2: RAG 知識庫載入完成", state="complete")
                    except Exception as e:
                        st.write(f"⚠️ RAG 載入失敗：{str(e)}")
                        rag_service = None
                        status.update(label="⚠️ Step 2: RAG 不可用，將使用一般模式", state="error")
            else:
                st.info("📚 Step 2: 已跳過 RAG 知識庫（未啟用）")

            # Step 3: Agent 工具調用
            with st.status("🔧 Step 3: Agent 調用內建工具", expanded=True) as status:
                st.write("**CopywritingAgent 會自動調用以下工具：**")
                st.write("1. 🎯 `get_top_performing_copy()` - 分析高效文案範例")
                st.write("2. 👥 `get_audience_insights()` - 獲取受眾洞察")
                st.write("3. 🎨 `get_brand_voice_guidelines()` - 獲取品牌語調")
                st.write("4. 🔍 `analyze_competitor_messaging()` - 分析競品訊息（使用 RAG）" if use_rag else "4. 🔍 `analyze_competitor_messaging()` - 分析市場定位")
                st.write("5. 🌸 `get_seasonal_themes()` - 獲取當季主題")
                status.update(label="✅ Step 3: 工具準備就緒", state="complete")

            # Step 4: 生成文案
            with st.status("✍️ Step 4: AI 生成文案（結構化輸出）", expanded=True) as status:
                st.write(f"🤖 正在調用 **{model_name}** 模型...")
                st.write("📝 生成 **3-5 個文案變體**...")
                st.write("🔍 執行 **Pydantic 驗證**（確保輸出格式正確）...")

                try:
                    # 呼叫 Agent 生成文案
                    result = copywriting_agent.generate_copy_sync(
                        df=df,
                        target_audience=target_audience,
                        campaign_objective=campaign_objective,
                        special_requirements=special_requirements or None,
                        rag_service=rag_service
                    )

                    st.write(f"✓ 成功生成 **{len(result.variants)} 個文案變體**")
                    st.write("✓ **型別驗證通過**（完全型別安全）")
                    status.update(label="✅ Step 4: 文案生成完成", state="complete")

                    # Step 5: 輸出總結
                    with st.status("📊 Step 5: 輸出分析", expanded=True) as final_status:
                        st.write("**生成內容包含：**")
                        st.write(f"• {len(result.variants)} 個文案變體（標題 + 內文 + CTA）")
                        st.write(f"• {len(result.ab_test_suggestions)} 個 A/B 測試建議")
                        st.write(f"• {len(result.optimization_tips)} 個優化建議")
                        st.write("• 1 個整體策略說明")
                        st.write("• 1 個表現預測分析")
                        st.write("• 1 個合規性檢查結果")
                        final_status.update(label="✅ Step 5: 所有輸出已驗證", state="complete")

                    st.success("🎉 **文案生成完成！**（使用 Pydantic AI Agent）")

                except Exception as e:
                    st.error(f"❌ 文案生成失敗：{str(e)}")
                    status.update(label="❌ Step 4: 生成失敗", state="error")
                    import traceback
                    with st.expander("🔍 錯誤詳情"):
                        st.code(traceback.format_exc())
                    st.stop()

        st.divider()

        # 顯示結果
        st.divider()

        # 策略說明
        st.subheader("📋 策略說明")
        st.info(result.strategy_explanation)

        st.divider()

        # 顯示文案變體
        st.subheader(f"✨ 生成的文案變體（共 {len(result.variants)} 個）")

        for i, variant in enumerate(result.variants, 1):
            with st.expander(f"📝 變體 {i}：{variant.tone}", expanded=(i == 1)):
                # 模擬廣告預覽
                st.markdown(f"""
                <div style="border: 1px solid #ddd; border-radius: 8px; padding: 20px; background: white; margin: 16px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="font-weight: bold; font-size: 20px; margin-bottom: 12px; color: #1c1e21;">
                        {variant.headline}
                    </div>
                    <div style="font-size: 15px; margin-bottom: 16px; color: #1c1e21; line-height: 1.6; white-space: pre-wrap;">
{variant.primary_text}
                    </div>
                    <div style="text-align: center; margin-top: 16px;">
                        <button style="background: #1877f2; color: white; border: none; padding: 12px 32px; border-radius: 6px; font-weight: bold; font-size: 15px; cursor: pointer;">
                            {variant.cta}
                        </button>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 詳細資訊
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**🎯 核心資訊**")
                    st.write(f"**語氣風格**：{variant.tone}")
                    st.write(f"**目標受眾**：{variant.target_audience}")
                    st.write(f"**核心訊息**：{variant.key_message}")

                with col2:
                    st.markdown("**💡 策略要點**")
                    st.write(f"**情感訴求**：{variant.emotional_appeal}")
                    st.write(f"**差異化重點**：{variant.differentiation}")

                # 複製按鈕
                copy_text = f"""標題：{variant.headline}

內文：
{variant.primary_text}

CTA：{variant.cta}"""
                st.text_area(
                    f"複製文案（變體 {i}）",
                    value=copy_text,
                    height=150,
                    key=f"copy_variant_{i}",
                    label_visibility="collapsed"
                )

        st.divider()

        # A/B 測試建議
        st.subheader("🧪 A/B 測試建議")
        for i, suggestion in enumerate(result.ab_test_suggestions, 1):
            st.markdown(f"**{i}.** {suggestion}")

        st.divider()

        # 優化建議
        st.subheader("💡 優化建議")
        for i, tip in enumerate(result.optimization_tips, 1):
            st.markdown(f"**{i}.** {tip}")

        st.divider()

        # 表現預測
        st.subheader("📊 表現預測")
        st.info(result.performance_prediction)

        st.divider()

        # 合規性檢查
        st.subheader("✅ Meta 廣告政策合規性檢查")
        st.success(result.compliance_check)

        # 儲存到 session state（供其他頁面使用）
        st.session_state['latest_copywriting_result'] = result
        st.session_state['latest_copywriting_timestamp'] = datetime.now()

    # 顯示歷史生成記錄（如果有）
    if 'latest_copywriting_result' in st.session_state:
        st.divider()
        st.caption(f"上次生成時間：{st.session_state.get('latest_copywriting_timestamp', '未知')}")

    # 使用指南
    with st.expander("📖 使用指南", expanded=False):
        st.markdown("""
        ### 🎯 如何獲得最佳文案

        **1. 明確目標受眾**
        - 越具體越好（年齡、興趣、需求）
        - 例如：「25-34歲注重健康養生的上班族女性」

        **2. 清晰的廣告目標**
        - 品牌知名度：強調品牌故事和價值
        - 產品銷售：突出產品優勢和優惠
        - 新品推廣：製造好奇心和嘗鮮感

        **3. 善用特殊要求**
        - 強調特定賣點
        - 包含關鍵字（如「限時」「新品」）
        - 避免某些詞彙（如過度誇張的用語）

        **4. 啟用 RAG 知識庫**
        - 學習歷史高效案例
        - 提高文案成功率
        - 建議保持開啟

        **5. 多變體測試**
        - Agent 會生成 3-5 個不同角度的文案
        - 建議全部測試，找出最佳表現者
        - 使用 A/B 測試建議優化

        ### 🤖 Pydantic AI Agent 優勢

        - ✅ **型別安全**：保證輸出格式一致
        - ✅ **結構化輸出**：自動驗證數據完整性
        - ✅ **工具整合**：自動調用歷史數據和 RAG
        - ✅ **可觀測性**：可追蹤執行過程
        - ✅ **品質保證**：內建合規性檢查
        """)

    # 文案撰寫技巧
    with st.expander("💡 文案撰寫技巧", expanded=False):
        st.markdown("""
        ### Meta 廣告文案最佳實踐

        **標題（Headline）**
        - ✅ 25-40 字最佳
        - ✅ 包含核心賣點
        - ✅ 引發好奇或共鳴
        - ❌ 避免過度誇張

        **內文（Primary Text）**
        - ✅ 90-125 字最佳
        - ✅ 前 2-3 句最重要
        - ✅ 有故事性或情境感
        - ✅ 使用具體數字和利益點

        **CTA（Call-to-Action）**
        - ✅ 明確且具體
        - ✅ 製造緊迫感
        - ✅ 降低行動門檻
        - 範例：「立即選購」「了解更多」「限時優惠」

        **避免事項**
        - ❌ 誇大效果（「一定」「保證」「100%」）
        - ❌ 針對個人特徵（「你是不是很胖」）
        - ❌ 製造不安全感（「你的健康出問題了」）
        - ❌ 文字佔比超過 20%（圖片中）
        """)

if __name__ == "__main__":
    main()
