import streamlit as st
import os
from utils.cache_manager import get_agent_cache

st.set_page_config(page_title="快取管理", page_icon="🗄️", layout="wide")

st.title("🗄️ Agent 快取管理")
st.markdown("管理 AI Agent 執行結果的快取，節省 API 成本並提升效能")

# 取得快取管理器
cache = get_agent_cache()

# 取得統計資料
stats = cache.get_stats()

# 顯示快取狀態
st.subheader("📊 快取狀態")

col1, col2, col3, col4 = st.columns(4)

with col1:
    status_icon = "✅" if stats['enabled'] else "❌"
    status_text = "啟用" if stats['enabled'] else "停用"
    st.metric("快取狀態", f"{status_icon} {status_text}")

with col2:
    st.metric("總快取數", stats['total_entries'])

with col3:
    st.metric("有效快取", stats['active_entries'])

with col4:
    st.metric("過期快取", stats['expired_entries'])

st.divider()

# 設定說明
st.subheader("⚙️ 設定說明")

config_status = "✅ **已啟用**" if stats['enabled'] else "❌ **未啟用**（預設）"

st.markdown(f"""
**當前配置**：{config_status}

**快取過期時間**：{stats['ttl_seconds']} 秒（{stats['ttl_seconds']//60} 分鐘）

**如何修改設定**：

1. 開啟 `.env` 檔案
2. 修改以下設定：
```env
# 啟用快取（正式環境建議）
ENABLE_AGENT_CACHE=true

# 快取過期時間（秒）
AGENT_CACHE_TTL=3600
```
3. 重新啟動應用程式

**建議**：
- 🧪 **開發階段**：`ENABLE_AGENT_CACHE=false`（方便測試調整效果）
- 🚀 **正式環境**：`ENABLE_AGENT_CACHE=true`（節省成本 40-60%）
""")

st.divider()

# 快取效益說明
st.subheader("💡 快取效益")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **啟用快取的好處**：
    - 💰 節省 API 成本 40-60%
    - ⚡ 響應速度提升 10-100 倍
    - 😊 用戶體驗更流暢
    - 🌍 減少碳排放
    """)

with col2:
    st.markdown("""
    **何時應該停用快取**：
    - 🧪 開發階段測試新 Prompt
    - 🔧 調整 Agent 參數後驗證效果
    - 🐛 除錯 Agent 輸出問題
    - 📊 需要即時最新結果
    """)

st.divider()

# 快取管理操作
st.subheader("🛠️ 快取管理操作")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🗑️ 清空所有快取", type="secondary", use_container_width=True):
        cache.clear()
        st.success("✅ 所有快取已清空")
        st.rerun()

with col2:
    if st.button("🧹 清理過期快取", type="secondary", use_container_width=True):
        cleaned = cache.cleanup_expired()
        st.success(f"✅ 已清理 {cleaned} 個過期快取")
        st.rerun()

with col3:
    if st.button("🔄 重新整理", type="secondary", use_container_width=True):
        st.rerun()

# 顯示提示
if not stats['enabled']:
    st.info("""
    💡 **提示**：快取目前為停用狀態。如果您在正式環境使用，建議啟用快取以節省成本。

    在 `.env` 檔案中設定 `ENABLE_AGENT_CACHE=true` 即可啟用。
    """)

if stats['expired_entries'] > 0:
    st.warning(f"""
    ⚠️ **注意**：目前有 {stats['expired_entries']} 個過期快取。

    建議點擊「清理過期快取」按鈕釋放記憶體空間。
    """)

st.divider()

# 快取工作原理說明
with st.expander("📖 快取工作原理", expanded=False):
    st.markdown("""
    ### 快取機制說明

    **1. 快取 Key 生成**
    - 根據 Agent 名稱 + 輸入參數生成唯一 MD5 hash
    - 相同參數的請求會命中相同快取

    **2. 快取儲存**
    - 使用 Streamlit Session State 儲存
    - 每個快取項目包含：結果 + 時間戳

    **3. 快取有效期**
    - 預設 3600 秒（1 小時）
    - 超過有效期自動失效

    **4. 快取命中流程**
    ```
    用戶請求 → 檢查快取 →
    ├─ 命中 → 立即返回（節省成本）
    └─ 未命中 → 呼叫 API → 儲存快取 → 返回結果
    ```

    ### 技術實作

    在 Agent 的 `generate_copy()` 方法上加上 `@cache_agent_result()` 裝飾器：

    ```python
    @cache_agent_result()
    async def generate_copy(self, ...):
        # Agent 執行邏輯
        ...
    ```

    裝飾器會自動處理：
    - 快取 key 生成
    - 快取檢查與返回
    - 結果儲存
    - 過期處理
    """)

# 使用指南
with st.expander("📚 使用指南", expanded=False):
    st.markdown("""
    ### 開發階段

    1. 保持快取**停用**（`ENABLE_AGENT_CACHE=false`）
    2. 每次修改 Prompt 或參數後，都能看到最新效果
    3. 不需要手動清除快取

    ### 測試階段

    1. **啟用**快取（`ENABLE_AGENT_CACHE=true`）
    2. 測試相同請求的響應時間
    3. 驗證快取命中率
    4. 評估成本節省效果

    ### 正式環境

    1. **啟用**快取（`ENABLE_AGENT_CACHE=true`）
    2. 設定合適的過期時間（建議 1-4 小時）
    3. 定期監控快取統計數據
    4. 在重大更新後清空快取

    ### 最佳實踐

    - ✅ 高頻請求適合快取（如：文案生成）
    - ✅ 結果穩定的請求適合快取（如：數據分析）
    - ❌ 即時性要求高的不適合快取（如：競價數據）
    - ❌ 個人化結果不適合快取（如：用戶專屬建議）
    """)
