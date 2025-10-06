# Pydantic AI 全面改造計畫

> 目標：將所有 AI 功能改用 Pydantic AI Agent，打造超強產品

## 📊 現況盤點

> 2025-10-05 進度更新：核心圖片體驗已全面切換為 **Gemini 2.5 Flash Image**（nano-banana），並由 Pydantic Agent 統一提示詞、分析與再生成流程，朝「超強產品」目標邁出第一里程碑。

### ✅ 已使用 Pydantic AI 的頁面（2個）

| 頁面 | Agent | 輸出結構 | 狀態 |
|------|-------|----------|------|
| 21_🤖_智能Agent巡檢.py | DailyCheckAgent | DailyCheckResult | ✅ 完成 |
| 22_💬_對話式投放助手.py | ConversationalAgent | AgentResponse | ✅ 完成 |

### 🚀 新增：核心圖片體驗全面升級（2025-10-05 完成）

| 頁面 | Agent | 角色 | 模型策略 |
|------|-------|------|----------|
| 13_🎨_AI圖片生成.py | ImagePromptAgent | 生成圖片提示詞 & 控制流程 | Gemini 2.5 Flash Image（固定）＋ GPT-5-nano（文字） |
| 25_📸_AI圖片分析與優化.py | ImageAnalysisAgent | 圖片評分、優化、再生成 | Gemini 2.5 Flash Image（分析＋再生成） |

**產品亮點**
- 單一模型策略：所有圖片生成、優化、分析皆使用 Gemini 2.5 Flash Image，品質一致、維運更簡單。
- Pydantic Agent 全面接管提示詞／分析結果，輸出結構化資料，方便後續串接儀表板與自動化流程。
- 內建 debug expander，快速檢視 Gemini 回應，加速除錯與最佳化。
- README、使用指南與開發文件已同步更新，團隊與使用者隨時掌握最新體驗。

### ✅ 已完成的 Agent 改造

| 頁面 | Agent | 狀態 |
|------|-------|------|
| 5_🎨_素材成效分析.py | CreativePerformanceAgent | ✅ 已完成 |
| 6_📈_廣告品質評分.py | QualityScoreAgent | ✅ 已完成 |
| 7_🔄_轉換漏斗優化.py | FunnelAnalysisAgent | ✅ 已完成 |
| 10_⚡_即時優化建議.py | OptimizationAgent | ✅ 已完成 |
| 12_✍️_AI文案生成.py | CopywritingAgent | ✅ 已完成 |
| 13_🎨_AI圖片生成.py | ImagePromptAgent | ✅ 已完成 |
| 14_🧠_智能素材優化.py | CreativeOptimizationAgent | ✅ 已完成 |
| 17_👥_受眾擴展建議.py | AudienceExpansionAgent | ✅ 已完成 |
| 18_💰_預算優化建議.py | BudgetOptimizationAgent | ✅ 已完成 |
| 19_📄_自動化報告.py | ReportGenerationAgent | ✅ 已完成 |
| 20_🧪_AB測試設計.py | ABTestDesignAgent | ✅ 已完成 |
| 23_🌐_競爭對手分析.py | CompetitorAnalysisAgent | ✅ 已完成 |
| 25_📸_AI圖片分析與優化.py | ImageAnalysisAgent | ✅ 已完成 |

### 🧑‍💻 進行中的改造任務

| # | 任務 | Agent | 進度 |
|---|------|-------|------|
| 1 | 24_🧬_多變量測試優化.py | MVTDesignAgent | ✅ 已完成 |
| 2 | 15_🎯_智能投放策略.py | StrategyAgent | ✅ 已完成 |

### 🧭 下一波優先級
- Phase 2：完成 MVTDesignAgent（頁面 24）與 StrategyAgent（頁面 15）串接。
- Phase 3：素材／品質／受眾類頁面逐步轉換。


### ❌ 尚未使用 Pydantic AI 的頁面（17個）

#### 優先級 1：核心生成功能（必須改造）

| # | 頁面 | 主要功能 | 需要的 Agent | 優先級 |
|---|------|----------|--------------|--------|
| 1 | 12_✍️_AI文案生成.py | 生成廣告文案 | CopywritingAgent | ✅ 完成 |
| 2 | 13_🎨_AI圖片生成.py | 生成圖片提示詞 | ImagePromptAgent | ✅ 完成 |
| 3 | 25_📸_AI圖片分析與優化.py | 分析圖片+生成優化建議 | ImageAnalysisAgent | ✅ 完成 |
| 4 | 14_🧠_智能素材優化.py | 素材優化建議 | CreativeOptimizationAgent | 🟡 高 |

#### 優先級 2：分析與建議功能（應該改造）

| # | 頁面 | 主要功能 | 需要的 Agent | 優先級 |
|---|------|----------|--------------|--------|
| 5 | 10_⚡_即時優化建議.py | 緊急問題分析+優化建議 | OptimizationAgent | ✅ 完成 |
| 6 | 7_🔄_轉換漏斗優化.py | 漏斗分析+瓶頸識別 | FunnelAnalysisAgent | ✅ 完成 |
| 7 | 5_🎨_素材成效分析.py | 素材表現分析 | CreativePerformanceAgent | ✅ 完成 |
| 8 | 6_📈_廣告品質評分.py | 品質評分+改善計畫 | QualityScoreAgent | ✅ 完成 |
| 9 | 17_👥_受眾擴展建議.py | 受眾推薦 | AudienceExpansionAgent | ✅ 完成 |
| 10 | 18_💰_預算優化建議.py | 預算優化 | BudgetOptimizationAgent | ✅ 完成 |

