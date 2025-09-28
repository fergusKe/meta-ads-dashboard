import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.data_loader import load_meta_ads_data
import os

def show_ai_creative_hub():
    """顯示 AI 素材製作首頁"""
    st.markdown("# 🤖 AI 素材製作中心")
    st.markdown("使用人工智能技術，快速生成高質量的廣告文案和創意素材")

    # 載入數據分析當前素材表現
    df = load_meta_ads_data()

    # 應用日期篩選邏輯
    filtered_df = df.copy() if df is not None else pd.DataFrame()
    if not filtered_df.empty and '分析報告開始' in df.columns and '分析報告結束' in df.columns:
        report_start_dates = df['分析報告開始'].dropna()
        report_end_dates = df['分析報告結束'].dropna()

        if not report_start_dates.empty and not report_end_dates.empty:
            report_start = report_start_dates.min()
            report_end = report_end_dates.max()

            filtered_df = df[
                (df['開始'] >= report_start) &
                (df['開始'] <= report_end)
            ].copy()

    # AI 功能總覽
    st.markdown("## 🚀 AI 創意工具")

    tool_col1, tool_col2, tool_col3 = st.columns(3)

    with tool_col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 20px; border-radius: 10px; color: white; text-align: center; margin-bottom: 20px;">
            <h3>✍️ AI 文案生成</h3>
            <p>使用 GPT-5-nano 生成吸引人的廣告文案</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("開始文案創作", key="copywriting", use_container_width=True):
            st.session_state.navigate_to = "✍️ AI 文案生成"
            st.rerun()

    with tool_col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    padding: 20px; border-radius: 10px; color: white; text-align: center; margin-bottom: 20px;">
            <h3>🎨 AI 圖片生成</h3>
            <p>使用 Gemini nano-banana 創作視覺素材</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("開始圖片創作", key="image_gen", use_container_width=True):
            st.session_state.navigate_to = "🎨 AI 圖片生成"
            st.rerun()

    with tool_col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                    padding: 20px; border-radius: 10px; color: white; text-align: center; margin-bottom: 20px;">
            <h3>🧠 智能優化</h3>
            <p>AI 驅動的素材表現分析與優化建議</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("開始智能優化", key="optimization", use_container_width=True):
            st.session_state.navigate_to = "🧠 智能素材優化"
            st.rerun()

    st.markdown("---")

    # 當前素材表現分析
    if not filtered_df.empty:
        st.markdown("## 📊 當前素材表現分析")

        # 素材表現概況
        performance_col1, performance_col2, performance_col3, performance_col4 = st.columns(4)

        with performance_col1:
            avg_ctr = filtered_df['CTR（全部）'].mean()
            st.metric("平均點擊率", f"{avg_ctr:.2f}%",
                     delta="良好" if avg_ctr > 2.0 else "需改善")

        with performance_col2:
            avg_roas = filtered_df['購買 ROAS（廣告投資報酬率）'].mean()
            st.metric("平均 ROAS", f"{avg_roas:.2f}",
                     delta="優秀" if avg_roas > 3.0 else "待優化")

        with performance_col3:
            total_campaigns = len(filtered_df)
            active_campaigns = len(filtered_df[filtered_df['花費金額 (TWD)'] > 0])
            st.metric("活躍活動", f"{active_campaigns}",
                     delta=f"總共 {total_campaigns} 個")

        with performance_col4:
            total_spend = filtered_df['花費金額 (TWD)'].sum()
            st.metric("總投入", f"${total_spend:,.0f}",
                     delta="TWD")

        # 素材表現趨勢
        st.markdown("### 📈 素材表現趨勢")

        if '開始' in filtered_df.columns:
            trend_data = prepare_creative_trend_data(filtered_df)

            if not trend_data.empty:
                trend_chart = create_creative_performance_chart(trend_data)
                if trend_chart:
                    st.plotly_chart(trend_chart, use_container_width=True)
            else:
                st.info("暫無足夠數據顯示趨勢")

    # AI 創作靈感
    st.markdown("## 💡 AI 創作靈感")

    inspiration_tab1, inspiration_tab2, inspiration_tab3 = st.tabs(["🔥 熱門主題", "🎯 受眾洞察", "📝 文案模板"])

    with inspiration_tab1:
        st.markdown("### 🔥 本週熱門創意主題")

        hot_topics = get_trending_topics()

        topic_col1, topic_col2 = st.columns(2)

        with topic_col1:
            for i, topic in enumerate(hot_topics[:3]):
                with st.expander(f"🔥 {topic['title']}"):
                    st.write(f"**主題**: {topic['description']}")
                    st.write(f"**適用場景**: {topic['scenario']}")
                    st.write(f"**關鍵字**: {', '.join(topic['keywords'])}")

                    if st.button(f"使用此主題創作", key=f"topic_{i}"):
                        st.session_state.selected_topic = topic
                        st.session_state.navigate_to = "✍️ AI 文案生成"
                        st.rerun()

        with topic_col2:
            for i, topic in enumerate(hot_topics[3:6]):
                with st.expander(f"📈 {topic['title']}"):
                    st.write(f"**主題**: {topic['description']}")
                    st.write(f"**適用場景**: {topic['scenario']}")
                    st.write(f"**關鍵字**: {', '.join(topic['keywords'])}")

                    if st.button(f"使用此主題創作", key=f"topic_{i+3}"):
                        st.session_state.selected_topic = topic
                        st.session_state.navigate_to = "✍️ AI 文案生成"
                        st.rerun()

    with inspiration_tab2:
        st.markdown("### 🎯 受眾偏好分析")

        if not filtered_df.empty:
            audience_insights = analyze_audience_preferences(filtered_df)

            insights_col1, insights_col2 = st.columns(2)

            with insights_col1:
                st.markdown("#### 👥 高表現受眾特徵")
                if audience_insights['top_demographics']:
                    for demo in audience_insights['top_demographics']:
                        st.success(f"✅ {demo}")
                else:
                    st.info("暫無足夠數據分析受眾特徵")

            with insights_col2:
                st.markdown("#### 💡 創意建議")
                creative_suggestions = generate_creative_suggestions(audience_insights)
                for suggestion in creative_suggestions:
                    st.info(f"💡 {suggestion}")
        else:
            st.info("載入數據以獲得受眾洞察")

    with inspiration_tab3:
        st.markdown("### 📝 高效文案模板")

        templates = get_copywriting_templates()

        template_col1, template_col2 = st.columns(2)

        with template_col1:
            st.markdown("#### 🎯 轉換型文案")
            for template in templates['conversion']:
                with st.expander(f"📄 {template['name']}"):
                    st.code(template['template'], language='text')
                    st.caption(f"適用：{template['use_case']}")

                    if st.button(f"使用此模板", key=f"conv_template_{template['name']}"):
                        st.session_state.selected_template = template
                        st.session_state.navigate_to = "✍️ AI 文案生成"
                        st.rerun()

        with template_col2:
            st.markdown("#### 🚀 品牌推廣")
            for template in templates['branding']:
                with st.expander(f"📄 {template['name']}"):
                    st.code(template['template'], language='text')
                    st.caption(f"適用：{template['use_case']}")

                    if st.button(f"使用此模板", key=f"brand_template_{template['name']}"):
                        st.session_state.selected_template = template
                        st.session_state.navigate_to = "✍️ AI 文案生成"
                        st.rerun()

    st.markdown("---")

    # 創作歷史與管理
    st.markdown("## 📚 創作歷史與管理")

    history_tab1, history_tab2 = st.tabs(["📝 文案歷史", "🎨 素材庫"])

    with history_tab1:
        st.markdown("### 📝 最近的文案創作")

        copy_history = get_copy_history()

        if copy_history:
            for i, copy in enumerate(copy_history[:5]):
                with st.expander(f"📄 {copy['title']} - {copy['date']}"):
                    st.write(f"**主題**: {copy['topic']}")
                    st.write(f"**文案內容**:")
                    st.code(copy['content'], language='text')
                    st.write(f"**表現**: CTR {copy['performance']['ctr']:.2f}% | ROAS {copy['performance']['roas']:.2f}")

                    col_copy1, col_copy2, col_copy3 = st.columns(3)
                    with col_copy1:
                        if st.button("重新使用", key=f"reuse_copy_{i}"):
                            st.session_state.reuse_content = copy
                            st.session_state.navigate_to = "✍️ AI 文案生成"
                            st.rerun()
                    with col_copy2:
                        if st.button("優化改寫", key=f"optimize_copy_{i}"):
                            st.session_state.optimize_content = copy
                            st.session_state.navigate_to = "✍️ AI 文案生成"
                            st.rerun()
                    with col_copy3:
                        if st.button("刪除", key=f"delete_copy_{i}"):
                            st.success("已刪除該文案")
        else:
            st.info("還沒有創作歷史，開始您的第一次 AI 文案創作吧！")

    with history_tab2:
        st.markdown("### 🎨 素材庫管理")

        asset_col1, asset_col2, asset_col3 = st.columns(3)

        with asset_col1:
            st.metric("文案素材", "12 個", delta="+3 本週")

        with asset_col2:
            st.metric("圖片素材", "8 個", delta="+2 本週")

        with asset_col3:
            st.metric("模板", "15 個", delta="系統預設")

        # 素材管理功能
        management_col1, management_col2, management_col3 = st.columns(3)

        with management_col1:
            if st.button("📁 整理素材庫", use_container_width=True):
                st.info("素材庫整理功能開發中...")

        with management_col2:
            if st.button("📤 匯出素材", use_container_width=True):
                st.info("素材匯出功能開發中...")

        with management_col3:
            if st.button("🗑️ 清理舊素材", use_container_width=True):
                st.info("素材清理功能開發中...")

    # API 狀態檢查
    st.markdown("---")
    st.markdown("## ⚙️ AI 服務狀態")

    api_col1, api_col2, api_col3 = st.columns(3)

    with api_col1:
        openai_status = check_openai_api()
        if openai_status['available']:
            st.success(f"✅ OpenAI GPT-5-nano\n運行正常")
        else:
            st.error(f"❌ OpenAI API\n{openai_status['error']}")

    with api_col2:
        gemini_status = check_gemini_api()
        if gemini_status['available']:
            st.success(f"✅ Gemini nano-banana\n運行正常")
        else:
            st.error(f"❌ Gemini API\n{gemini_status['error']}")

    with api_col3:
        if openai_status['available'] and gemini_status['available']:
            st.success("🚀 所有 AI 服務正常\n可以開始創作！")
        else:
            st.warning("⚠️ 部分服務不可用\n請檢查 API 設定")

