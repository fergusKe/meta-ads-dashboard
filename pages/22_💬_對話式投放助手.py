import streamlit as st
import pandas as pd
from datetime import datetime
from utils.data_loader import load_meta_ads_data
from utils.agents.conversational_agent import ConversationalAdAgent
from utils.rag_service import RAGService

st.set_page_config(page_title="對話式投放助手", page_icon="💬", layout="wide")

def initialize_session():
    """初始化 session state"""
    if 'agent' not in st.session_state:
        st.session_state.agent = ConversationalAdAgent()

    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "您好！我是廣告投放助手 **小廣** 🤖\n\n我可以幫您：\n- 📊 查詢廣告數據\n- 🔍 分析活動表現\n- 💡 提供優化建議\n- ✍️ 參考高效文案\n\n請問有什麼可以幫您的嗎？",
                "intent": "chat",
                "suggestions": []
            }
        ]

    if 'rag_enabled' not in st.session_state:
        # 嘗試載入 RAG
        try:
            rag = RAGService()
            if rag.load_knowledge_base("ad_creatives"):
                st.session_state.rag_service = rag
                st.session_state.rag_enabled = True
            else:
                st.session_state.rag_service = None
                st.session_state.rag_enabled = False
        except:
            st.session_state.rag_service = None
            st.session_state.rag_enabled = False

def display_message(message):
    """顯示訊息"""
    role = message["role"]
    content = message["content"]

    if role == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(content)
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(content)

            # 顯示意圖標籤
            if "intent" in message and message["intent"]:
                intent_emoji = {
                    "query_data": "📊",
                    "analyze": "🔍",
                    "recommend": "💡",
                    "generate_copy": "✍️",
                    "optimize": "🚀",
                    "chat": "💬"
                }
                intent_text = {
                    "query_data": "查詢數據",
                    "analyze": "分析表現",
                    "recommend": "提供建議",
                    "generate_copy": "生成文案",
                    "optimize": "優化建議",
                    "chat": "一般對話"
                }
                emoji = intent_emoji.get(message["intent"], "💬")
                text = intent_text.get(message["intent"], "對話")
                st.caption(f"{emoji} {text}")

            # 顯示後續建議
            if "suggestions" in message and message["suggestions"]:
                st.markdown("**💡 您可能也想問：**")
                for sug in message["suggestions"]:
                    if st.button(sug, key=f"sug_{hash(sug)}_{len(st.session_state.messages)}"):
                        # 點擊建議時，自動送出
                        st.session_state.user_input = sug
                        st.rerun()

