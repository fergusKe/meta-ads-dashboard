"""
圖片提示詞生成 Agent (Pydantic AI)

功能：
- 為 Gemini 生成優化的圖片提示詞
- 結合品牌視覺規範和廣告目標
- 提供多個提示詞變體供選擇
- 整合 RAG 檢索高效圖片特徵

特色：
- 完全型別安全
- 結構化輸出（Pydantic models）
- 自動優化提示詞品質
- 品牌一致性檢查
"""

import os
import streamlit as st

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from dataclasses import dataclass
from typing import Optional
import pandas as pd

from utils.cache_manager import cache_agent_result
from utils.error_handler import handle_agent_errors
from utils.model_selector import ModelSelector
from utils.history_manager import record_history
from utils.validators import validate_inputs
from utils.security import sanitize_payload

# ============================================
# 結構化輸出定義（完全型別安全）
# ============================================

class ImagePrompt(BaseModel):
    """單個圖片提示詞"""
    main_prompt: str = Field(
        description="主要提示詞（英文，詳細描述圖片內容）",
        min_length=50,
        max_length=500
    )
    chinese_description: str = Field(
        description="中文說明（幫助理解提示詞內容）",
        min_length=20,
        max_length=200
    )
    style_keywords: list[str] = Field(
        description="風格關鍵字（如：modern, elegant, warm）",
        min_length=3,
        max_length=8
    )
    composition_tips: list[str] = Field(
        description="構圖建議（如：主體居中、三分法）",
        min_length=2,
        max_length=5
    )
    color_palette: list[str] = Field(
        description="建議色彩（如：warm tones, green, brown）",
        min_length=2,
        max_length=5
    )
    mood: str = Field(
        description="氛圍/情緒（如：relaxing, energetic, elegant）"
    )
    target_platform: str = Field(
        description="目標平台（如：Instagram, Facebook feed）"
    )

class ImageGenerationResult(BaseModel):
    """圖片生成結果（完全型別安全）"""
    prompts: list[ImagePrompt] = Field(
        description="3個提示詞變體（不同風格和角度）",
        min_length=3,
        max_length=3
    )
    brand_alignment_score: int = Field(
        ge=0,
        le=100,
        description="品牌一致性分數（0-100）"
    )
    ad_suitability_score: int = Field(
        ge=0,
        le=100,
        description="廣告適配性分數（0-100）"
    )
    rationale: str = Field(
        description="設計理念說明（為何選擇這些角度和風格）"
    )
    optimization_tips: list[str] = Field(
        description="優化建議（如何進一步改善）",
        min_length=3,
        max_length=5
    )
    recommended_variant: int = Field(
        ge=0,
        le=2,
        description="推薦使用的變體索引（0-2）"
    )
    platform_guidelines: dict[str, list[str]] = Field(
        description="平台規範提醒（Meta 廣告圖片要求）"
    )

# ============================================
# Agent 依賴注入
# ============================================

@dataclass
class ImagePromptDeps:
    """Agent 依賴（用於依賴注入）"""
    df: pd.DataFrame  # 廣告數據
    brand_name: str = "耘初茶食"
    product_category: str = "台灣茶飲、茶食產品"
    brand_visual_style: str = "現代簡約、溫暖自然、專業質感"
    image_type: str = "產品展示"  # 產品展示/生活場景/品牌識別/促銷活動
    style_preference: str = "現代簡約"  # 現代簡約/溫暖自然/時尚潮流/傳統文化
    target_audience: Optional[str] = None
    special_requirements: Optional[str] = None
    image_size: str = "1024x1024"  # 圖片尺寸
    rag_service: Optional[object] = None  # RAG 服務（可選）

# ============================================
# Agent 定義
# ============================================

