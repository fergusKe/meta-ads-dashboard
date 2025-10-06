# Pydantic AI Agents 完整文件

> 耘初茶食 Meta 廣告儀表板 - AI Agent 架構說明

---

## 📊 總覽

**總計 17 個 Pydantic AI Agent**，涵蓋文案生成、圖片處理、數據分析、優化建議等全方位功能。

### 模型策略

| 用途 | 使用模型 | 配置來源 |
|------|---------|----------|
| **文字生成/分析** | `gpt-5-nano` | `OPENAI_MODEL` (.env) |
| **圖片生成/分析** | `gemini-2.5-flash-image` | `GEMINI_IMAGE_MODEL` (.env) |

---

## 📋 全部 17 個 Agent 快速索引表

| # | Agent 名稱 | 使用頁面 | 主要功能 | 分類 | 模型 |
|---|-----------|---------|---------|------|------|
| 1 | **CopywritingAgent** | 12_✍️_AI文案生成 | 生成廣告文案變體、A/B測試建議 | 🎨 創意生成 | gpt-5-nano |
| 2 | **ImagePromptAgent** | 13_🎨_AI圖片生成 | 生成圖片提示詞、平台優化 | 🎨 創意生成 | gpt-5-nano |
| 3 | **ImageAnalysisAgent** | 25_📸_AI圖片分析與優化 | 圖片分析評分、優化建議 | 🎨 創意生成 | **Gemini 2.5** |
| 4 | **CreativeOptimizationAgent** | 14_🧠_智能素材優化 | 素材優化建議、A/B測試計畫 | 🎨 創意生成 | gpt-5-nano |
| 5 | **OptimizationAgent** | 10_⚡_即時優化建議 | 緊急問題識別、即時優化建議 | 📊 數據分析 | gpt-5-nano |
| 6 | **FunnelAnalysisAgent** | 7_🔄_轉換漏斗優化 | 漏斗瓶頸分析、流失原因診斷 | 📊 數據分析 | gpt-5-nano |
| 7 | **CreativePerformanceAgent** | 5_🎨_素材成效分析 | 素材表現分析、成功要素提取 | 📊 數據分析 | gpt-5-nano |
| 8 | **QualityScoreAgent** | 6_📈_廣告品質評分 | 多維度品質評分、改善計畫 | 📊 數據分析 | gpt-5-nano |
| 9 | **AudienceExpansionAgent** | 17_👥_受眾擴展建議 | 相似受眾推薦、擴展策略 | 📊 數據分析 | gpt-5-nano |
| 10 | **BudgetOptimizationAgent** | 18_💰_預算優化建議 | 預算分配優化、ROI預測 | 📊 數據分析 | gpt-5-nano |
| 11 | **ReportGenerationAgent** | 19_📄_自動化報告 | 週報月報生成、趨勢分析 | 🧪 測試報告 | gpt-5-nano |
| 12 | **ABTestDesignAgent** | 20_🧪_AB測試設計 | A/B測試方案設計、樣本量計算 | 🧪 測試報告 | gpt-5-nano |
| 13 | **MVTDesignAgent** | 24_🧬_多變量測試優化 | 多變量測試設計、交互作用分析 | 🧪 測試報告 | gpt-5-nano |
| 14 | **CompetitorAnalysisAgent** | 23_🌐_競爭對手分析 | 競品策略分析、差異化機會 | 🧪 測試報告 | gpt-5-nano |
| 15 | **StrategyAgent** | 15_🎯_智能投放策略 | 投放策略建議、目標設定 | 🎯 策略助手 | gpt-5-nano |
| 16 | **DailyCheckAgent** | 21_🤖_智能Agent巡檢 | 每日帳戶巡檢、異常檢測 | 🎯 策略助手 | gpt-5-nano |
| 17 | **ConversationalAdAgent** | 22_💬_對話式投放助手 | 自然語言對話、智能問答 | 🎯 策略助手 | gpt-5-nano |

### 分類統計

- 🎨 **創意生成類**：4 個（文案、圖片生成、圖片分析、素材優化）
- 📊 **數據分析類**：6 個（即時優化、漏斗、成效、品質、受眾、預算）
- 🧪 **測試報告類**：4 個（報告、A/B測試、MVT、競品分析）
- 🎯 **策略助手類**：3 個（投放策略、巡檢、對話助手）

