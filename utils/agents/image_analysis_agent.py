"""
圖片分析 Agent (Pydantic AI + Gemini 2.5 Flash Image)

功能：
- 使用 Gemini 2.5 Flash Image 分析廣告圖片
- 6 大維度專業評分
- 詳細優缺點分析
- 生成優化建議
- 結構化輸出保證品質

特色：
- 完全型別安全
- 整合 Gemini Vision API
- 自動生成優化提示詞
- 品牌一致性檢查
- 統一使用 Gemini（分析+生成）
"""

import os

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from dataclasses import dataclass
from typing import Optional
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# ============================================
# 結構化輸出定義（完全型別安全）
# ============================================

class ImageAnalysisScores(BaseModel):
    """圖片分析評分"""
    visual_appeal: int = Field(ge=1, le=10, description="視覺吸引力")
    composition: int = Field(ge=1, le=10, description="構圖設計")
    color_usage: int = Field(ge=1, le=10, description="色彩運用")
    text_readability: int = Field(ge=1, le=10, description="文字可讀性")
    brand_consistency: int = Field(ge=1, le=10, description="品牌一致性")
    ad_suitability: int = Field(ge=1, le=10, description="投放適配性")

class ImageAnalysisResult(BaseModel):
    """圖片分析結果（完全型別安全）"""
    scores: ImageAnalysisScores = Field(description="6 大維度評分")
    overall_score: float = Field(
        ge=0,
        le=10,
        description="總體評分（6 個分數的平均）"
    )
    strengths: list[str] = Field(
        description="優點列表",
        min_length=3,
        max_length=5
    )
    weaknesses: list[str] = Field(
        description="缺點列表",
        min_length=3,
        max_length=5
    )
    detailed_analysis: dict[str, str] = Field(
        description="詳細分析（每個維度的具體說明）"
    )
    optimization_suggestions: list[str] = Field(
        description="優化建議（具體可執行的改善方案）",
        min_length=5,
        max_length=7
    )
    is_suitable_for_ads: bool = Field(
        description="是否適合用於廣告投放"
    )
    suitability_reason: str = Field(
        description="適合/不適合的原因說明"
    )
    target_audience_recommendation: str = Field(
        description="建議的目標受眾特徵"
    )
    optimization_prompt: str = Field(
        description="用於生成優化圖片的提示詞"
    )

# ============================================
# Agent 依賴注入
# ============================================

@dataclass
class ImageAnalysisDeps:
    """Agent 依賴（用於依賴注入）"""
    image: Image.Image  # PIL Image 物件
    df: pd.DataFrame  # 廣告數據（用於品牌背景）
    brand_name: str = "耘初茶食"
    brand_context: str = "台灣茶飲品牌，注重品質與傳統工藝"
    openai_client: Optional[object] = None  # OpenAI 客戶端

# ============================================
# Agent 定義
# ============================================