class ImagePromptAgent:
    """圖片提示詞生成 Agent（Pydantic AI）"""

    def __init__(self):
        """初始化 Agent"""
        selector = ModelSelector()
        preference = st.session_state.get('user_preferences', {}).get('image_prompt_complexity')
        model_name = selector.choose(complexity=preference or os.getenv('IMAGE_PROMPT_COMPLEXITY', 'balanced'))

        self.agent = Agent(
            f'openai:{model_name}',
            output_type=ImageGenerationResult,
            deps_type=ImagePromptDeps,
            system_prompt=self._get_system_prompt()
        )

        # 註冊工具
        self._register_tools()

    def _get_system_prompt(self) -> str:
        """系統提示詞"""
        return """
你是專業的 AI 圖片提示詞工程師（Prompt Engineer），專精於為 Gemini 生成高品質廣告圖片提示詞。

專長：
1. 撰寫詳細且有效的圖片生成提示詞
2. 理解品牌視覺規範和廣告目標
3. 優化提示詞以獲得最佳生成結果
4. 確保圖片符合 Meta 廣告規範

提示詞撰寫原則：

**結構化描述**：
- 主體（Subject）：明確描述主要物體
- 環境（Environment）：背景和場景設定
- 風格（Style）：藝術風格和視覺處理
- 構圖（Composition）：視角和佈局
- 光線（Lighting）：光線和氛圍
- 色彩（Colors）：色調和色彩搭配
- 細節（Details）：重要的細節和質感

**優質提示詞特徵**：
1. **具體明確**：避免模糊詞彙，使用具體描述
2. **層次分明**：從主體到細節，層次清晰
3. **風格一致**：整體風格統一協調
4. **關鍵字優先**：重要元素放前面
5. **適當長度**：50-300字為佳（英文）

**Meta 廣告圖片要求**：
- ✅ 高解析度、清晰銳利
- ✅ 主體明確、視覺焦點清晰
- ✅ 適合手機螢幕瀏覽
- ✅ 文字（如有）要清晰可讀
- ✅ 符合品牌調性
- ❌ 避免過度複雜的構圖
- ❌ 避免低品質或模糊
- ❌ 避免誤導性圖片

**品牌視覺原則（耘初茶食）**：
- 傳統與現代融合
- 自然、溫暖的色調
- 專業、高品質感
- 台灣在地特色
- 健康、養生氛圍

輸出要求：
- 生成 3 個不同角度的提示詞變體
- 每個提示詞要用英文（AI 圖片生成對英文效果更好）
- 提供中文說明幫助理解
- 評估品牌一致性和廣告適配性
- 推薦最佳變體
- 提供優化建議
"""

    def _register_tools(self):
        """註冊 Agent 可用的工具"""

        @self.agent.tool
        def get_brand_visual_guidelines(ctx: RunContext[ImagePromptDeps]) -> dict:
            """獲取品牌視覺規範"""
            return {
                'brand_name': ctx.deps.brand_name,
                'product_category': ctx.deps.product_category,
                'visual_style': ctx.deps.brand_visual_style,
                'color_palette': [
                    '溫暖的茶色系（brown, amber, golden）',
                    '自然綠色（green, sage, olive）',
                    '乾淨的白色和米色（white, cream, beige）',
                    '點綴的深色（dark brown, black）'
                ],
                'style_keywords': [
                    'modern', 'elegant', 'natural', 'warm',
                    'professional', 'high-quality', 'taiwanese',
                    'traditional-meets-modern', 'wellness', 'artisanal'
                ],
                'avoid': [
                    '過於商業化、促銷感太重',
                    '低品質、粗糙的視覺',
                    '與健康養生無關的元素',
                    '過度後製、不自然的效果'
                ]
            }

        @self.agent.tool
        def get_top_performing_image_features(ctx: RunContext[ImagePromptDeps]) -> dict:
            """獲取高效圖片特徵（從歷史數據推斷）"""
            df = ctx.deps.df

            # 找出高 ROAS 的活動
            high_performers = df[
                df['購買 ROAS（廣告投資報酬率）'] > 3.0
            ].nlargest(10, '購買 ROAS（廣告投資報酬率）')

            # 分析受眾特徵（推斷適合的圖片風格）
            audience_insights = []
            if '年齡' in df.columns:
                age_groups = high_performers['年齡'].value_counts().head(3).to_dict()
                for age, count in age_groups.items():
                    if '25-34' in str(age) or '35-44' in str(age):
                        audience_insights.append('年輕專業族群：現代簡約、時尚感')
                    elif '45-54' in str(age) or '55-64' in str(age):
                        audience_insights.append('成熟族群：傳統工藝、品質感')

            return {
                'high_performing_campaigns': high_performers['行銷活動名稱'].tolist()[:5],
                'audience_insights': audience_insights if audience_insights else ['一般大眾：平衡傳統與現代'],
                'recommended_styles': [
                    '產品特寫：突出質感和細節',
                    '生活場景：營造品茶氛圍',
                    '品牌故事：展現工藝和傳承'
                ]
            }

        @self.agent.tool
        def get_platform_specific_requirements(ctx: RunContext[ImagePromptDeps]) -> dict:
            """獲取平台特定要求（Meta 廣告）"""
            image_size = ctx.deps.image_size

            # 根據尺寸判斷平台
            platform_info = {
                '1024x1024': {
                    'platform': 'Instagram Feed / Facebook 方形貼文',
                    'requirements': [
                        '主體居中，適合方形裁切',
                        '視覺焦點明確',
                        '文字（如有）保持在安全區域內',
                        '適合手機直式瀏覽'
                    ]
                },
                '1792x1024': {
                    'platform': 'Facebook 橫幅 / Desktop Feed',
                    'requirements': [
                        '橫向構圖，主體可偏左或偏右',
                        '適合桌面版瀏覽',
                        '可包含更多環境元素',
                        '文字區域建議在左側或右側'
                    ]
                },
                '1024x1792': {
                    'platform': 'Instagram / Facebook Stories',
                    'requirements': [
                        '直式構圖，主體在中上方',
                        '適合全螢幕直式瀏覽',
                        '上下預留空間給文字覆蓋',
                        'CTA 按鈕區域在下方'
                    ]
                }
            }

            return platform_info.get(image_size, platform_info['1024x1024'])

        @self.agent.tool
        def analyze_similar_high_performing_images(ctx: RunContext[ImagePromptDeps]) -> dict:
            """分析相似的高效圖片（使用 RAG 如果可用）"""
            rag_service = ctx.deps.rag_service

            if rag_service:
                try:
                    # 使用 RAG 檢索相似的高效廣告
                    query = f"{ctx.deps.product_category} {ctx.deps.style_preference}"
                    similar_ads = rag_service.search_similar_ads(query, top_k=5)

                    return {
                        'similar_high_performing_ads': similar_ads,
                        'visual_insights': '已從知識庫檢索相似高效廣告的視覺特徵'
                    }
                except:
                    pass

            # 如果沒有 RAG，返回一般建議
            return {
                'general_recommendations': [
                    '使用自然光線，營造溫暖氛圍',
                    '產品特寫搭配環境元素',
                    '色調統一，避免過多顏色',
                    '留白空間，避免擁擠感'
                ]
            }

        @self.agent.tool
        def get_style_specific_prompts(ctx: RunContext[ImagePromptDeps]) -> dict:
            """獲取風格特定的提示詞模板"""
            style = ctx.deps.style_preference
            image_type = ctx.deps.image_type

            style_templates = {
                '現代簡約': {
                    'keywords': ['minimalist', 'clean', 'simple', 'modern', 'sleek'],
                    'composition': ['centered', 'lots of white space', 'geometric'],
                    'lighting': ['soft natural light', 'bright', 'even lighting'],
                    'colors': ['neutral tones', 'white', 'beige', 'minimal colors']
                },
                '溫暖自然': {
                    'keywords': ['natural', 'warm', 'organic', 'cozy', 'rustic'],
                    'composition': ['natural arrangement', 'soft focus background'],
                    'lighting': ['warm sunlight', 'golden hour', 'soft shadows'],
                    'colors': ['earth tones', 'brown', 'green', 'warm amber']
                },
                '時尚潮流': {
                    'keywords': ['trendy', 'stylish', 'contemporary', 'chic', 'vibrant'],
                    'composition': ['dynamic angle', 'bold composition'],
                    'lighting': ['dramatic lighting', 'high contrast'],
                    'colors': ['bold colors', 'gradient', 'vibrant tones']
                },
                '傳統文化': {
                    'keywords': ['traditional', 'cultural', 'elegant', 'classic', 'artisanal'],
                    'composition': ['symmetrical', 'balanced', 'traditional arrangement'],
                    'lighting': ['soft diffused light', 'atmospheric'],
                    'colors': ['traditional colors', 'muted tones', 'classic palette']
                }
            }

            return style_templates.get(style, style_templates['現代簡約'])

    @cache_agent_result()
    @handle_agent_errors(context='生成圖片提示')
    async def generate_prompts(
        self,
        df: pd.DataFrame,
        image_type: str = "產品展示",
        style_preference: str = "現代簡約",
        target_audience: Optional[str] = None,
        special_requirements: Optional[str] = None,
        image_size: str = "1024x1024",
        rag_service: Optional[object] = None
    ) -> ImageGenerationResult:
        """
        生成圖片提示詞

        Args:
            df: 廣告數據 DataFrame
            image_type: 圖片類型
            style_preference: 風格偏好
            target_audience: 目標受眾
            special_requirements: 特殊要求
            image_size: 圖片尺寸
            rag_service: RAG 服務（可選）

        Returns:
            ImageGenerationResult: 型別安全的提示詞生成結果
        """
        # 輸入驗證
        warnings = validate_inputs({'target_audience': target_audience, 'objective': image_type})
        if warnings:
            for message in warnings:
                st.warning(f'輸入提醒: {message}')

        deps = ImagePromptDeps(
            df=df,
            image_type=image_type,
            style_preference=style_preference,
            target_audience=target_audience,
            special_requirements=special_requirements,
            image_size=image_size,
            rag_service=rag_service
        )

        # 構建提示詞
        user_prompt = f"""
生成廣告圖片提示詞：

圖片類型：{image_type}
風格偏好：{style_preference}
目標受眾：{target_audience or '一般大眾'}
圖片尺寸：{image_size}
特殊要求：{special_requirements or '無'}

請執行以下步驟：
1. 使用工具了解品牌視覺規範
2. 分析高效圖片特徵
3. 獲取平台特定要求
4. 參考風格模板
5. 生成 3 個不同角度的提示詞變體

提示詞要求：
- 用英文撰寫（AI 圖片生成效果更好）
- 詳細描述主體、環境、風格、構圖、光線、色彩
- 每個變體要有不同的視覺重點或情境
- 符合品牌視覺規範
- 適合 Meta 廣告投放

請提供：
- 3 個完整的提示詞變體（含中文說明）
- 品牌一致性和廣告適配性評分
- 設計理念說明
- 優化建議
- 推薦使用的變體
- 平台規範提醒
"""

        # 執行 Agent
        result = await self.agent.run(user_prompt, deps=deps)
        output = result.output
        record_history(
            'ImagePromptAgent',
            inputs=sanitize_payload({
                'audience': target_audience or '',
                'image_type': image_type,

            }),
            output=output.model_dump() if hasattr(output, 'model_dump') else str(output),
            metadata={'warnings': warnings},
        )
        return output

    def generate_prompts_sync(
        self,
        df: pd.DataFrame,
        image_type: str = "產品展示",
        style_preference: str = "現代簡約",
        target_audience: Optional[str] = None,
        special_requirements: Optional[str] = None,
        image_size: str = "1024x1024",
        rag_service: Optional[object] = None
    ) -> ImageGenerationResult:
        """
        同步版本的提示詞生成（用於 Streamlit）
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.generate_prompts(
                df,
                image_type,
                style_preference,
                target_audience,
                special_requirements,
                image_size,
                rag_service
            )
        )


# ============================================
# 使用範例
# ============================================

if __name__ == "__main__":
    """測試 Agent"""
    from utils.data_loader import load_meta_ads_data

    # 載入數據
    df = load_meta_ads_data()

    # 創建 Agent
    agent = ImagePromptAgent()

    # 生成提示詞
    result = agent.generate_prompts_sync(
        df,
        image_type="產品展示",
        style_preference="溫暖自然",
        target_audience="25-44歲 女性，注重健康養生",
        special_requirements="展現茶葉的天然質感，適合下午茶氛圍",
        image_size="1024x1024"
    )

    # 輸出結果
    print("=" * 70)
    print("圖片提示詞變體：")
    for i, prompt in enumerate(result.prompts, 1):
        print(f"\n{'='*70}")
        print(f"變體 {i}:")
        print(f"\n英文提示詞:")
        print(prompt.main_prompt)
        print(f"\n中文說明:")
        print(prompt.chinese_description)
        print(f"\n風格關鍵字: {', '.join(prompt.style_keywords)}")
        print(f"色彩建議: {', '.join(prompt.color_palette)}")
        print(f"氛圍: {prompt.mood}")

    print(f"\n{'='*70}")
    print(f"品牌一致性分數: {result.brand_alignment_score}/100")
    print(f"廣告適配性分數: {result.ad_suitability_score}/100")
    print(f"\n推薦使用: 變體 {result.recommended_variant + 1}")
    print(f"\n設計理念:")
    print(result.rationale)