---

## 🎨 創意生成類 Agent (4個)

### 1. CopywritingAgent - 文案生成 Agent

**檔案**：`utils/agents/copywriting_agent.py`
**使用頁面**：`12_✍️_AI文案生成.py`
**使用模型**：gpt-5-nano

#### 功能
- 生成 3-5 個廣告文案變體
- 自動整合 RAG 知識庫
- A/B 測試建議
- Meta 廣告政策合規性檢查

#### 結構化輸出
```python
class CopywritingResult(BaseModel):
    variants: list[AdCopyVariant]  # 3-5個文案變體
    strategy_explanation: str       # 策略說明
    ab_test_suggestions: list[str] # A/B測試建議
    optimization_tips: list[str]   # 優化建議
    performance_prediction: str    # 表現預測
    compliance_check: str          # 合規性檢查
```

#### 註冊工具
- `get_top_performing_copy()` - 獲取高效文案範例
- `get_audience_insights()` - 獲取受眾洞察
- `get_brand_voice_guidelines()` - 獲取品牌語調
- `analyze_competitor_messaging()` - 分析競品文案
- `get_seasonal_themes()` - 獲取節慶主題

---

### 2. ImagePromptAgent - 圖片提示詞生成 Agent

**檔案**：`utils/agents/image_prompt_agent.py`
**使用頁面**：`13_🎨_AI圖片生成.py`
**使用模型**：gpt-5-nano

#### 功能
- 生成 3 個優化的圖片提示詞變體
- 針對不同平台（Instagram/Facebook/Stories）優化
- 風格關鍵字提取
- 構圖建議

#### 結構化輸出
```python
class ImageGenerationResult(BaseModel):
    variants: list[ImagePrompt]         # 3個提示詞變體
    recommended_variant_index: int      # 推薦使用的變體
    style_consistency_notes: str        # 風格一致性說明
    platform_optimization_tips: list[str]  # 平台優化建議
```

#### 註冊工具
- `get_brand_visual_guidelines()` - 品牌視覺指南
- `get_top_performing_image_features()` - 高效圖片特徵
- `get_platform_specific_requirements()` - 平台規格要求
- `analyze_similar_high_performing_images()` - 分析相似高效圖片
- `get_style_specific_prompts()` - 風格範本庫

---

### 3. ImageAnalysisAgent - 圖片分析 Agent

**檔案**：`utils/agents/image_analysis_agent.py`
**使用頁面**：`25_📸_AI圖片分析與優化.py`
**使用模型**：**Gemini 2.5 Flash Image** (Vision)

#### 功能
- 使用 Gemini Vision 分析廣告圖片
- 6 大維度專業評分（1-10分）
- 詳細優缺點分析
- 生成優化建議和新提示詞

#### 結構化輸出
```python
class ImageAnalysisResult(BaseModel):
    scores: ImageScores              # 6維度評分
    overall_score: float             # 總分
    strengths: list[str]             # 優點（3-5個）
    weaknesses: list[str]            # 缺點（3-5個）
    detailed_analysis: dict[str, str]  # 各維度詳細分析
    optimization_suggestions: list[str]  # 優化建議（5-10個）
    optimized_prompts: list[str]     # 優化後的提示詞（3個）
```

#### 6 大評分維度
1. **視覺吸引力** (visual_appeal)
2. **構圖設計** (composition)
3. **色彩運用** (color_usage)
4. **文字可讀性** (text_readability)
5. **品牌一致性** (brand_consistency)
6. **投放適配性** (ad_suitability)

#### 註冊工具
- `analyze_with_vision()` - 使用 Gemini Vision API 分析圖片
- `get_brand_visual_standards()` - 品牌視覺標準
- `get_meta_ad_guidelines()` - Meta 廣告規範
- `get_high_performing_image_examples()` - 高效圖片範例

---

### 4. CreativeOptimizationAgent - 素材優化 Agent

**檔案**：`utils/agents/creative_optimization_agent.py`
**使用頁面**：`14_🧠_智能素材優化.py`
**使用模型**：gpt-5-nano