class ImageAnalysisAgent:
    """圖片分析 Agent（Pydantic AI + Gemini 2.5 Flash Image）"""

    def __init__(self):
        """初始化 Agent"""
        # 從 .env 讀取模型名稱
        model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')

        # 創建 Agent
        self.agent = Agent(
            f'openai:{model_name}',
            output_type=ImageAnalysisResult,
            deps_type=ImageAnalysisDeps,
            system_prompt=self._get_system_prompt()
        )

        # 註冊工具
        self._register_tools()

    def _get_system_prompt(self) -> str:
        """系統提示詞"""
        return """
你是專業的廣告圖片分析 AI Agent，專精於評估 Meta 廣告圖片的品質和效果。

分析維度：

**1. 視覺吸引力（Visual Appeal）**
- 第一眼的吸引程度
- 是否能在動態消息中脫穎而出
- 整體美感和專業度
- 評分標準：10分=極具吸引力，1分=毫無吸引力

**2. 構圖設計（Composition）**
- 主體是否清晰明確
- 視覺層次是否合理
- 留白和平衡感
- 視覺引導流暢度
- 評分標準：10分=構圖完美，1分=構圖混亂

**3. 色彩運用（Color Usage）**
- 色彩搭配是否和諧
- 是否符合品牌調性
- 色彩對比與可讀性
- 色彩情感是否適當
- 評分標準：10分=色彩完美，1分=色彩糟糕

**4. 文字可讀性（Text Readability）**
- 文字大小是否適中
- 字體選擇是否合適
- 手機端是否清晰可讀
- 文字與背景對比度
- 評分標準：10分=完全清晰，1分=無法閱讀

**5. 品牌一致性（Brand Consistency）**
- 是否體現品牌特色
- 風格是否符合品牌形象
- 品牌識別度
- 與品牌價值觀的契合度
- 評分標準：10分=完美契合，1分=完全不符

**6. 投放適配性（Ad Suitability）**
- 是否符合 Meta 廣告規範
- 是否適合目標受眾
- 轉換潛力評估
- 平台適配性
- 評分標準：10分=極佳，1分=不適合

分析原則：
- **客觀公正**：基於專業標準評分
- **具體明確**：指出具體問題和改善方向
- **可執行性**：建議要具體可執行
- **平衡性**：既指出優點也指出缺點
- **數據驅動**：結合行業最佳實踐

輸出要求：
- 6 個維度的評分（1-10 分）
- 3-5 個優點
- 3-5 個缺點
- 每個維度的詳細分析
- 5-7 個具體的優化建議
- 是否適合投放的判斷
- 目標受眾建議
- 優化圖片的提示詞
"""

    def _register_tools(self):
        """註冊 Agent 可用的工具"""

        @self.agent.tool
        def analyze_with_vision(ctx: RunContext[ImageAnalysisDeps]) -> dict:
            """使用 Gemini 2.5 Flash Image 分析圖片"""
            image = ctx.deps.image
            brand_context = ctx.deps.brand_context

            try:
                from google import genai
                import os

                # 取得 Gemini API Key
                api_key = os.getenv('GEMINI_API_KEY')
                if not api_key:
                    return {'error': 'GEMINI_API_KEY 未設定', 'success': False}

                # 初始化 Gemini 客戶端
                client = genai.Client(api_key=api_key)
                model_name = os.getenv('GEMINI_IMAGE_MODEL', 'gemini-2.5-flash-image')

                # 將圖片轉為 bytes
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                image_bytes = buffered.getvalue()

                # 構建分析提示
                vision_prompt = f"""
請以專業廣告分析師的角度，詳細分析這張廣告圖片。

品牌背景：{brand_context}

請描述：
1. 圖片的主要內容和元素
2. 構圖和視覺流
3. 色彩運用
4. 文字內容（如有）
5. 整體風格和氛圍
6. 是否適合用於廣告

請提供客觀且詳細的描述，作為後續評分的依據。
"""

                # 呼叫 Gemini Vision API
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        vision_prompt,
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": base64.b64encode(image_bytes).decode('utf-8')
                            }
                        }
                    ]
                )

                # 解析回應
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        return {
                                            'vision_analysis': part.text,
                                            'success': True
                                        }

                return {
                    'error': 'Gemini 未返回文字分析',
                    'success': False
                }

            except Exception as e:
                return {
                    'error': f'Gemini 分析失敗：{str(e)}',
                    'success': False
                }

        @self.agent.tool
        def get_brand_visual_standards(ctx: RunContext[ImageAnalysisDeps]) -> dict:
            """獲取品牌視覺標準"""
            return {
                'brand_name': ctx.deps.brand_name,
                'brand_values': '傳統工藝與現代創新結合，注重健康養生',
                'visual_standards': {
                    'color_palette': '溫暖自然色調（茶色、綠色、米白色）',
                    'style': '現代簡約、溫暖自然、專業質感',
                    'tone': '親切專業、值得信賴',
                    'key_elements': '茶葉、茶具、自然元素、台灣特色'
                },
                'avoid': [
                    '過於商業化、促銷感太重',
                    '低品質、粗糙的視覺',
                    '與健康養生無關的元素'
                ]
            }

        @self.agent.tool
        def get_meta_ad_guidelines(ctx: RunContext[ImageAnalysisDeps]) -> dict:
            """獲取 Meta 廣告規範"""
            return {
                'image_requirements': [
                    '解析度：至少 1080x1080',
                    '檔案格式：JPG 或 PNG',
                    '文字占比：建議少於 20%',
                    '圖片清晰度：高清晰，無模糊',
                    '主體明確：視覺焦點清晰'
                ],
                'content_policies': [
                    '❌ 誤導性內容',
                    '❌ 低品質或令人困惑的圖片',
                    '❌ 過度性暗示',
                    '❌ 前後對比圖（減肥廣告）',
                    '✅ 真實產品呈現',
                    '✅ 符合品牌形象',
                    '✅ 專業高品質'
                ],
                'best_practices': [
                    '手機優先：確保手機端清晰可見',
                    '焦點明確：單一主體，避免過多元素',
                    '色彩和諧：使用品牌色系',
                    'CTA 清晰：如有文字，要清晰可讀'
                ]
            }

        @self.agent.tool
        def get_high_performing_image_examples(ctx: RunContext[ImageAnalysisDeps]) -> dict:
            """獲取高效圖片範例特徵"""
            df = ctx.deps.df

            # 找出高 ROAS 的活動
            high_performers = df[
                df['購買 ROAS（廣告投資報酬率）'] > 3.0
            ].nlargest(5, '購買 ROAS（廣告投資報酬率）')

            return {
                'high_performing_campaigns': high_performers['行銷活動名稱'].tolist(),
                'common_success_factors': [
                    '產品特寫清晰可見',
                    '生活場景營造氛圍',
                    '色調溫暖自然',
                    '構圖簡潔專業',
                    '品牌識別明確'
                ]
            }

    async def analyze_image(
        self,
        image: Image.Image,
        df: pd.DataFrame,
        brand_context: Optional[str] = None,
        openai_client: Optional[object] = None
    ) -> ImageAnalysisResult:
        """
        分析圖片

        Args:
            image: PIL Image 物件
            df: 廣告數據 DataFrame
            brand_context: 品牌背景（可選）
            openai_client: OpenAI 客戶端

        Returns:
            ImageAnalysisResult: 型別安全的分析結果
        """
        if not brand_context:
            brand_context = "耘初茶食 - 台灣茶飲品牌，注重品質與傳統工藝"

        # 準備依賴
        deps = ImageAnalysisDeps(
            image=image,
            df=df,
            brand_context=brand_context,
            openai_client=openai_client
        )

        # 構建提示詞
        user_prompt = """
請分析這張廣告圖片：

步驟：
1. 使用 Vision API 工具分析圖片內容
2. 參考品牌視覺標準
3. 檢查 Meta 廣告規範
4. 參考高效圖片範例

請提供：
- 6 個維度的詳細評分（1-10 分）
- 3-5 個具體優點
- 3-5 個具體缺點
- 每個維度的詳細分析
- 5-7 個可執行的優化建議
- 是否適合投放的判斷
- 目標受眾建議
- 生成優化圖片的提示詞

注意：
- 評分要客觀公正
- 分析要具體明確
- 建議要可執行
- 考慮手機端瀏覽體驗
"""

        # 執行 Agent
        result = await self.agent.run(user_prompt, deps=deps)
        return result.output

    def analyze_image_sync(
        self,
        image: Image.Image,
        df: pd.DataFrame,
        brand_context: Optional[str] = None,
        openai_client: Optional[object] = None
    ) -> ImageAnalysisResult:
        """
        同步版本的圖片分析（用於 Streamlit）
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.analyze_image(image, df, brand_context, openai_client)
        )


# ============================================
# 使用範例
# ============================================

if __name__ == "__main__":
    """測試 Agent"""
    from utils.data_loader import load_meta_ads_data
    from openai import OpenAI
    import os

    # 載入數據
    df = load_meta_ads_data()

    # 載入 OpenAI 客戶端
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    # 創建測試圖片（實際使用時應該是上傳的圖片）
    test_image = Image.new('RGB', (1024, 1024), color='white')

    # 創建 Agent
    agent = ImageAnalysisAgent()

    # 分析圖片
    result = agent.analyze_image_sync(
        image=test_image,
        df=df,
        openai_client=client
    )

    # 輸出結果
    print("=" * 70)
    print("圖片分析結果：")
    print(f"\n總體評分：{result.overall_score:.1f}/10")
    print(f"\n6 大維度評分：")
    print(f"- 視覺吸引力：{result.scores.visual_appeal}/10")
    print(f"- 構圖設計：{result.scores.composition}/10")
    print(f"- 色彩運用：{result.scores.color_usage}/10")
    print(f"- 文字可讀性：{result.scores.text_readability}/10")
    print(f"- 品牌一致性：{result.scores.brand_consistency}/10")
    print(f"- 投放適配性：{result.scores.ad_suitability}/10")

    print(f"\n優點：")
    for strength in result.strengths:
        print(f"✓ {strength}")

    print(f"\n缺點：")
    for weakness in result.weaknesses:
        print(f"• {weakness}")

    print(f"\n優化建議：")
    for i, suggestion in enumerate(result.optimization_suggestions, 1):
        print(f"{i}. {suggestion}")

    print(f"\n適合投放：{'是' if result.is_suitable_for_ads else '否'}")
    print(f"原因：{result.suitability_reason}")
