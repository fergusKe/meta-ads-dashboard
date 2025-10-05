import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import json

# 添加父目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import load_meta_ads_data
from utils.rag_service import RAGService

def show_rag_management():
    """顯示 RAG 知識庫管理頁面"""
    st.markdown("# 🧠 RAG 知識庫管理")
    st.markdown("建立和管理歷史廣告素材與優化案例知識庫")

    st.info("""
💡 **什麼是 RAG 知識庫？**

RAG（Retrieval-Augmented Generation）可以讓 AI 從歷史成功案例中學習，生成更準確的建議。

**知識庫類型**：
1. **高效廣告素材庫**：儲存 ROAS >= 3.0 的廣告（Headline、文案、CTA、受眾）
2. **優化案例庫**：儲存過去的優化案例（問題、解決方案、效果）

**使用場景**：
- 生成文案時，參考歷史高效 Headline
- 提供優化建議時，引用相似的成功案例
- 分析受眾時，找出過去對該受眾有效的素材
    """)

    # 初始化 RAG 服務
    rag = RAGService()

    # 載入數據
    df = load_meta_ads_data()
    if df is None or df.empty:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    st.markdown("---")

    # ========== 第一部分：知識庫狀態 ==========
    st.markdown("## 📊 知識庫狀態")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🎨 高效廣告素材庫")

        # 檢查知識庫是否存在
        try:
            if rag.load_knowledge_base("ad_creatives"):
                stats = rag.get_stats()

                if stats['status'] == 'loaded':
                    st.success(f"""
**✅ 知識庫已建立**

- 素材數量：{stats['count']} 筆
- 儲存位置：`{stats['persist_directory']}`
- 狀態：可用
                    """)
                else:
                    st.warning("知識庫存在但載入失敗")
            else:
                st.warning("知識庫尚未建立")
        except:
            st.warning("知識庫尚未建立，請先建立知識庫")

    with col2:
        st.markdown("### 📚 優化案例庫")
        st.info("""
**🚧 開發中**

優化案例庫將儲存：
- 過去的優化決策
- 效果追蹤記錄
- 成功/失敗經驗

**即將推出**
        """)

    st.markdown("---")

    # ========== 第二部分：建立廣告素材知識庫 ==========
    st.markdown("## 🛠️ 建立高效廣告素材知識庫")

    st.markdown("""
從當前數據中提取高效廣告（ROAS >= 3.0）並建立向量資料庫，供 AI 學習參考。
    """)

    # 顯示可用的高效廣告數量
    high_performing_count = len(df[df['購買 ROAS（廣告投資報酬率）'] >= 3.0])

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("總廣告數", f"{len(df)} 筆")

    with col2:
        st.metric("高效廣告數", f"{high_performing_count} 筆", delta=f"{high_performing_count/len(df)*100:.1f}%")

    with col3:
        avg_roas = df[df['購買 ROAS（廣告投資報酬率）'] >= 3.0]['購買 ROAS（廣告投資報酬率）'].mean()
        st.metric("平均 ROAS", f"{avg_roas:.2f}" if high_performing_count > 0 else "N/A")

    if high_performing_count == 0:
        st.warning("⚠️ 沒有找到高效廣告（ROAS >= 3.0），無法建立知識庫")
    else:
        # 顯示高效廣告範例
        st.markdown("### 📋 高效廣告範例預覽")

        sample_ads = df[df['購買 ROAS（廣告投資報酬率）'] >= 3.0].nlargest(5, '購買 ROAS（廣告投資報酬率）')

        st.dataframe(
            sample_ads[[
                'headline',
                'call_to_action_type',
                '購買 ROAS（廣告投資報酬率）',
                'CTR（全部）',
                '購買次數',
                '年齡',
                '性別'
            ]],
            use_container_width=True,
            column_config={
                "headline": "Headline",
                "call_to_action_type": "CTA",
                "購買 ROAS（廣告投資報酬率）": st.column_config.NumberColumn("ROAS", format="%.2f"),
                "CTR（全部）": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
                "購買次數": st.column_config.NumberColumn("購買", format="%d"),
                "年齡": "年齡",
                "性別": "性別"
            },
            hide_index=True
        )

        # 建立知識庫按鈕
        st.markdown("### 🚀 開始建立")

        if st.button("🔨 建立/更新廣告素材知識庫", type="primary"):
            with st.spinner(f"正在建立知識庫（處理 {high_performing_count} 筆廣告）..."):
                try:
                    # 建立知識庫
                    rag.create_ad_creative_knowledge_base(df, collection_name="ad_creatives")

                    st.success(f"""
✅ **知識庫建立成功！**

- 已索引：{high_performing_count} 筆高效廣告
- 包含：Headline、文案、CTA、受眾、成效指標
- 狀態：可供 AI 檢索使用

**下一步**：
1. 前往「AI文案生成」頁面測試 RAG 增強功能
2. 前往「即時優化建議」頁面查看歷史案例引用
                    """)

                    # 顯示知識庫統計
                    stats = rag.get_stats()
                    st.json(stats)

                except Exception as e:
                    st.error(f"""
❌ **知識庫建立失敗**

錯誤訊息：{str(e)}

可能原因：
1. OpenAI API Key 未設定或無效
2. 網路連線問題
3. 權限不足（無法寫入資料庫檔案）

請檢查設定後重試。
                    """)

    st.markdown("---")

    # ========== 第三部分：測試知識庫檢索 ==========
    st.markdown("## 🔍 測試知識庫檢索")

    st.markdown("""
測試向量搜尋功能，查看 AI 能否找到相關的歷史案例。
    """)

    # 嘗試載入知識庫
    try:
        if rag.load_knowledge_base("ad_creatives"):
            st.success("✅ 知識庫已載入，可以開始測試")

            # 測試查詢
            query = st.text_input(
                "輸入搜尋查詢",
                placeholder="例如：高轉換率的 Headline",
                help="輸入你想找的廣告特徵，AI 會從知識庫中檢索相似案例"
            )

            k = st.slider("檢索數量", min_value=1, max_value=10, value=3)

            if st.button("🔍 搜尋相似案例"):
                if query:
                    with st.spinner("正在檢索..."):
                        results = rag.search_similar_ads(query, k=k)

                        if results:
                            st.success(f"找到 {len(results)} 個相關案例")

                            for i, doc in enumerate(results, 1):
                                with st.expander(f"📄 案例 {i}（ROAS {doc.metadata.get('roas', 0):.2f}）"):
                                    st.markdown(doc.page_content)

                                    st.markdown("**Metadata：**")
                                    st.json(doc.metadata)
                        else:
                            st.warning("沒有找到相關案例")
                else:
                    st.warning("請輸入搜尋查詢")

            # 預設查詢範例
            st.markdown("### 💡 查詢範例")

            example_col1, example_col2, example_col3 = st.columns(3)

            with example_col1:
                if st.button("📝 查詢：高 CTR Headline"):
                    results = rag.search_similar_ads("CTR 高的 Headline 特徵", k=3)
                    for i, doc in enumerate(results, 1):
                        st.markdown(f"**案例 {i}**：{doc.metadata.get('headline', '未知')}")
                        st.caption(f"ROAS: {doc.metadata.get('roas', 0):.2f}")

            with example_col2:
                if st.button("🎯 查詢：女性受眾廣告"):
                    results = rag.search_similar_ads("針對女性的高效廣告", k=3)
                    for i, doc in enumerate(results, 1):
                        st.markdown(f"**案例 {i}**：{doc.metadata.get('headline', '未知')}")
                        st.caption(f"受眾: {doc.metadata.get('gender', '未知')}")

            with example_col3:
                if st.button("💰 查詢：高 ROAS CTA"):
                    results = rag.search_similar_ads("高 ROAS 的 CTA 類型", k=3)
                    for i, doc in enumerate(results, 1):
                        st.markdown(f"**CTA**: {doc.metadata.get('cta', '未知')}")
                        st.caption(f"ROAS: {doc.metadata.get('roas', 0):.2f}")

        else:
            st.warning("知識庫尚未建立或載入失敗，請先建立知識庫")

    except Exception as e:
        st.warning(f"知識庫尚未建立：{str(e)}")

    st.markdown("---")

    # ========== 第四部分：知識庫管理 ==========
    st.markdown("## ⚙️ 知識庫管理")

    manage_col1, manage_col2 = st.columns(2)

    with manage_col1:
        st.markdown("### 🗑️ 清除知識庫")

        st.warning("""
**注意**：此操作將刪除所有已建立的向量資料庫。

刪除後需要重新建立知識庫才能使用 RAG 功能。
        """)

        if st.button("🗑️ 清除所有知識庫", type="secondary"):
            import shutil

            chroma_dir = Path(rag.persist_directory)
            if chroma_dir.exists():
                try:
                    shutil.rmtree(chroma_dir)
                    st.success("✅ 知識庫已清除")
                except Exception as e:
                    st.error(f"清除失敗：{str(e)}")
            else:
                st.info("知識庫目錄不存在，無需清除")

    with manage_col2:
        st.markdown("### 📊 知識庫資訊")

        chroma_dir = Path(rag.persist_directory)

        if chroma_dir.exists():
            # 計算資料夾大小
            total_size = sum(f.stat().st_size for f in chroma_dir.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)

            st.info(f"""
**儲存資訊**：
- 路徑：`{chroma_dir}`
- 大小：{size_mb:.2f} MB
- 檔案數：{len(list(chroma_dir.rglob('*')))}
            """)
        else:
            st.info("知識庫目錄不存在")

if __name__ == "__main__":
    show_rag_management()