#### 功能
- 分析現有素材表現
- 提供 5-10 個優化建議
- A/B 測試計畫
- 計算優化潛力

#### 結構化輸出
```python
class CreativeOptimizationResult(BaseModel):
    optimization_suggestions: list[OptimizationSuggestion]  # 5-10個建議
    ab_test_plans: list[ABTestPlan]      # A/B測試計畫
    priority_actions: list[str]          # 優先行動項目
    expected_improvement: str            # 預期改善幅度
    implementation_roadmap: list[str]    # 實施路線圖
```

#### 註冊工具
- `analyze_creative_performance()` - 分析素材表現
- `get_successful_creative_patterns()` - 獲取成功素材模式
- `identify_underperforming_elements()` - 識別低效元素
- `get_optimization_examples()` - 獲取優化範例
- `calculate_optimization_potential()` - 計算優化潛力

---

## 📊 數據分析類 Agent (6個)

### 5. OptimizationAgent - 即時優化建議 Agent

**檔案**：`utils/agents/optimization_agent.py`
**使用頁面**：`10_⚡_即時優化建議.py`
**使用模型**：gpt-5-nano

#### 功能
- 識別緊急問題
- 提供即時優化建議
- 優先級排序
- 預期改善評估

#### 結構化輸出
```python
class OptimizationResult(BaseModel):
    urgent_issues: list[Issue]           # 緊急問題
    optimization_recommendations: list[Recommendation]  # 優化建議
    priority_ranking: list[str]          # 優先級排序
    estimated_impact: dict[str, str]     # 預期影響
    action_plan: list[str]               # 行動計畫
```

---

### 6. FunnelAnalysisAgent - 漏斗分析 Agent

**檔案**：`utils/agents/funnel_analysis_agent.py`
**使用頁面**：`7_🔄_轉換漏斗優化.py`
**使用模型**：gpt-5-nano

#### 功能
- 識別漏斗瓶頸
- 轉換率分析
- 流失原因診斷
- 優化建議

#### 結構化輸出
```python
class FunnelAnalysisResult(BaseModel):
    bottlenecks: list[Bottleneck]        # 瓶頸點
    conversion_insights: list[str]       # 轉換洞察
    drop_off_reasons: list[str]          # 流失原因
    optimization_suggestions: list[str]  # 優化建議
    expected_improvement: str            # 預期改善
```

---

### 7. CreativePerformanceAgent - 素材成效分析 Agent

**檔案**：`utils/agents/creative_performance_agent.py`
**使用頁面**：`5_🎨_素材成效分析.py`
**使用模型**：gpt-5-nano

#### 功能
- 素材表現分析
- 成功要素提取
- 對比分析
- 改善建議

#### 結構化輸出
```python
class CreativePerformanceResult(BaseModel):
    top_performers: list[CreativeInsight]   # 最佳素材
    success_factors: list[str]              # 成功要素
    underperformers: list[CreativeInsight]  # 低效素材
    improvement_recommendations: list[str]  # 改善建議
    trend_analysis: str                     # 趨勢分析
```

---

### 8. QualityScoreAgent - 廣告品質評分 Agent

**檔案**：`utils/agents/quality_score_agent.py`
**使用頁面**：`6_📈_廣告品質評分.py`
**使用模型**：gpt-5-nano

#### 功能
- 多維度品質評分
- 詳細改善計畫
- 基準對比
- 優化路徑

#### 結構化輸出
```python
class QualityScoreResult(BaseModel):
    overall_score: float                 # 總分
    dimension_scores: dict[str, float]   # 各維度分數
    improvement_plan: list[str]          # 改善計畫
    benchmark_comparison: str            # 基準對比
    priority_areas: list[str]            # 優先改善領域
```

---

### 9. AudienceExpansionAgent - 受眾擴展建議 Agent

**檔案**：`utils/agents/audience_expansion_agent.py`
**使用頁面**：`17_👥_受眾擴展建議.py`
**使用模型**：gpt-5-nano

#### 功能
- 相似受眾推薦
- 擴展策略
- 風險評估
- 測試計畫