#### 優先級 3：進階功能（可以改造）

| # | 頁面 | 主要功能 | 需要的 Agent | 優先級 |
|---|------|----------|--------------|--------|
| 11 | 19_📄_自動化報告.py | 週報/月報生成 | ReportGenerationAgent | ✅ 完成 |
| 12 | 20_🧪_AB測試設計.py | A/B測試設計 | ABTestDesignAgent | ✅ 完成 |
| 13 | 23_🌐_競爭對手分析.py | 競品分析 | CompetitorAnalysisAgent | ✅ 完成 |
| 14 | 24_🧬_多變量測試優化.py | MVT 設計 | MVTDesignAgent | ✅ 完成 |
| 15 | 15_🎯_智能投放策略.py | 投放策略建議 | StrategyAgent | ✅ 完成 |

#### 優先級 4：不需要 Agent 的頁面（7個）

| 頁面 | 原因 |
|------|------|
| 1_📊_整體效能儀表板.py | 純數據展示 |
| 2_🎯_活動分析.py | 純數據展示 |
| 3_👥_受眾洞察.py | 純數據展示 |
| 4_💰_ROI分析.py | 純數據展示 |
| 8_📋_詳細數據表格.py | 純數據表格 |
| 9_📈_趨勢分析.py | 純圖表展示 |
| 11_🤖_AI素材製作首頁.py | 導航頁面 |
| 16_🧠_RAG知識庫管理.py | 工具頁面 |

---

## 🎯 改造策略

### Phase 1：核心生成功能（第1週）

#### 1. CopywritingAgent - 文案生成 Agent

**結構化輸出**：
```python
class AdCopyVariant(BaseModel):
    headline: str = Field(description="廣告標題（25-40字）")
    primary_text: str = Field(description="主要文案（90-125字）")
    cta: str = Field(description="行動呼籲")
    tone: str = Field(description="語氣風格")
    target_audience: str = Field(description="目標受眾")
    key_message: str = Field(description="核心訊息")

class CopywritingResult(BaseModel):
    variants: list[AdCopyVariant] = Field(description="3-5個文案變體")
    strategy_explanation: str = Field(description="策略說明")
    ab_test_suggestions: list[str] = Field(description="A/B測試建議")
    optimization_tips: list[str] = Field(description="優化建議")
```

**Agent Tools**：
- `get_top_performing_copy()` - 獲取高效文案範例
- `get_audience_insights()` - 獲取受眾洞察
- `get_brand_voice()` - 獲取品牌語調
- `analyze_competitor_copy()` - 分析競品文案（RAG）

---

#### 2. ImagePromptAgent - 圖片提示詞生成 Agent

**結構化輸出**：
```python
class ImagePrompt(BaseModel):
    main_prompt: str = Field(description="主要提示詞（英文）")
    chinese_description: str = Field(description="中文說明")
    style_keywords: list[str] = Field(description="風格關鍵字")
    composition_tips: list[str] = Field(description="構圖建議")
    color_palette: list[str] = Field(description="建議色彩")

class ImageGenerationResult(BaseModel):
    prompts: list[ImagePrompt] = Field(description="3個提示詞變體")
    brand_alignment_score: int = Field(ge=0, le=100, description="品牌一致性分數")
    ad_suitability_score: int = Field(ge=0, le=100, description="廣告適配性分數")
    rationale: str = Field(description="設計理念說明")
```

**Agent Tools**：
- `get_brand_visual_guidelines()` - 獲取品牌視覺規範
- `get_top_performing_images()` - 獲取高效圖片特徵
- `analyze_image_trends()` - 分析圖片趨勢（RAG）
- `optimize_for_platform()` - 平台優化建議

---

#### 3. ImageAnalysisAgent - 圖片分析 Agent

**結構化輸出**：
```python
class ImageAnalysisScores(BaseModel):
    visual_appeal: int = Field(ge=1, le=10)
    composition: int = Field(ge=1, le=10)
    color_usage: int = Field(ge=1, le=10)
    text_readability: int = Field(ge=1, le=10)
    brand_consistency: int = Field(ge=1, le=10)
    ad_suitability: int = Field(ge=1, le=10)

class ImageAnalysisResult(BaseModel):
    scores: ImageAnalysisScores
    overall_score: float = Field(ge=0, le=10)
    strengths: list[str] = Field(min_length=3, max_length=5)
    weaknesses: list[str] = Field(min_length=3, max_length=5)
    detailed_analysis: dict[str, str]
    optimization_suggestions: list[str] = Field(min_length=5, max_length=7)
    is_suitable_for_ads: bool
    suitability_reason: str
    target_audience_recommendation: str
```

**Agent Tools**：
- `analyze_image_with_gemini()` - Gemini 圖片分析
- `get_platform_guidelines()` - 獲取平台規範
- `get_similar_high_performing_images()` - 相似高效圖片（RAG）
- `generate_optimization_prompt()` - 生成優化提示詞

