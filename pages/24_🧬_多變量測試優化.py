import streamlit as st
import pandas as pd
import numpy as np
import itertools
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.agents import MVTDesignAgent, MVTDesignResult
from utils.data_loader import load_meta_ads_data

st.set_page_config(page_title="多變量測試優化", page_icon="🧬", layout="wide")

def calculate_mvt_sample_size(num_variants, baseline_rate, mde, alpha=0.05, power=0.8):
    """
    計算 MVT 所需樣本數

    MVT 需要更大的樣本數，因為要測試多個組合
    """
    from scipy.stats import norm

    p1 = baseline_rate
    p2 = baseline_rate * (1 + mde)

    z_alpha = norm.ppf(1 - alpha / (2 * num_variants))  # Bonferroni 校正
    z_beta = norm.ppf(power)

    p_avg = (p1 + p2) / 2

    n = (z_alpha * np.sqrt(2 * p_avg * (1 - p_avg)) + z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2)))**2 / (p1 - p2)**2

    return int(np.ceil(n))

def generate_variant_combinations(variables):
    """生成所有可能的變體組合"""
    keys = list(variables.keys())
    values = [variables[k] for k in keys]

    combinations = list(itertools.product(*values))

    combo_list = []
    for i, combo in enumerate(combinations, 1):
        combo_dict = {
            'ID': f'V{i}',
            **{keys[j]: combo[j] for j in range(len(keys))}
        }
        combo_list.append(combo_dict)

    return pd.DataFrame(combo_list)

def calculate_factorial_effects(results_df, variables):
    """計算各因子的主效應和交互效應"""
    effects = {}

    # 計算主效應
    for var in variables.keys():
        var_effects = {}
        for value in variables[var]:
            mask = results_df[var] == value
            if mask.sum() > 0:
                var_effects[value] = results_df[mask]['轉換率'].mean()
        effects[var] = var_effects

    return effects

def simulate_mvt_results(combinations_df, baseline_rate=0.02):
    """模擬 MVT 結果（示範用）"""
    np.random.seed(42)

    # 為每個組合生成模擬數據
    combinations_df['訪客數'] = np.random.randint(500, 2000, size=len(combinations_df))

    # 基於組合特徵生成不同的轉換率
    base_rates = []
    for _, row in combinations_df.iterrows():
        rate = baseline_rate
        # 簡單的效應模擬
        rate *= np.random.uniform(0.8, 1.5)
        base_rates.append(rate)

    combinations_df['轉換率'] = base_rates
    combinations_df['轉換數'] = (combinations_df['訪客數'] * combinations_df['轉換率']).astype(int)
    combinations_df['信賴區間'] = combinations_df.apply(
        lambda row: f"±{np.sqrt(row['轉換率'] * (1 - row['轉換率']) / row['訪客數']) * 1.96 * 100:.2f}%",
        axis=1
    )

    return combinations_df

@st.cache_resource
def get_mvt_design_agent() -> MVTDesignAgent | None:
    """建立並快取 MVTDesignAgent。"""
    try:
        return MVTDesignAgent()
    except Exception as exc:  # pragma: no cover - Streamlit 介面顯示
        st.error(f"❌ 無法初始化 MVTDesignAgent：{exc}")
        return None


def render_mvt_design_result(result: MVTDesignResult) -> None:
    """呈現 MVTDesignAgent 的輸出。"""
    plan = result.plan

    st.subheader("🧭 MVT 測試計畫")
    st.markdown(f"**核心假設**：{plan.hypothesis}")

    col1, col2 = st.columns(2)
    col1.metric("主要衡量指標", plan.primary_metric)
    col2.metric("總組合數", str(plan.required_runs))

    st.markdown("### 🔬 測試因子與層級")
    for idx, factor in enumerate(plan.factors, start=1):
        header = f"{idx}. {factor.factor}"
        with st.expander(header, expanded=(idx == 1)):
            st.markdown(f"**選擇理由**：{factor.rationale}")
            st.markdown("**測試層級**：")
            for level in factor.levels:
                st.markdown(f"- {level}")

    if plan.interaction_focus:
        st.markdown("### 🔁 交互作用關注")
        for item in plan.interaction_focus:
            st.markdown(f"- {item}")

    if plan.phased_rollout:
        st.markdown("### 🚀 分階段上線策略")
        for phase in plan.phased_rollout:
            st.markdown(f"- {phase}")

    _render_bullet_section("📡 資料蒐集計畫", result.data_collection_plan)
    _render_bullet_section("🧮 分析框架", result.analysis_framework)
    _render_bullet_section("🛡️ 風險控管", result.risk_controls)
    _render_bullet_section("👥 利害關係人", result.stakeholders)