#### 結構化輸出
```python
class AudienceExpansionResult(BaseModel):
    lookalike_audiences: list[LookalikeAudience]  # 相似受眾
    expansion_strategies: list[str]               # 擴展策略
    risk_assessment: str                          # 風險評估
    testing_plan: list[str]                       # 測試計畫
    expected_reach_increase: str                  # 預期觸及增長
```

---

### 10. BudgetOptimizationAgent - 預算優化建議 Agent

**檔案**：`utils/agents/budget_optimization_agent.py`
**使用頁面**：`18_💰_預算優化建議.py`
**使用模型**：gpt-5-nano

#### 功能
- 預算分配優化
- ROI 預測
- 重新分配建議
- 風險控制

#### 結構化輸出
```python
class BudgetOptimizationResult(BaseModel):
    current_allocation_analysis: str     # 當前分配分析
    optimization_recommendations: list[BudgetRecommendation]  # 優化建議
    reallocation_plan: list[str]         # 重新分配計畫
    expected_roi_improvement: str        # 預期ROI改善
    risk_factors: list[str]              # 風險因素
```

---

## 🧪 測試與報告類 Agent (4個)

### 11. ReportGenerationAgent - 自動化報告生成 Agent

**檔案**：`utils/agents/report_generation_agent.py`
**使用頁面**：`19_📄_自動化報告.py`
**使用模型**：gpt-5-nano

#### 功能
- 週報/月報自動生成
- 關鍵指標摘要
- 趨勢分析
- 行動建議

#### 結構化輸出
```python
class ReportGenerationResult(BaseModel):
    executive_summary: str               # 執行摘要
    key_metrics: dict[str, str]          # 關鍵指標
    performance_highlights: list[str]    # 表現亮點
    areas_of_concern: list[str]          # 需關注領域
    recommendations: list[str]           # 建議
    next_period_forecast: str            # 下期預測
```

---

### 12. ABTestDesignAgent - A/B 測試設計 Agent

**檔案**：`utils/agents/ab_test_design_agent.py`
**使用頁面**：`20_🧪_AB測試設計.py`
**使用模型**：gpt-5-nano

#### 功能
- A/B 測試方案設計
- 變數選擇
- 樣本量計算
- 成功指標定義

#### 結構化輸出
```python
class ABTestDesignResult(BaseModel):
    test_hypothesis: str                 # 測試假設
    control_variant: Variant             # 對照組
    test_variants: list[Variant]         # 測試組
    success_metrics: list[str]           # 成功指標
    sample_size_recommendation: str      # 樣本量建議
    duration_recommendation: str         # 測試時長建議
    analysis_plan: list[str]             # 分析計畫
```

---

### 13. MVTDesignAgent - 多變量測試設計 Agent

**檔案**：`utils/agents/mvt_design_agent.py`
**使用頁面**：`24_🧬_多變量測試優化.py`
**使用模型**：gpt-5-nano

#### 功能
- 多變量測試設計
- 變數組合優化
- 交互作用分析
- 複雜度管理

#### 結構化輸出
```python
class MVTDesignResult(BaseModel):
    test_variables: list[TestVariable]   # 測試變數
    combinations: list[Combination]      # 變數組合
    interaction_analysis: str            # 交互作用分析
    complexity_assessment: str           # 複雜度評估
    implementation_guide: list[str]      # 實施指南
```

---

### 14. CompetitorAnalysisAgent - 競爭對手分析 Agent

**檔案**：`utils/agents/competitor_analysis_agent.py`
**使用頁面**：`23_🌐_競爭對手分析.py`
**使用模型**：gpt-5-nano

#### 功能
- 競品策略分析
- 差異化機會
- 威脅識別
- 應對建議

#### 結構化輸出
```python
class CompetitorAnalysisResult(BaseModel):
    competitor_strategies: list[CompetitorStrategy]  # 競品策略
    differentiation_opportunities: list[str]         # 差異化機會
    threats: list[str]                               # 威脅
    counter_strategies: list[str]                    # 應對策略
    market_positioning_advice: str                   # 市場定位建議
```

---

## 🎯 策略與助手類 Agent (3個)

### 15. StrategyAgent - 智能投放策略 Agent

**檔案**：`utils/agents/strategy_agent.py`
**使用頁面**：`15_🎯_智能投放策略.py`
**使用模型**：gpt-5-nano