---

#### 4. CreativeOptimizationAgent - 素材優化 Agent

**結構化輸出**：
```python
class CreativeOptimization(BaseModel):
    element_type: str = Field(description="素材元素類型")
    current_performance: str = Field(description="當前表現")
    optimization_action: str = Field(description="優化動作")
    expected_improvement: str = Field(description="預期改善")
    priority: str = Field(description="優先級")

class CreativeOptimizationResult(BaseModel):
    optimizations: list[CreativeOptimization]
    quick_wins: list[str] = Field(description="快速見效的改進")
    long_term_strategy: str = Field(description="長期策略")
    ab_test_plan: list[str] = Field(description="A/B測試計畫")
```

---

### Phase 2：分析與建議功能（第2週）

#### 5. OptimizationAgent - 即時優化建議 Agent

**結構化輸出**：
```python
from typing import Literal
from pydantic import BaseModel, Field

class OptimizationIssue(BaseModel):
    metric: str = Field(description="受影響的指標")
    current_value: float = Field(description="目前值")
    baseline_value: float = Field(description="對照組/基準值")
    severity: Literal["高", "中", "低"] = Field(description="嚴重程度")
    root_cause: str = Field(description="可能原因")
    recommended_action: str = Field(description="建議動作")
    expected_impact: str = Field(description="預期改善幅度")
    time_to_impact_days: int = Field(description="預估見效天數")

class OptimizationResult(BaseModel):
    summary: str = Field(description="整體狀況摘要")
    prioritized_issues: list[OptimizationIssue] = Field(description="優先處理項目")
    quick_actions: list[str] = Field(description="立即行動清單")
    follow_up_checks: list[str] = Field(description="後續追蹤重點")
    monitoring_suggestions: list[str] = Field(description="監控建議")
```

**依賴注入**：
- `performance_df: pd.DataFrame` - 近 7 日主要 KPI 與分層數據
- `budget_df: pd.DataFrame` - 預算與實際花費紀錄
- `alert_rules: dict` - 自訂化告警規則與閾值

**Agent Tools**：
- `get_recent_performance()` - 取得最新成效指標
- `detect_anomaly_segments()` - 自動標記異常受眾/素材
- `simulate_budget_shift()` - 模擬預算移轉對 KPI 的影響

**落地重點**：
- 給出可直接在 Ads Manager 操作的步驟與調整幅度
- 融合 Slack 告警，確保異常事件第一時間被追蹤

---

#### 6. FunnelAnalysisAgent - 轉換漏斗分析 Agent

**結構化輸出**：
```python
from typing import Literal
from pydantic import BaseModel, Field

class FunnelStageBreakdown(BaseModel):
    stage: str = Field(description="漏斗階段")
    conversion_rate: float = Field(description="轉換率")
    drop_rate: float = Field(description="流失率")
    avg_time_spent: float = Field(description="平均停留時間(秒)")
    key_insights: list[str] = Field(description="洞察重點")

class FunnelAlert(BaseModel):
    stage: str = Field(description="受影響階段")
    severity: Literal["高", "中", "低"] = Field(description="嚴重程度")
    issue: str = Field(description="問題描述")
    recommendation: str = Field(description="建議行動")

class FunnelAnalysisResult(BaseModel):
    stages: list[FunnelStageBreakdown] = Field(description="各階段表現")
    critical_alerts: list[FunnelAlert] = Field(description="緊急警示")
    optimization_playbook: list[str] = Field(description="最佳化劇本")
    experiment_ideas: list[str] = Field(description="實驗建議")
    data_quality_flags: list[str] = Field(description="資料品質提醒")
```

**依賴注入**：
- `funnel_df: pd.DataFrame` - 事件轉換與漏斗指標
- `benchmark_df: pd.DataFrame` - 產業/歷史基準
- `event_mapping: dict` - 事件對應設定

**Agent Tools**：
- `get_funnel_metrics()` - 聚合同階段成效
- `compare_with_benchmark()` - 與基準比較差異
- `suggest_stage_actions()` - 依階段輸出改善建議

**落地重點**：
- 明確標註瓶頸階段與預估改善幅度
- 與漏斗儀表板互動，支援一鍵帶入建議

---

#### 7. CreativePerformanceAgent - 素材表現分析 Agent

**結構化輸出**：
```python
from pydantic import BaseModel, Field

class AssetPerformance(BaseModel):
    asset_id: str = Field(description="素材 ID")
    asset_name: str = Field(description="素材名稱")
    format: str = Field(description="素材格式")
    spend: float = Field(description="花費")
    cpa: float = Field(description="每轉換成本")
    roas: float = Field(description="ROAS")
    learning_stage: str = Field(description="學習階段")
    insights: list[str] = Field(description="洞察備註")

class CreativePerformanceResult(BaseModel):
    leaderboard: list[AssetPerformance] = Field(description="表現最佳素材")
    underperformers: list[AssetPerformance] = Field(description="待優化素材")
    optimization_suggestions: list[str] = Field(description="優化動作建議")
    testing_opportunities: list[str] = Field(description="待測試機會")
    sunset_recommendations: list[str] = Field(description="建議下架素材")
```