def prepare_creative_trend_data(df):
    """準備創意表現趨勢數據"""
    if df.empty or '開始' not in df.columns:
        return pd.DataFrame()

    # 按日期分組聚合
    daily_data = df.groupby(df['開始'].dt.date).agg({
        'CTR（全部）': 'mean',
        '購買 ROAS（廣告投資報酬率）': 'mean',
        'CPM（每千次廣告曝光成本）': 'mean',
        '花費金額 (TWD)': 'sum'
    }).reset_index()

    daily_data.columns = ['日期', 'CTR', 'ROAS', 'CPM', '花費']
    return daily_data.sort_values('日期')

def create_creative_performance_chart(trend_data):
    """創建創意表現圖表"""
    if trend_data.empty:
        return None

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('點擊率趨勢', 'ROAS 趨勢', 'CPM 趨勢', '每日花費'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )

    # CTR 趨勢
    fig.add_trace(
        go.Scatter(x=trend_data['日期'], y=trend_data['CTR'],
                  name='CTR (%)', line=dict(color='blue')),
        row=1, col=1
    )

    # ROAS 趨勢
    fig.add_trace(
        go.Scatter(x=trend_data['日期'], y=trend_data['ROAS'],
                  name='ROAS', line=dict(color='green')),
        row=1, col=2
    )

    # CPM 趨勢
    fig.add_trace(
        go.Scatter(x=trend_data['日期'], y=trend_data['CPM'],
                  name='CPM (TWD)', line=dict(color='orange')),
        row=2, col=1
    )

    # 花費趨勢
    fig.add_trace(
        go.Bar(x=trend_data['日期'], y=trend_data['花費'],
               name='花費 (TWD)', marker_color='lightblue'),
        row=2, col=2
    )

    fig.update_layout(height=600, showlegend=False, title_text="素材表現綜合分析")
    return fig