def _render_bullet_section(title: str, items: list[str]) -> None:
    if not items:
        return
    st.markdown(f"### {title}")
    for item in items:
        st.markdown(f"- {item}")


def main():
    st.title("🧬 多變量測試（MVT）優化")
    st.markdown("""
    設計並分析多變量測試，找出廣告元素的最佳組合。

    **MVT vs A/B 測試**：
    - 📊 **A/B 測試**：一次測試一個變數（標題 A vs B）
    - 🧬 **MVT**：同時測試多個變數（標題 × 圖片 × CTA）
    - 💡 **優勢**：更快找到最佳組合，發現交互效應
    - ⚠️ **挑戰**：需要更大流量，分析更複雜
    """)

    # 載入數據
    df = load_meta_ads_data()
    if df is None:
        st.error("無法載入數據，請檢查數據檔案。")
        return

    # 測試設定移到主要區域
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🎯 測試設定")
        test_objective = st.selectbox(
            "測試目標",
            ["提升轉換率", "提升 CTR", "提升 ROAS", "降低 CPA"]
        )

    with col2:
        st.subheader("📊 功能說明")
        st.info("""
        **MVT 測試流程**

        - 🔧 設計測試變體
        - 📊 預覽所有組合
        - 🤖 AI 優化建議
        - 📈 結果分析解讀
        """)

    st.markdown("---")

    # 主要內容
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔧 設計變體",
        "📊 組合預覽",
        "🤖 AI 分析",
        "📈 結果分析"
    ])

    with tab1:
        st.markdown("## 🔧 設計測試變體")

        st.info("💡 定義要測試的變數和選項。建議：2-4 個變數，每個 2-3 個選項")

        # 變數定義
        st.markdown("### 📝 定義測試變數")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 變數 1：標題")
            headline_options = st.text_area(
                "輸入標題選項（每行一個）",
                value="限時優惠 85 折起\n新品上市 免運費\n會員專享 買一送一",
                height=120,
                key="headlines"
            )
            headlines = [h.strip() for h in headline_options.split('\n') if h.strip()]

            st.markdown("#### 變數 2：圖片風格")
            image_options = st.text_area(
                "輸入圖片風格選項（每行一個）",
                value="產品特寫\n生活情境\n使用者見證",
                height=100,
                key="images"
            )
            images = [i.strip() for i in image_options.split('\n') if i.strip()]

        with col2:
            st.markdown("#### 變數 3：CTA")
            cta_options = st.text_area(
                "輸入 CTA 選項（每行一個）",
                value="立即購買\n了解更多\n限時搶購",
                height=120,
                key="ctas"
            )
            ctas = [c.strip() for c in cta_options.split('\n') if c.strip()]

            st.markdown("#### 變數 4：受眾（選填）")
            audience_options = st.text_area(
                "輸入受眾選項（每行一個，可留空）",
                value="25-34 歲女性\n35-44 歲女性",
                height=100,
                key="audiences"
            )
            audiences = [a.strip() for a in audience_options.split('\n') if a.strip()]

        # 整合變數
        variables = {
            '標題': headlines,
            '圖片': images,
            'CTA': ctas
        }

        if audiences:
            variables['受眾'] = audiences

        # 計算組合數
        num_combinations = 1
        for v in variables.values():
            num_combinations *= len(v)

        st.markdown("---")

        # 測試規模評估
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("變數數量", len(variables))

        with col2:
            st.metric("總組合數", num_combinations)

        with col3:
            complexity = "🟢 簡單" if num_combinations <= 10 else "🟡 中等" if num_combinations <= 20 else "🔴 複雜"
            st.metric("複雜度", complexity)

        # 警告
        if num_combinations > 30:
            st.error(f"""
            ⚠️ **組合數過多（{num_combinations} 個）！**

            建議：
            - 減少變數數量（建議 2-3 個）
            - 減少每個變數的選項（建議 2-3 個）
            - 或改用階段式測試（先測試部分組合）
            """)
        elif num_combinations > 20:
            st.warning(f"⚠️ 組合數較多（{num_combinations} 個），需要大量流量。建議評估是否簡化測試。")

        # 儲存變數
        st.session_state['mvt_variables'] = variables
        st.session_state['mvt_combinations'] = num_combinations

    with tab2:
        st.markdown("## 📊 變體組合預覽")

        if 'mvt_variables' not in st.session_state:
            st.warning("請先在「設計變體」標籤中定義測試變數")
        else:
            variables = st.session_state['mvt_variables']
            num_combinations = st.session_state['mvt_combinations']

            # 生成組合
            combinations_df = generate_variant_combinations(variables)

            st.success(f"✅ 已生成 {len(combinations_df)} 個測試組合")

            # 顯示組合表格
            st.markdown("### 📋 所有測試組合")
            st.dataframe(
                combinations_df,
                use_container_width=True,
                height=400
            )

            # 樣本數計算
            st.markdown("---")
            st.markdown("### 📐 樣本數計算")

            col1, col2 = st.columns(2)

            with col1:
                baseline_rate = st.number_input(
                    "當前轉換率 (%)",
                    min_value=0.1,
                    max_value=50.0,
                    value=2.0,
                    step=0.1
                ) / 100

                mde = st.number_input(
                    "最小可檢測效應 MDE (%)",
                    min_value=5.0,
                    max_value=100.0,
                    value=20.0,
                    step=5.0
                ) / 100

                daily_traffic = st.number_input(
                    "預期每日訪客數",
                    min_value=100,
                    max_value=100000,
                    value=5000,
                    step=500
                )

            with col2:
                # 計算所需樣本數
                sample_size = calculate_mvt_sample_size(
                    num_combinations,
                    baseline_rate,
                    mde
                )

                total_sample = sample_size * num_combinations
                test_days = int(np.ceil(total_sample / daily_traffic))

                st.metric("每組所需樣本數", f"{sample_size:,}")
                st.metric("總樣本數", f"{total_sample:,}")
                st.metric("預估測試天數", f"{test_days} 天")

                if test_days > 30:
                    st.error(f"⚠️ 測試時間過長（{test_days} 天），建議簡化測試")
                elif test_days > 14:
                    st.warning(f"⚠️ 測試時間較長（{test_days} 天），需注意市場變化")

            st.session_state['mvt_baseline_rate'] = baseline_rate
            st.session_state['mvt_mde'] = mde
            st.session_state['mvt_daily_traffic'] = daily_traffic

            # 儲存組合
            st.session_state['mvt_combinations_df'] = combinations_df
            st.session_state['mvt_test_days'] = test_days

    with tab3:
        st.markdown("## 🤖 AI MVT 分析與建議")

        if 'mvt_variables' not in st.session_state:
            st.warning("請先在「設計變體」標籤中定義測試變數")
        else:
            variables = st.session_state['mvt_variables']
            num_combinations = st.session_state['mvt_combinations']
            baseline_rate = st.session_state.get('mvt_baseline_rate', 0.02)
            mde = st.session_state.get('mvt_mde', 0.2)
            stored_daily_traffic = st.session_state.get('mvt_daily_traffic', 5000)

            st.info(f"✅ 測試設定完成：{len(variables)} 個變數，{num_combinations} 個組合")

            col1, col2, col3 = st.columns(3)
            col1.metric('組合數', num_combinations)
            col2.metric('基準轉換率', f"{baseline_rate * 100:.2f}%")
            col3.metric('MDE', f"{mde * 100:.1f}%")

            ai_daily_traffic = st.number_input(
                '預期每日訪客數（用於 AI 計畫）',
                min_value=100,
                max_value=100000,
                value=int(stored_daily_traffic),
                step=500,
                key='mvt_ai_daily_traffic'
            )

            launch_calendar_input = st.text_area(
                '關鍵檔期 / Launch 限制（每行一項，可留空）',
                placeholder='例如：3/15 春季檔期起跑\n3/28 電商大促前必須凍結變更',
            )
            launch_calendar = [line.strip() for line in launch_calendar_input.splitlines() if line.strip()]

            default_template = {
                'best_practices': [
                    '每個因子維持 2-3 個層級以控制組合數',
                    '先採均等流量，依中期結果再調整分配',
                    '設定護欄指標，例如 CPA 與 CTR 低於歷史分位須暫停'
                ],
                'analysis_methods': [
                    '使用 ANOVA 檢驗主效應與交互效應',
                    '採用 Bonferroni 校正控制多重比較風險',
                    'MVT 結束後以增量提升量化投資報酬'
                ]
            }

            if st.button('🚀 啟動 MVTDesignAgent', type='primary'):
                agent = get_mvt_design_agent()
                if agent is None:
                    st.stop()

                with st.spinner('AI 正在設計 MVT 測試計畫...'):
                    try:
                        result = agent.design_sync(
                            df=df,
                            variables=variables,
                            test_objective=test_objective,
                            baseline_rate=baseline_rate,
                            minimum_detectable_effect=mde,
                            expected_daily_traffic=ai_daily_traffic,
                            design_template=default_template,
                            launch_calendar=launch_calendar or None,
                        )
                        st.session_state['mvt_design_result'] = result
                        st.session_state['mvt_design_generated_at'] = pd.Timestamp.now()
                        st.success('✅ 已生成完整的 MVT 測試計畫')
                    except Exception as exc:
                        st.error(f'❌ 生成失敗：{exc}')
                        import traceback
                        with st.expander('🔍 錯誤詳情'):
                            st.code(traceback.format_exc())

            design_result: MVTDesignResult | None = st.session_state.get('mvt_design_result')
            if design_result:
                generated_at = st.session_state.get('mvt_design_generated_at')
                if generated_at:
                    st.caption(f"最後更新時間：{generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
                render_mvt_design_result(design_result)
            else:
                st.info('設定完成後點擊按鈕，即可獲得完整的 MVT 設計計畫。')

    with tab4:
        st.markdown("## 📈 MVT 結果分析")

        if 'mvt_combinations_df' not in st.session_state:
            st.warning("請先在「組合預覽」標籤中生成測試組合")
        else:
            st.info("💡 這是模擬結果示範。實際測試中，請替換為真實數據。")

            # 模擬結果
            combinations_df = st.session_state['mvt_combinations_df'].copy()
            results_df = simulate_mvt_results(combinations_df)

            # 顯示結果表格
            st.markdown("### 📊 測試結果")

            # 排序並顯示
            results_df_sorted = results_df.sort_values('轉換率', ascending=False)

            st.dataframe(
                results_df_sorted[[
                    'ID',
                    *list(st.session_state['mvt_variables'].keys()),
                    '訪客數',
                    '轉換數',
                    '轉換率',
                    '信賴區間'
                ]],
                use_container_width=True,
                column_config={
                    '轉換率': st.column_config.NumberColumn('轉換率', format="%.2f%%")
                }
            )

            # 最佳組合
            st.markdown("---")
            st.markdown("### 🏆 最佳組合")

            best_combo = results_df_sorted.iloc[0]

            col1, col2 = st.columns(2)

            with col1:
                st.success(f"""
                **勝出組合**：{best_combo['ID']}

                **組合內容**：
                {chr(10).join([f"- **{k}**：{best_combo[k]}" for k in st.session_state['mvt_variables'].keys()])}
                """)

            with col2:
                st.metric("轉換率", f"{best_combo['轉換率']*100:.2f}%")
                st.metric("轉換數", f"{best_combo['轉換數']:.0f}")
                st.metric("訪客數", f"{best_combo['訪客數']:,.0f}")

            # 視覺化分析
            st.markdown("---")
            st.markdown("### 📊 視覺化分析")

            # 轉換率排名
            fig = px.bar(
                results_df_sorted.head(10),
                x='ID',
                y='轉換率',
                title='Top 10 組合轉換率',
                color='轉換率',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

            # 因子分析
            st.markdown("### 🔬 因子效應分析")

            variables = st.session_state['mvt_variables']
            effects = calculate_factorial_effects(results_df, variables)

            # 為每個變數創建效應圖
            for var_name, var_effects in effects.items():
                st.markdown(f"#### {var_name} 的主效應")

                effect_df = pd.DataFrame([
                    {'選項': k, '平均轉換率': v * 100}
                    for k, v in var_effects.items()
                ])

                fig = px.bar(
                    effect_df,
                    x='選項',
                    y='平均轉換率',
                    title=f'{var_name} 對轉換率的影響',
                    color='平均轉換率',
                    color_continuous_scale='RdYlGn'
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)

    # 頁面底部
    st.markdown("---")
    st.markdown("""
    ### 💡 MVT 最佳實踐

    **何時使用 MVT**：
    - ✅ 有足夠流量（每天 5000+ 訪客）
    - ✅ 想同時測試多個變數
    - ✅ 需要發現交互效應
    - ✅ 有時間進行較長測試（2-4 週）

    **何時避免 MVT**：
    - ❌ 流量不足（每天 < 1000 訪客）
    - ❌ 時間緊迫（< 1 週）
    - ❌ 變數太多（> 4 個）
    - ❌ 組合數過多（> 30 個）

    **MVT vs A/B 測試選擇**：
    ```
    流量充足 + 多變數 → MVT
    流量有限 + 單變數 → A/B 測試
    流量有限 + 多變數 → 序列 A/B 測試
    ```

    **成功關鍵**：
    1. 🎯 明確測試目標
    2. 📊 足夠樣本數（避免假陽性）
    3. ⏱️ 合理測試時長（至少 1-2 週）
    4. 🔬 嚴謹統計分析（Bonferroni 校正）
    5. 💡 可執行的洞察（找出最佳組合並推出）
    """)

if __name__ == "__main__":
    main()