**依賴注入**：
- `creative_df: pd.DataFrame` - 素材層級成效
- `asset_library: dict` - Meta 素材庫補充資料
- `performance_thresholds: dict` - KPI 閾值設定

**Agent Tools**：
- `rank_creatives()` - 依 KPI 排序素材
- `detect_fatigue_signals()` - 辨識疲乏訊號
- `recommend_new_tests()` - 提出測試主題

**落地重點**：
- 術語對應投手日常（如 CPR、CTR、Learning Limited）
- 產出可直接匯出成素材週報的欄位

---

#### 8. QualityScoreAgent - 品質評分 Agent

**結構化輸出**：
```python
from typing import Literal
from pydantic import BaseModel, Field

class QualityDimension(BaseModel):
    dimension: str = Field(description="品質面向")
    score: int = Field(ge=0, le=100, description="得分")
    rationale: str = Field(description="評分理由")
    recommended_actions: list[str] = Field(description="改善建議")

class QualityScoreResult(BaseModel):
    overall_score: int = Field(ge=0, le=100, description="總分")
    dimensions: list[QualityDimension] = Field(description="面向細節")
    compliance_risks: list[str] = Field(description="可能違規風險")
    audit_trail: list[str] = Field(description="稽核紀錄")
    improvement_plan: list[str] = Field(description="30 日改善計畫")
```

**依賴注入**：
- `quality_rules: dict` - Meta 品質規則/最佳實務
- `policy_updates: list[str]` - 最新政策更新
- `historical_scores: pd.DataFrame` - 過往評分紀錄

**Agent Tools**：
- `score_creative_quality()` - 評估素材與文案品質
- `check_policy_compliance()` - 政策與稽核檢查
- `generate_improvement_plan()` - 自動生成改善計畫

**落地重點**：
- 產出可同步至品質儀表板的 JSON 結構
- 為每個低分項目提供具體修正建議與例句

---

#### 9. AudienceExpansionAgent - 受眾擴展 Agent

**結構化輸出**：
```python
from pydantic import BaseModel, Field

class AudienceExpansionIdea(BaseModel):
    segment_name: str = Field(description="新受眾名稱")
    base_audience: str = Field(description="來源受眾")
    lookalike_seed: str = Field(description="類似受眾種子")
    expected_reach: int = Field(description="預估觸及人數")
    estimated_cpa: float = Field(description="預估 CPA")
    rationale: str = Field(description="推薦理由")
    activation_steps: list[str] = Field(description="啟動步驟")

class AudienceExpansionResult(BaseModel):
    prioritized_segments: list[AudienceExpansionIdea] = Field(description="優先擴展清單")
    testing_matrix: list[str] = Field(description="測試矩陣")
    creative_requirements: list[str] = Field(description="素材需求")
    measurement_plan: list[str] = Field(description="衡量計畫")
    risk_notes: list[str] = Field(description="風險提醒")
```

**依賴注入**：
- `audience_insights_df: pd.DataFrame` - 受眾洞察
- `crm_segments: pd.DataFrame` - 自有名單分群
- `pixel_events: dict` - 轉換事件資料

**Agent Tools**：
- `find_adjacent_segments()` - 挖掘相鄰市場
- `suggest_lookalike_configs()` - 推薦類似受眾設定
- `estimate_reach_and_cpa()` - 預估觸及與成本

**落地重點**：
- 每項建議附上啟動步驟與設定參數
- 輸出格式可直接匯入 audience backlog

---

#### 10. BudgetOptimizationAgent - 預算優化 Agent

**結構化輸出**：
```python
from typing import Literal
from pydantic import BaseModel, Field

class BudgetShiftRecommendation(BaseModel):
    campaign_id: str = Field(description="活動 ID")
    campaign_name: str = Field(description="活動名稱")
    current_daily_budget: float = Field(description="目前日預算")
    proposed_daily_budget: float = Field(description="建議日預算")
    reason: str = Field(description="調整原因")
    expected_roi_delta: float = Field(description="預估 ROI 變化")
    risk_level: Literal["高", "中", "低"] = Field(description="風險等級")

class BudgetOptimizationResult(BaseModel):
    summary: str = Field(description="整體預算建議摘要")
    reallocation_plan: list[BudgetShiftRecommendation] = Field(description="預算重新配置方案")
    pacing_alerts: list[str] = Field(description="投放節奏提醒")
    guardrails: list[str] = Field(description="守門原則")
    follow_up_actions: list[str] = Field(description="後續追蹤")
```

**依賴注入**：
- `spend_df: pd.DataFrame` - 實際花費與 pacing
- `roi_targets: dict` - 財務目標與上限
- `finance_constraints: dict` - 財務/法務限制

**Agent Tools**：
- `analyze_budget_efficiency()` - 評估投資效率
- `recommend_shift_plan()` - 計算預算移轉方案
- `check_guardrails()` - 驗證是否符合守門規則

**落地重點**：
- 自動產出可貼到財務審批的摘要與數據表
- 支援將建議同步到 pacing 監控模組

---

### Phase 3：進階功能（第3週）

#### 11. ReportGenerationAgent - 報告生成 Agent