def main():
    st.title("💬 對話式投放助手「小廣」")
    st.markdown("""
    使用 **Pydantic AI** 開發的對話式 Agent，可以用自然語言與系統互動。

    **特色**：
    - 🗣️ 自然語言對話
    - 🧠 理解您的意圖
    - 🔧 自動調用合適工具
    - 📚 整合 RAG 知識庫
    - 💭 記憶對話上下文
    """)

    # 初始化
    initialize_session()

    # 載入數據
    df = load_meta_ads_data()
    if df is None:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 頂部控制區域
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        # RAG 狀態
        if st.session_state.rag_enabled:
            st.success("✅ RAG 知識庫已啟用")
        else:
            st.warning("⚠️ RAG 知識庫未啟用 - 前往「RAG 知識庫管理」建立")

    with col2:
        # 對話統計
        st.metric("對話輪數", len(st.session_state.messages))

    with col3:
        # 清除對話
        if st.button("🗑️ 清除對話歷史", use_container_width=True):
            st.session_state.agent.clear_history()
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": "對話已清除！有什麼可以幫您的嗎？",
                    "intent": "chat",
                    "suggestions": []
                }
            ]
            st.rerun()

    st.divider()

    # 範例問題和 Agent 資訊
    col_left, col_right = st.columns([3, 1])

    with col_right:
        # Agent 資訊
        with st.expander("🤖 Agent 資訊", expanded=False):
            st.markdown("""
            **名字**: 小廣
            **框架**: Pydantic AI
            **模型**: GPT-4o-mini
            **工具**: 4 個
            - 查詢活動
            - 獲取 Top 活動
            - RAG 搜尋
            - 整體摘要

            **能力**:
            - 多輪對話
            - 上下文記憶
            - 意圖識別
            - 工具自動選擇
            """)

        # 範例問題
        st.markdown("### 💡 範例問題")

        example_questions = [
            "目前整體投放表現如何？",
            "幫我分析表現最好的活動",
            "有哪些活動需要優化？",
            "給我看高 CTR 的文案範例",
            "推薦受眾擴展策略"
        ]

        for i, q in enumerate(example_questions):
            if st.button(q, key=f"example_{i}", use_container_width=True):
                st.session_state.user_input = q
                st.rerun()

    with col_left:
        # 顯示對話歷史
        st.markdown("### 💬 對話區域")

    # 顯示對話歷史
    for message in st.session_state.messages:
        display_message(message)

    # 用戶輸入
    user_input = st.chat_input("輸入您的問題...")

    # 處理建議點擊
    if 'user_input' in st.session_state and st.session_state.user_input:
        user_input = st.session_state.user_input
        del st.session_state.user_input

    if user_input:
        # 顯示用戶訊息
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        # Agent 回應
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("小廣正在思考..."):
                try:
                    # 執行 Agent
                    response = st.session_state.agent.chat_sync(
                        user_message=user_input,
                        df=df,
                        rag_service=st.session_state.rag_service
                    )

                    # 顯示回應
                    st.markdown(response.message)

                    # 顯示意圖
                    intent_emoji = {
                        "query_data": "📊",
                        "analyze": "🔍",
                        "recommend": "💡",
                        "generate_copy": "✍️",
                        "optimize": "🚀",
                        "chat": "💬"
                    }
                    intent_text = {
                        "query_data": "查詢數據",
                        "analyze": "分析表現",
                        "recommend": "提供建議",
                        "generate_copy": "生成文案",
                        "optimize": "優化建議",
                        "chat": "一般對話"
                    }
                    emoji = intent_emoji.get(response.intent, "💬")
                    text = intent_text.get(response.intent, "對話")
                    st.caption(f"{emoji} {text}")

                    # 顯示相關數據（如果有）
                    if response.data:
                        with st.expander("📊 查看詳細數據"):
                            st.json(response.data)

                    # 顯示建議
                    if response.suggestions:
                        st.markdown("**💡 您可能也想問：**")
                        for sug in response.suggestions:
                            if st.button(sug, key=f"sug_{hash(sug)}_{len(st.session_state.messages)}"):
                                st.session_state.user_input = sug
                                st.rerun()

                    # 儲存 Agent 回應
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.message,
                        "intent": response.intent,
                        "suggestions": response.suggestions,
                        "data": response.data
                    })

                except Exception as e:
                    st.error(f"❌ Agent 回應失敗: {str(e)}")
                    st.exception(e)

        # 重新渲染以顯示新訊息
        st.rerun()

    # 頁面底部說明
    with st.expander("📖 使用說明", expanded=False):
        st.markdown("""
        ## 如何與小廣對話

        ### 支援的問題類型

        **1. 查詢數據** 📊
        - "目前整體表現如何？"
        - "幫我查詢活動 A 的數據"
        - "最近一週花了多少錢？"

        **2. 分析表現** 🔍
        - "哪些活動表現最好？"
        - "為什麼活動 B 的 ROAS 這麼低？"
        - "對比活動 A 和活動 C"

        **3. 優化建議** 💡
        - "有哪些活動需要優化？"
        - "如何提升 CTR？"
        - "預算應該如何分配？"

        **4. 文案參考** ✍️
        - "給我看高效的廣告標題"
        - "有哪些高轉換的 CTA？"
        - "參考相似產品的文案"

        ### Agent 如何工作

        ```
        用戶問題
            ↓
        理解意圖（意圖分類）
            ↓
        選擇工具（自動決策）
            ↓
        調用工具獲取數據
            ↓
        分析並生成回應
            ↓
        提供後續建議
        ```

        ### 對話技巧

        ✅ **明確具體**
        - ❌ "幫我看一下"
        - ✅ "分析活動 A 的表現"

        ✅ **可以追問**
        - Agent 會記住上下文
        - 例如：先問"表現最好的活動"，再問"為什麼這些活動表現好？"

        ✅ **使用建議按鈕**
        - Agent 會提供相關的後續問題
        - 點擊即可快速詢問

        ### 與傳統頁面的差異

        | 特性 | 傳統頁面 | 對話式 Agent |
        |------|---------|-------------|
        | 操作方式 | 點擊按鈕、填表單 | 自然語言 |
        | 靈活性 | 固定功能 | 自由組合 |
        | 學習成本 | 需熟悉介面 | 直接問問題 |
        | 適合場景 | 深度分析 | 快速查詢 |

        ### 最佳實踐

        1. **快速查詢**：用對話式助手
        2. **深度分析**：用專門頁面
        3. **探索發現**：兩者結合使用

        ### 未來功能

        - 🚀 語音輸入/輸出
        - 🚀 主動推送通知
        - 🚀 自動執行優化
        - 🚀 多 Agent 協作（數據分析師 + 策略師）
        """)

if __name__ == "__main__":
    main()