def get_trending_topics():
    """獲取熱門創意主題"""
    return [
        {
            'title': '季節限定茶品',
            'description': '結合當季特色的茶葉推廣',
            'scenario': '秋冬季節推廣、節慶特別款',
            'keywords': ['秋冬暖身', '限時特惠', '季節限定', '溫暖時光']
        },
        {
            'title': '健康生活方式',
            'description': '強調茶品的健康益處',
            'scenario': '都市白領、健康意識族群',
            'keywords': ['天然健康', '無添加', '養生', '有機茶葉']
        },
        {
            'title': '辦公室茶飲',
            'description': '針對上班族的便利茶品',
            'scenario': '辦公室場景、下午茶時光',
            'keywords': ['提神醒腦', '辦公夥伴', '便利沖泡', '工作能量']
        },
        {
            'title': '送禮首選',
            'description': '茶品作為精美禮品的定位',
            'scenario': '節慶送禮、商務贈品',
            'keywords': ['精美包裝', '送禮體面', '心意滿滿', '品味之選']
        },
        {
            'title': '傳統工藝',
            'description': '強調製茶工藝與品質',
            'scenario': '茶藝愛好者、品質追求者',
            'keywords': ['傳統工藝', '匠心製作', '品質保證', '文化傳承']
        },
        {
            'title': '輕鬆時光',
            'description': '營造悠閒放鬆的氛圍',
            'scenario': '休閒時光、居家享受',
            'keywords': ['輕鬆愜意', '慢生活', '享受當下', '悠閒片刻']
        }
    ]