**結構化輸出**：
```python
from pydantic import BaseModel, Field

class ReportSection(BaseModel):
    title: str = Field(description="章節標題")
    summary: str = Field(description="章節摘要")
    highlights: list[str] = Field(description="重點 bullet")
    supporting_charts: list[str] = Field(description="支援圖表 ID")

class ReportGenerationResult(BaseModel):
    period: str = Field(description="報告週期")
    executive_summary: str = Field(description="主管摘要")
    key_metrics: dict[str, float] = Field(description="核心 KPI")
    sections: list[ReportSection] = Field(description="報告章節")
    next_steps: list[str] = Field(description="後續行動")
    appendix_links: list[str] = Field(description="附錄連結")
```

**依賴注入**：
- `metric_store: dict` - KPI 儲存服務
- `chart_service: Any` - 圖表生成器 (interface)
- `notes_repo: list[str]` - 重要事件紀錄

**Agent Tools**：
- `fetch_metric_snapshot()` - 取得 KPI snapshot
- `compile_highlights()` - 萃取亮點
- `generate_chart_specs()` - 生出圖表設定

**落地重點**：
- 支援同時輸出 Markdown 與 PDF 模板
- 為高層報表加入一句話洞察與風險提醒

---

#### 12. ABTestDesignAgent - A/B 測試設計 Agent

**結構化輸出**：
```python
from pydantic import BaseModel, Field

class Hypothesis(BaseModel):
    statement: str = Field(description="假設敘述")
    metrics: list[str] = Field(description="衡量指標")
    success_criteria: dict[str, float] = Field(description="成功門檻")

class ExperimentPlan(BaseModel):
    name: str = Field(description="實驗名稱")
    hypothesis: Hypothesis = Field(description="實驗假設")
    target_audience: str = Field(description="鎖定受眾")
    required_sample_size: int = Field(description="樣本數")
    duration_days: int = Field(description="預估天數")
    variants: list[str] = Field(description="測試版本")
    risk_mitigation: list[str] = Field(description="風險控管")

class ABTestDesignResult(BaseModel):
    recommended_tests: list[ExperimentPlan] = Field(description="推薦實驗")
    prioritization_matrix: list[str] = Field(description="優先級分析")
    implementation_checklist: list[str] = Field(description="落地檢查表")
    data_requirements: list[str] = Field(description="資料需求")
```

**依賴注入**：
- `historical_tests: pd.DataFrame` - 過往實驗紀錄
- `sample_size_calculator: Any` - 樣本計算服務
- `experiment_calendar: list[str]` - 既定實驗排程

**Agent Tools**：
- `calculate_sample_size()` - 自動估算樣本數
- `identify_high_impact_tests()` - 找出高影響假設
- `generate_ga_tracking_plan()` - 動態生成追蹤需求

**落地重點**：
- 報告需包含效應量與統計檢定設定
- 與實驗看板整合，支援一鍵建立 Jira 任務

---

#### 13. CompetitorAnalysisAgent - 競品分析 Agent

**結構化輸出**：
```python
from pydantic import BaseModel, Field

class CompetitorInsight(BaseModel):
    competitor: str = Field(description="競品名稱")
    campaign_theme: str = Field(description="活動主題")
    spend_tier: str = Field(description="預估投放層級")
    creative_highlights: list[str] = Field(description="創意重點")
    tactical_moves: list[str] = Field(description="策略動作")
    risk_assessment: str = Field(description="對我方風險")

class CompetitorAnalysisResult(BaseModel):
    market_summary: str = Field(description="市場總覽")
    competitor_insights: list[CompetitorInsight] = Field(description="競品洞察")
    opportunity_gaps: list[str] = Field(description="機會缺口")
    defensive_actions: list[str] = Field(description="防禦策略")
    alerts: list[str] = Field(description="即時提醒")
```

**依賴注入**：
- `ad_library_client: Any` - Meta Ad Library 抓取器
- `creative_classifier: Any` - 創意分類模型
- `market_notes: list[str]` - BD/銷售回饋

**Agent Tools**：
- `fetch_competitor_ads()` - 取得競品投放
- `cluster_creative_themes()` - 聚類創意主題
- `highlight_threats()` - 標出潛在威脅

**落地重點**：
- 每周自動生成競品快訊可推送至 Slack
- 保留引用來源與素材截圖連結以利查核

---

#### 14. MVTDesignAgent - 多變量測試設計 Agent

**結構化輸出**：
```python
from pydantic import BaseModel, Field

class FactorLevel(BaseModel):
    factor: str = Field(description="實驗因子")
    levels: list[str] = Field(description="測試層級")
    rationale: str = Field(description="選擇理由")

class MVTPlan(BaseModel):
    hypothesis: str = Field(description="核心假設")
    factors: list[FactorLevel] = Field(description="實驗因子設定")
    primary_metric: str = Field(description="主要指標")
    interaction_focus: list[str] = Field(description="關注交互作用")
    required_runs: int = Field(description="所需組合數")
    phased_rollout: list[str] = Field(description="分階段上線")

class MVTDesignResult(BaseModel):
    plan: MVTPlan = Field(description="完整實驗計畫")
    data_collection_plan: list[str] = Field(description="資料蒐集需求")
    analysis_framework: list[str] = Field(description="分析方法")
    risk_controls: list[str] = Field(description="風險控管")
    stakeholders: list[str] = Field(description="利害關係人")
```