#### 功能
- 投放策略建議
- 目標設定
- 預算分配
- 時間規劃

#### 結構化輸出
```python
class StrategyAgentResult(BaseModel):
    recommended_strategy: str            # 推薦策略
    target_audience: str                 # 目標受眾
    budget_allocation: dict[str, str]    # 預算分配
    timeline: list[str]                  # 時間規劃
    success_metrics: list[str]           # 成功指標
    risk_mitigation: list[str]           # 風險緩解
```

---

### 16. DailyCheckAgent - 每日巡檢 Agent

**檔案**：`utils/agents/daily_check_agent.py`
**使用頁面**：`21_🤖_智能Agent巡檢.py`
**使用模型**：gpt-5-nano

#### 功能
- 每日廣告帳戶巡檢
- 異常檢測
- 緊急建議
- 健康度評分

#### 結構化輸出
```python
class DailyCheckResult(BaseModel):
    health_score: float                  # 健康度評分（0-100）
    critical_issues: list[Issue]         # 嚴重問題
    warnings: list[Warning]              # 警告
    opportunities: list[Opportunity]     # 機會
    daily_recommendations: list[str]     # 每日建議
    trend_alerts: list[str]              # 趨勢警報
```

---

### 17. ConversationalAdAgent - 對話式投放助手 Agent

**檔案**：`utils/agents/conversational_agent.py`
**使用頁面**：`22_💬_對話式投放助手.py`
**使用模型**：gpt-5-nano

#### 功能
- 自然語言對話
- 多輪問答
- 上下文記憶
- 智能建議

#### 結構化輸出
```python
class AgentResponse(BaseModel):
    message: str                         # 回覆訊息
    suggestions: list[str]               # 建議（可選）
    data_insights: dict[str, Any]        # 數據洞察（可選）
    next_steps: list[str]                # 後續步驟（可選）
```

---

## 📋 頁面對應表

### 已整合 Pydantic AI 的頁面（17個）

| 頁面編號 | 頁面名稱 | 使用 Agent | Agent 類型 |
|---------|---------|-----------|-----------|
| 5 | 🎨_素材成效分析 | CreativePerformanceAgent | 數據分析 |
| 6 | 📈_廣告品質評分 | QualityScoreAgent | 數據分析 |
| 7 | 🔄_轉換漏斗優化 | FunnelAnalysisAgent | 數據分析 |
| 10 | ⚡_即時優化建議 | OptimizationAgent | 數據分析 |
| 12 | ✍️_AI文案生成 | CopywritingAgent | 創意生成 |
| 13 | 🎨_AI圖片生成 | ImagePromptAgent | 創意生成 |
| 14 | 🧠_智能素材優化 | CreativeOptimizationAgent | 創意生成 |
| 15 | 🎯_智能投放策略 | StrategyAgent | 策略助手 |
| 17 | 👥_受眾擴展建議 | AudienceExpansionAgent | 數據分析 |
| 18 | 💰_預算優化建議 | BudgetOptimizationAgent | 數據分析 |
| 19 | 📄_自動化報告 | ReportGenerationAgent | 測試報告 |
| 20 | 🧪_AB測試設計 | ABTestDesignAgent | 測試報告 |
| 21 | 🤖_智能Agent巡檢 | DailyCheckAgent | 策略助手 |
| 22 | 💬_對話式投放助手 | ConversationalAdAgent | 策略助手 |
| 23 | 🌐_競爭對手分析 | CompetitorAnalysisAgent | 測試報告 |
| 24 | 🧬_多變量測試優化 | MVTDesignAgent | 測試報告 |
| 25 | 📸_AI圖片分析與優化 | ImageAnalysisAgent | 創意生成 |

### 不需要 Agent 的頁面（8個）

純數據展示、圖表、導航頁面，無需 AI 功能：

| 頁面編號 | 頁面名稱 | 類型 |
|---------|---------|------|
| 1 | 📊_整體效能儀表板 | 數據展示 |
| 2 | 🎯_活動分析 | 數據展示 |
| 3 | 👥_受眾洞察 | 數據展示 |
| 4 | 💰_ROI分析 | 數據展示 |
| 8 | 📋_詳細數據表格 | 數據表格 |
| 9 | 📈_趨勢分析 | 圖表展示 |
| 11 | 🤖_AI素材製作首頁 | 導航頁面 |
| 16 | 🧠_RAG知識庫管理 | 工具頁面 |