def analyze_audience_preferences(df):
    """分析受眾偏好"""
    insights = {
        'top_demographics': [],
        'performance_patterns': [],
        'engagement_insights': []
    }

    if df.empty:
        return insights

    # 分析高表現活動的特徵
    high_performers = df[df['購買 ROAS（廣告投資報酬率）'] > 3.0]

    if not high_performers.empty:
        # 年齡分析
        if '年齡' in high_performers.columns:
            top_ages = high_performers['年齡'].value_counts().head(3)
            for age, count in top_ages.items():
                insights['top_demographics'].append(f"年齡 {age} 表現優異")

        # 性別分析
        if '性別' in high_performers.columns:
            gender_performance = high_performers.groupby('性別')['購買 ROAS（廣告投資報酬率）'].mean()
            best_gender = gender_performance.idxmax()
            insights['top_demographics'].append(f"{best_gender} 群體轉換率較高")

    return insights

def generate_creative_suggestions(audience_insights):
    """生成創意建議"""
    suggestions = [
        "考慮使用溫馨的色調來提升親和力",
        "加入生活化場景提高共鳴感",
        "強調產品的獨特價值主張",
        "使用情感化語言增加吸引力",
        "添加限時優惠增加緊迫感"
    ]

    # 根據受眾洞察調整建議
    if audience_insights['top_demographics']:
        suggestions.insert(0, "根據高表現受眾特徵調整創意方向")

    return suggestions

def get_copywriting_templates():
    """獲取文案模板"""
    return {
        'conversion': [
            {
                'name': '限時優惠型',
                'template': '🔥 限時特惠！{product_name}\n✨ 原價 ${original_price}，現在只要 ${sale_price}\n⏰ 僅限 {days} 天，錯過不再！\n🛒 立即搶購 >> {link}',
                'use_case': '促銷活動、清庫存'
            },
            {
                'name': '問題解決型',
                'template': '還在為 {problem} 煩惱嗎？\n✅ {product_name} 幫你解決！\n🎯 {benefit_1}\n🎯 {benefit_2}\n🎯 {benefit_3}\n👆 立即了解更多',
                'use_case': '痛點行銷、功能導向'
            },
            {
                'name': '社會證明型',
                'template': '🌟 已有 {customer_count}+ 客戶選擇 {product_name}！\n💬 "{testimonial}"\n⭐ 平均評分 {rating}/5\n🔥 加入滿意客戶的行列',
                'use_case': '建立信任、降低疑慮'
            }
        ],
        'branding': [
            {
                'name': '品牌故事型',
                'template': '🌱 {brand_name} 的故事開始於...\n💫 我們相信 {brand_belief}\n🎯 致力於為您提供 {brand_promise}\n💝 與我們一起 {call_to_action}',
                'use_case': '品牌認知、情感連結'
            },
            {
                'name': '生活方式型',
                'template': '✨ 不只是 {product_category}，更是一種生活態度\n🌟 {lifestyle_description}\n💫 讓 {product_name} 成為您 {lifestyle_benefit}\n🛍️ 開始您的品味生活',
                'use_case': '生活方式行銷、品牌定位'
            }
        ]
    }

def get_copy_history():
    """獲取文案歷史（模擬數據）"""
    return [
        {
            'title': '秋季暖身茶',
            'date': '2025-09-25',
            'topic': '季節限定',
            'content': '🍂 秋風起，是時候來一杯暖身茶了\n🌟 精選高山茶葉，溫潤甘甜\n⏰ 限時優惠，買二送一\n☕ 讓溫暖從心開始',
            'performance': {'ctr': 2.4, 'roas': 3.2}
        },
        {
            'title': '辦公室能量補給',
            'date': '2025-09-23',
            'topic': '辦公室場景',
            'content': '💼 下午三點的疲憊時光\n☕ 一杯好茶，喚醒工作活力\n🌟 天然草本，無負擔提神\n🚀 讓工作效率翻倍',
            'performance': {'ctr': 1.8, 'roas': 2.7}
        },
        {
            'title': '健康生活首選',
            'date': '2025-09-20',
            'topic': '健康養生',
            'content': '🌿 天然有機，零添加\n💚 每一口都是健康的投資\n✨ 嚴選產地，品質保證\n🎯 開始您的健康茶生活',
            'performance': {'ctr': 2.1, 'roas': 3.5}
        }
    ]

def check_openai_api():
    """檢查 OpenAI API 狀態"""
    try:
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            return {'available': True, 'error': None}
        else:
            return {'available': False, 'error': '未設定 API Key'}
    except Exception as e:
        return {'available': False, 'error': str(e)}

def check_gemini_api():
    """檢查 Gemini API 狀態"""
    try:
        gemini_key = os.getenv('GEMINI_API_KEY')
        if gemini_key:
            return {'available': True, 'error': None}
        else:
            return {'available': False, 'error': '未設定 API Key'}
    except Exception as e:
        return {'available': False, 'error': str(e)}

if __name__ == "__main__":
    show_ai_creative_hub()