**依賴注入**：
- `design_template: dict` - 既有 MVT 模板
- `analytics_toolkit: Any` - 統計分析工具
- `launch_calendar: list[str]` - 上線時程限制

**Agent Tools**：
- `optimize_factor_levels()` - 建議最佳層級組合
- `estimate_runtime()` - 預估實驗天數
- `generate_risk_matrix()` - 風險評估

**落地重點**：
- 輸出包含 GA4/Meta Pixel 需要的事件設定
- 協助制定 phased rollout 與 rollback 計畫

---

#### 15. StrategyAgent - 投放策略 Agent

**結構化輸出**：
```python
from pydantic import BaseModel, Field

class StrategicPillar(BaseModel):
    name: str = Field(description="策略主軸")
    objective: str = Field(description="目標")
    key_results: list[str] = Field(description="關鍵成果指標")
    tactical_moves: list[str] = Field(description="戰術建議")

class StrategyAgentResult(BaseModel):
    horizon: str = Field(description="規劃期間")
    strategic_pillars: list[StrategicPillar] = Field(description="策略主軸清單")
    budget_allocation: dict[str, float] = Field(description="預算分配建議")
    audience_strategy: list[str] = Field(description="受眾策略")
    creative_strategy: list[str] = Field(description="創意策略")
    measurement_plan: list[str] = Field(description="衡量計畫")
    executive_summary: str = Field(description="主管摘要")
```

**依賴注入**：
- `business_goals: dict` - 商業目標與 KPI
- `market_forecast: dict` - 市場預測與季節性
- `inventory_constraints: dict` - 供應/預算限制

**Agent Tools**：
- `synthesize_cross_page_insights()` - 彙整各頁面洞察
- `build_budget_mix_model()` - 生成預算配置模型
- `draft_exec_brief()` - 產出主管簡報摘要

**落地重點**：
- 幫助制定季度 OKR 與戰術計畫
- 預設輸出含 Google Slides 範本填充資料

---

## 🏗️ 統一 Agent 架構

### 標準 Agent 結構

```python
# utils/agents/{agent_name}.py

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from dataclasses import dataclass
import pandas as pd

# 1. 定義結構化輸出
class {Agent}Result(BaseModel):
    """Agent 輸出結果（完全型別安全）"""
    # ... fields

# 2. 定義依賴注入
@dataclass
class {Agent}Deps:
    """Agent 依賴"""
    df: pd.DataFrame
    # ... other deps

# 3. Agent 類別
class {Agent}:
    def __init__(self):
        self.agent = Agent(
            'openai:gpt-5-nano',
            output_type={Agent}Result,
            deps_type={Agent}Deps,
            system_prompt=self._get_system_prompt()
        )
        self._register_tools()

    def _get_system_prompt(self) -> str:
        """系統提示詞"""
        return """..."""

    def _register_tools(self):
        """註冊工具"""
        @self.agent.tool
        def tool_name(ctx: RunContext[{Agent}Deps]) -> dict:
            """工具說明"""
            # ... implementation

    async def run(self, **kwargs) -> {Agent}Result:
        """執行 Agent"""
        # ... implementation

    def run_sync(self, **kwargs) -> {Agent}Result:
        """同步版本（用於 Streamlit）"""
        import asyncio
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(self.run(**kwargs))
```

---

## 📋 實作檢查清單

### Phase 1（本週）

- [x] 1. 創建 `CopywritingAgent` (utils/agents/copywriting_agent.py)
- [x] 2. 修改 `12_✍️_AI文案生成.py` 使用新 Agent
- [x] 3. 創建 `ImagePromptAgent` (utils/agents/image_prompt_agent.py)
- [x] 4. 修改 `13_🎨_AI圖片生成.py` 使用新 Agent
- [x] 5. 創建 `ImageAnalysisAgent` (utils/agents/image_analysis_agent.py)
- [x] 6. 修改 `25_📸_AI圖片分析與優化.py` 使用新 Agent
- [x] 7. 創建 `CreativeOptimizationAgent` (utils/agents/creative_optimization_agent.py)
- [x] 8. 修改 `14_🧠_智能素材優化.py` 使用新 Agent

### Phase 2（下週）

- [ ] 9-14. 創建並整合其他分析類 Agents

### Phase 3（第三週）

- [ ] 15-19. 創建並整合進階功能 Agents

---

## 🔍 測試與驗證策略
- 單元測試：針對各 Agent 的 Pydantic 模型建立 `pytest` 驗證，確保欄位與類型不被破壞
- 合成資料集：為主要情境產製固定範本，執行快照測試比較輸出差異
- Streamlit 端對端檢查：透過 `pytest-streamlit` 或 Playwright 腳本驗證互動流程
- 真實樣本抽驗：每週抽樣 5 組廣告帳戶，由投手與 PM 共同復核建議品質

## 📡 部署與觀測
- 將所有 Agent run 透過 Logfire 設定 `run_id`，串接儀表板監控成功率與耗時
- 於 `utils/telemetry.py` 提供統一封裝，記錄 prompt、tools、輸出摘要
- 與 Slack `#meta-ai-alert` 頻道整合，異常時自動推播告警
- 每月重新校準 Prompt Registry，維持提示詞與版本控管

