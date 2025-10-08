"""
RAG (Retrieval-Augmented Generation) Service
用於從歷史數據中檢索相關案例，增強 LLM 生成品質

主要功能：
1. 建立向量資料庫（高效廣告素材、優化案例）
2. 檢索相似案例
3. 增強 LLM Prompt
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
import pandas as pd
from datetime import datetime

# LangChain imports
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

class RAGService:
    """RAG 服務類別"""

    def __init__(self, persist_directory: str = "./data/chromadb"):
        """
        初始化 RAG 服務

        Args:
            persist_directory: 向量資料庫儲存路徑
        """
        self.persist_directory = persist_directory
        self.embeddings = None
        self.vectorstore = None

        # 確保目錄存在
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

    def _get_openai_api_key(self) -> Optional[str]:
        """獲取 OpenAI API Key"""
        # 優先從環境變數獲取
        api_key = os.getenv('OPENAI_API_KEY')

        if not api_key:
            # 嘗試從 .env 檔案讀取
            env_file = Path(__file__).parent.parent / '.env'
            if env_file.exists():
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith('OPENAI_API_KEY='):
                            api_key = line.split('=', 1)[1].strip().strip('"\'')
                            break

        if not api_key:
            # 嘗試從 Streamlit secrets 獲取
            try:
                import streamlit as st
                api_key = st.secrets.get("OPENAI_API_KEY")
            except:
                pass

        return api_key

    def initialize_embeddings(self) -> bool:
        """
        初始化 OpenAI Embeddings

        Returns:
            是否成功初始化
        """
        api_key = self._get_openai_api_key()

        if not api_key:
            print("⚠️ 警告：未找到 OPENAI_API_KEY，RAG 功能將無法使用")
            return False

        try:
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",  # 使用較便宜的 embedding 模型
                openai_api_key=api_key
            )
            return True
        except Exception as e:
            print(f"❌ Embeddings 初始化失敗：{str(e)}")
            return False

    def create_ad_creative_knowledge_base(self, df: pd.DataFrame, collection_name: str = "ad_creatives"):
        """
        建立高效廣告素材知識庫

        Args:
            df: 包含廣告數據的 DataFrame
            collection_name: 集合名稱
        """
        if not self.initialize_embeddings():
            raise ValueError("Embeddings 未初始化，請檢查 API Key")

        # 篩選高效廣告（ROAS >= 3.0）
        high_performing_ads = df[df['購買 ROAS（廣告投資報酬率）'] >= 3.0].copy()

        if high_performing_ads.empty:
            print("⚠️ 沒有找到高效廣告（ROAS >= 3.0）")
            return

        # 建立文檔
        documents = []

        for idx, row in high_performing_ads.iterrows():
            # 提取關鍵資訊
            headline = row.get('headline', '未知')
            body = row.get('內文', '')
            cta = row.get('call_to_action_type', '未知')
            roas = row.get('購買 ROAS（廣告投資報酬率）', 0)
            ctr = row.get('CTR（全部）', 0)
            purchases = row.get('購買次數', 0)
            age = row.get('年齡', '未知')
            gender = row.get('性別', '未知')

            # 組合成文檔內容
            content = f"""
【高效廣告素材】
Headline：{headline}
內文：{body[:200] if body else '無'}
CTA：{cta}

【成效指標】
ROAS：{roas:.2f}
CTR：{ctr:.2f}%
購買次數：{purchases:.0f}

【受眾】
年齡：{age}
性別：{gender}