---

## 🔧 技術規格

### Pydantic AI 架構

```python
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field

# 1. 定義輸出結構
class AgentResult(BaseModel):
    field1: str = Field(description="欄位說明")
    field2: list[str]
    # ...

# 2. 定義依賴項
class AgentDeps:
    data: pd.DataFrame
    context: str
    # ...

# 3. 創建 Agent
class MyAgent:
    def __init__(self):
        model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
        self.agent = Agent(
            f'openai:{model_name}',
            output_type=AgentResult,
            deps_type=AgentDeps,
            system_prompt=self._get_system_prompt()
        )
        self._register_tools()

    # 4. 註冊工具
    def _register_tools(self):
        @self.agent.tool
        def tool_name(ctx: RunContext[AgentDeps]) -> dict:
            # 工具邏輯
            return {'result': 'data'}

    # 5. 執行 Agent
    async def analyze(self, data, context):
        result = await self.agent.run(
            prompt,
            deps=AgentDeps(data=data, context=context)
        )
        return result.data
```

### 共通特色

✅ **型別安全**：所有輸出使用 Pydantic BaseModel 保證結構
✅ **工具整合**：每個 Agent 都有 4-6 個專屬工具
✅ **配置靈活**：從 .env 讀取模型配置
✅ **執行可視化**：UI 顯示 Agent 工作流程
✅ **RAG 整合**：支援知識庫檢索增強生成

---

## 📝 使用範例

### 文案生成範例

```python
from utils.agents import CopywritingAgent

# 初始化
agent = CopywritingAgent()

# 生成文案
result = await agent.generate_copy(
    product_name="耘初茶食高山烏龍茶",
    target_audience="25-40歲注重健康的都市上班族",
    campaign_goal="提升品牌知名度",
    tone="專業溫暖",
    special_requirements="強調傳統工藝"
)

# 使用結果
for i, variant in enumerate(result.variants, 1):
    print(f"變體 {i}：{variant.headline}")
    print(f"內文：{variant.primary_text}")
    print(f"CTA：{variant.cta}")
```

### 圖片分析範例

```python
from utils.agents import ImageAnalysisAgent
from PIL import Image

# 初始化
agent = ImageAnalysisAgent()

# 分析圖片
image = Image.open("ad_image.png")
result = await agent.analyze_image(
    image=image,
    brand_context="耘初茶食 - 台灣茶飲品牌"
)

# 查看評分
print(f"總分：{result.overall_score}/10")
print(f"視覺吸引力：{result.scores.visual_appeal}/10")
print(f"構圖設計：{result.scores.composition}/10")

# 優化建議
for suggestion in result.optimization_suggestions:
    print(f"• {suggestion}")
```

---

## 🎯 開發指南

### 新增 Agent 的步驟

1. **創建 Agent 檔案**：`utils/agents/your_agent.py`
2. **定義輸出結構**：繼承 `BaseModel`
3. **定義依賴項**：創建 `Deps` 類別
4. **實作 Agent 類別**：包含 `__init__`、`_register_tools`、執行方法
5. **註冊工具**：使用 `@self.agent.tool` 裝飾器
6. **導出 Agent**：在 `utils/agents/__init__.py` 中匯出
7. **整合到頁面**：在對應頁面導入並使用

### 最佳實踐

✅ 輸出結構簡單清晰（避免過度巢狀）
✅ 工具功能單一職責
✅ System Prompt 詳細明確
✅ 錯誤處理完善
✅ 加入執行流程可視化

---

## 📞 相關資源

- **Pydantic AI 官方文檔**：https://ai.pydantic.dev
- **改造計畫文件**：`Pydantic_AI_改造計畫.md`
- **Agent 原始碼**：`utils/agents/`
- **頁面整合範例**：`pages/12_✍️_AI文案生成.py`

---

*最後更新：2025-10-06*
*版本：v1.0*
*維護者：耘初茶食開發團隊*