## ⚠️ 風險與緩解
- LLM 漂移：建立基準測試集，模型或 Prompt 更新前後跑對照
- 資料缺漏：若必要欄位缺失，Agent 需回傳結構化錯誤並提示資料來源
- 效能壓力：大量併發時改用批次排程，並啟用結果快取
- 跨頁依賴：透過 deps 類別顯式宣告需求，避免隱性耦合

## 📈 成效追蹤指標
- Agent 覆蓋率：已完成 Pydantic 改造的頁面 / 需改造頁面
- 推薦採納率：投手實際採納建議的比例，來源串接回報模組
- 平均回應時間：Streamlit 呼叫 Agent 的 P95 延遲
- 節省作業時間：以問卷與時數紀錄估算人力節省
- 使用者滿意度：每季收集 NPS/CSAT，追蹤走勢

## 🤝 協作與溝通節奏
- 每日 15 分 stand-up，追蹤 Phase 任務進度與阻礙
- 週四 Demo，向利害關係人展示最新 Agent 輸出與回饋
- 雙週 Cross-team Sync，整合產品、數據、投手需求 
- Notion PRD 與 GitHub Projects 同步更新，確保資訊透明


---

## 🎁 使用 Pydantic AI 的好處

### 1. 型別安全
- ✅ 編譯時就能發現錯誤
- ✅ IDE 自動補全
- ✅ 清晰的資料結構

### 2. 結構化輸出
- ✅ 保證輸出格式一致
- ✅ 自動驗證數據
- ✅ 易於測試和維護

### 3. 工具整合
- ✅ Agent 可以調用自定義工具
- ✅ 工具有完整的型別提示
- ✅ 依賴注入模式清晰

### 4. 可觀測性
- ✅ 整合 Logfire（可選）
- ✅ 追蹤 Agent 執行過程
- ✅ 調試更容易

### 5. 成本優化
- ✅ 精確的 prompt 控制
- ✅ 結構化輸出減少 token
- ✅ 更好的快取策略

---

## 🧩 核心資料與依賴地圖

| Agent 類別 | 主要資料來源 | 關聯工具/服務 | Owner | 更新頻率 |
|------------|--------------|---------------|-------|-----------|
| 生成功能（Copywriting/Image 系列） | BigQuery `ad_creatives`, 品牌語調 Notion, 成效回饋 API | Gemini 2.5 Flash Image, OpenAI GPT-5 Nano | AI 團隊（Mia） | 每日 ETL + 每週語調回顧 |
| 即時優化（Optimization/Funnel） | Ads Manager Insights Export, 零時差轉換事件 Kafka Stream | anomaly-detector Lambda, Slack Bot | 數據工程（Leo） | 每小時增量 |
| 素材分析（CreativePerformance/QualityScore） | Meta Asset Library Sync, 历史素材 ROAS 表 | Feature Store, S3 素材倉儲 | 投手 Ops（Joy） | 每日同步 |
| 受眾與預算（AudienceExpansion/Budget） | CRM Segment Warehouse, 財務預算表, Pixel 行為 | Snowflake share, 財務審批 webhook | CRM（Ray） & 財務（Ivy） | 每週 |
| 策略與報告（Report/Strategy/MVT/ABTest/Competitor） | KPI Data Mart, 市場情報 Airtable, BD notes | Chart Service, GA4 Export, Ad Library crawler | 產品（Ken） | 週報 + ad-hoc |

> **提醒**：所有 DataFrame 由 `utils/data_access.py` 提供統一介面，Agent 建構子僅接觸經清理的資料集，避免重複實作。

## 🛠️ 開發與上線流程
- 需求規格：由產品 + 投手 co-write Agent PRD，確認輸入、輸出、工具清單
- 提示詞設計：AI 團隊於 Prompt Registry 建立初版 system/prompt 模板，並標註觀測指標
- 原型開發：工程師依 `utils/agents` 樣板實作，撰寫最小測試（模型驗證 + 工具 mock）
- 封閉測試：於 staging Streamlit 佈署，邀請 3 位投手在 sandbox 帳戶驗證
- 正式上線：通過 QA checklist 後合併 main，CI 觸發自動部署與 Logfire 儀表板註冊
- 事後回顧：上線兩週內收集採納率與使用者回饋，必要時進行 prompt 或工具迭代

## 🧾 Prompt 治理與版本控管
- `prompts/registry.yaml` 為單一真相來源，紀錄版本號、適用 Agent、實驗標誌
- 任何 prompt 更新需提出 Prompt PR，包含：目標、預期指標、Rollback 計畫
- 上線前於基準資料集跑回歸測試，確保指標未惡化（採納率、延遲、錯誤率）
- 版本變更寫入 Logfire metadata，方便日後回朔並分析 model drift
- 每月舉辦 Prompt Review，評估淘汰表現不佳的變體，維持 Registry 精簡

## 👥 內部訓練與導入計畫
- Week 0：舉辦 2 hr Workshop，介紹 Pydantic AI 架構、Agent 模型與 Debug Panel
- Week 1：投手 Ops 進行 hands-on 練習，每位至少完成一次文案/圖片/優化案例
- Week 2：產品、數據、AI 三方共同檢核採納率與阻礙，形成 FAQ 與操作手冊補充
- Week 3：導入例行 Retro，回顧 Agent 產出對業績的影響，調整優先順序
- 持續：每月分享最佳實務，收集跨部門案例加入 Knowledge Base