【成功要素分析】
- Headline 長度：{len(str(headline))} 字元
- 是否包含數字：{'是' if any(char.isdigit() for char in str(headline)) else '否'}
- 是否包含問號：{'是' if '?' in str(headline) else '否'}
- CTA 類型：{cta}
"""

            # 建立 metadata
            metadata = {
                'type': 'ad_creative',
                'headline': str(headline),
                'cta': str(cta),
                'roas': float(roas),
                'ctr': float(ctr),
                'purchases': int(purchases),
                'age': str(age),
                'gender': str(gender),
                'created_at': datetime.now().isoformat()
            }

            documents.append(Document(
                page_content=content,
                metadata=metadata
            ))

        # 建立向量資料庫（先刪除舊資料，避免重複）
        print(f"📚 正在建立知識庫：{len(documents)} 筆高效廣告素材...")

        # 嘗試刪除舊的 collection
        try:
            import chromadb
            client = chromadb.PersistentClient(path=self.persist_directory)
            try:
                client.delete_collection(name=collection_name)
                print(f"🗑️ 已刪除舊的 collection: {collection_name}")
            except:
                pass  # collection 不存在，忽略錯誤
        except:
            pass

        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            collection_name=collection_name,
            persist_directory=self.persist_directory
        )

        print(f"✅ 知識庫建立完成！儲存於：{self.persist_directory}")
        print(f"📊 實際儲存文檔數：{self.vectorstore._collection.count()}")

    def load_knowledge_base(self, collection_name: str = "ad_creatives"):
        """
        載入現有知識庫

        Args:
            collection_name: 集合名稱
        """
        if not self.initialize_embeddings():
            raise ValueError("Embeddings 未初始化，請檢查 API Key")

        try:
            self.vectorstore = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            print(f"✅ 知識庫載入成功：{collection_name}")
            return True
        except Exception as e:
            print(f"❌ 知識庫載入失敗：{str(e)}")
            return False

    def add_documents(self, documents: List[Document], collection_name: str = "ad_creatives") -> None:
        """
        向指定知識庫追加文件。若未載入則嘗試載入，無則建立。
        """
        if not documents:
            return

        if not self.initialize_embeddings():
            raise ValueError("Embeddings 未初始化，請檢查 API Key")

        if self.vectorstore is None:
            try:
                self.vectorstore = Chroma(
                    collection_name=collection_name,
                    embedding_function=self.embeddings,
                    persist_directory=self.persist_directory
                )
            except Exception:
                # 若 collection 不存在則建立新的
                self.vectorstore = Chroma.from_documents(
                    documents=documents,
                    embedding=self.embeddings,
                    collection_name=collection_name,
                    persist_directory=self.persist_directory
                )
                return

        self.vectorstore.add_documents(documents)
        self.vectorstore.persist()

    def search_similar_ads(self, query: str, k: int = 5, filter_criteria: Optional[Dict] = None) -> List[Document]:
        """
        搜尋相似廣告

        Args:
            query: 搜尋查詢（例如：「高轉換率的 Headline」）
            k: 返回結果數量
            filter_criteria: 篩選條件（例如：{'roas': {'$gte': 4.0}}）

        Returns:
            相似文檔列表
        """
        if not self.vectorstore:
            raise ValueError("知識庫未載入，請先調用 load_knowledge_base()")

        try:
            if filter_criteria:
                results = self.vectorstore.similarity_search(
                    query=query,
                    k=k,
                    filter=filter_criteria
                )
            else:
                results = self.vectorstore.similarity_search(query=query, k=k)

            return results
        except Exception as e:
            print(f"❌ 搜尋失敗：{str(e)}")
            return []

    def get_context_for_generation(self, query: str, k: int = 3) -> str:
        """
        獲取用於生成的上下文

        Args:
            query: 查詢內容
            k: 檢索結果數量

        Returns:
            格式化的上下文字串
        """
        similar_ads = self.search_similar_ads(query, k=k)

        if not similar_ads:
            return ""

        context = "**參考歷史高效案例**：\n\n"

        for i, doc in enumerate(similar_ads, 1):
            context += f"### 案例 {i}（ROAS {doc.metadata.get('roas', 0):.2f}）\n"
            context += f"{doc.page_content}\n\n"
            context += "---\n\n"

        return context

    def create_optimization_case_knowledge_base(self, cases: List[Dict], collection_name: str = "optimization_cases"):
        """
        建立優化案例知識庫

        Args:
            cases: 優化案例列表，每個案例包含：
                   - problem: 問題描述
                   - solution: 解決方案
                   - result: 優化結果
                   - metrics: 相關指標
            collection_name: 集合名稱
        """
        if not self.initialize_embeddings():
            raise ValueError("Embeddings 未初始化，請檢查 API Key")

        documents = []

        for case in cases:
            content = f"""
【優化案例】
問題：{case.get('problem', '未知')}
解決方案：{case.get('solution', '未知')}
結果：{case.get('result', '未知')}

【改善指標】
{json.dumps(case.get('metrics', {}), ensure_ascii=False, indent=2)}
"""

            metadata = {
                'type': 'optimization_case',
                'problem_type': case.get('problem_type', 'general'),
                'created_at': datetime.now().isoformat(),
                **case.get('metrics', {})
            }

            documents.append(Document(
                page_content=content,
                metadata=metadata
            ))

        print(f"📚 正在建立優化案例知識庫：{len(documents)} 筆案例...")

        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            collection_name=collection_name,
            persist_directory=self.persist_directory
        )

        print(f"✅ 優化案例知識庫建立完成！")

    def get_stats(self) -> Dict[str, Any]:
        """
        獲取知識庫統計資訊

        Returns:
            統計資訊字典
        """
        if not self.vectorstore:
            return {'status': 'not_loaded', 'count': 0}

        try:
            collection = self.vectorstore._collection
            count = collection.count()

            return {
                'status': 'loaded',
                'count': count,
                'persist_directory': self.persist_directory
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }


# 使用範例
if __name__ == "__main__":
    # 初始化 RAG 服務
    rag = RAGService()

    # 範例：建立知識庫（需要實際的 DataFrame）
    # rag.create_ad_creative_knowledge_base(df)

    # 範例：載入知識庫
    # rag.load_knowledge_base()

    # 範例：搜尋相似廣告
    # results = rag.search_similar_ads("高轉換率的 Headline", k=3)

    print("RAG Service 模組載入完成")