## 📆 里程碑與交付節奏

| 週次 | 目標 | 主要交付物 | 核心 Owner | 驗收標準 |
|------|------|------------|------------|-----------|
| Week 1 | Phase 1 收斂 | 4 個圖片/文案/優化頁面完成 Pydantic Agent 串接 | 工程（Kevin） | 單元測試通過、Staging 驗證 |
| Week 2 | Phase 2 啟動 | Optimization/Funnel/CreativePerformance Agent 落地 | 數據工程（Leo）+ 投手 Ops（Joy） | 指標比對報告、Slack 告警串接 |
| Week 3 | Phase 2 完成 | 剩餘分析類 Agent 上線、QA Checklist 完成 | 產品（Ken） | Logfire 成功率 ≥ 95%、採納率初測 |
| Week 4 | Phase 3 啟動 | 報告/策略/MVT/競品 Agent 原型 | AI 團隊（Mia） | Prompt Review 通過、Stakeholder Demo |
| Week 5 | Phase 3 完成 | 全面上線 + 執行回顧 | 全體 | Retro & KPI 對齊、知識庫更新 |

## 🔄 發佈與變更管理
- 發佈節奏：每週三為固定上線窗，非緊急項目需排入下一個週期
- 變更流程：提交 `CHANGELOG.md` 條目 + GitHub PR，並於 Slack `#meta-ai-release` 通知
- 風險等級：以 `minor`（提示詞微調）、`major`（模型/工具改動）、`hotfix`（生產問題）分類
- Rollback 指南：保留上一版 prompt/程式快照，於 Logfire 中標註 `rollback_from` 方便追蹤
- 發佈後 24 小時內由當日值班者負責觀測指標與錯誤率

## 🧯 維運支援與 SLA
- 值班輪值：數據工程、AI、投手 Ops 每週輪值，更新於 Notion 值班表
- 事件處理：重大故障 < 30 分鐘內於 Slack 建立 War Room，60 分鐘內提供暫行方案
- 支援管道：一般問題走 GitHub Discussions，緊急事件走 PagerDuty 呼叫當週值班
- Runbook：`docs/runbooks/pydantic-agents.md` 詳列常見錯誤碼、重新初始化步驟
- 復盤機制：每次 P1/P2 事件 48 小時內完成事後分析並更新預防措施


## 🧾 資料契約與驗證流程
- 每個 Agent 依賴的 DataFrame 需於 `utils/data_contracts.yaml` 註明欄位型別、允許值與缺漏策略
- 建立 `tests/data_contracts/test_*.py`，對接入資料做 schema 驗證與抽樣偵錯（使用 pandera）
- 重要欄位變更需先於 Notion Data Change Log 登記，並至少提前一個衝刺通知所有 Agent Owner
- 透過 `make validate-data` 指令在 CI 中自動比對資料契約與實際樣本，避免部署後才發現破版

## 💰 成本監控與效率優化
- Token 監控：Logfire 自動紀錄每次呼叫的 input/output token，週報匯總成本走勢
- 快取策略：對相同輸入的高頻任務啟用 `redis` 快取，或將結果落地至 `data/cache/agents/*.json`
- 模型等級降級指引：若 P95 延遲 > 6 秒或成本超出預算，優先評估改用 GPT-5-nano-instruct 或 Gemini 1.5 Flash
- 批次化：對可離線處理的頁面（例：報告生成）提供批次介面，降低尖峰時段的即時推論量

## 🔄 CI/CD 自動化流程
1. `pre-commit`：執行 `ruff`, `mypy`, `pytest tests/agents`，確保型別與測試皆通過
2. GitHub Actions `ci.yml`：啟動後端單元測試、`python -m compileall`, `streamlit e2e smoke`（headless）
3. 若變更 `utils/agents`，自動觸發 `tests/snapshots` 對應回歸比對；若差異超過閾值則標記審核
4. Merge 到 `main` 後觸發 `deploy.yaml`，部署至 staging，完成 Smoke Check 後再手動升至 production

## 🚀 持續優化 Roadmap
- Q1：完成 Phase 3 全頁面 Agent 化，並導入成本儀表板與 Slack Cost Alert
- Q2：導入自訂工具 SDK，支援自動抓取第三方 API（Shopify、GA4）並納入 Agent deps
- Q3：推出 Offline Reinforcement Loop，透過採納率與成效回傳自動微調 prompt 與策略
- Q4：評估引入混合推論（本地 LLM + 雲端）以降低敏感資料外流風險與雲端成本



## 🚀 開始執行

**立即開始**：
1. 從 `CopywritingAgent` 開始
2. 測試通過後，應用到 `12_✍️_AI文案生成.py`
3. 依序完成其他 Phase 1 的 Agents

**預估時間**：
- Phase 1: 3-4 天
- Phase 2: 4-5 天
- Phase 3: 3-4 天
- **總計**: 2-3 週完成全面改造

---

> **目標**：打造業界最強的 Meta 廣告 AI 助手！💪
