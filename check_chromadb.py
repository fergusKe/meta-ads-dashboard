#!/usr/bin/env python3
"""檢查 ChromaDB 實際儲存的數據"""
from utils.rag_service import RAGService
from utils.data_loader import load_meta_ads_data

# 載入數據
df = load_meta_ads_data()
high_performing_count = len(df[df['購買 ROAS（廣告投資報酬率）'] >= 3.0])
print(f"📊 數據中高效廣告數（ROAS >= 3.0）: {high_performing_count} 筆")

# 檢查 RAG
rag = RAGService()
if rag.load_knowledge_base("ad_creatives"):
    stats = rag.get_stats()
    print(f"\n📚 ChromaDB 知識庫狀態:")
    print(f"  - 狀態: {stats['status']}")
    print(f"  - 文檔數量: {stats['count']} 筆")
    print(f"  - 儲存位置: {stats['persist_directory']}")

    # 獲取實際的 collection
    collection = rag.vectorstore._collection

    # 檢查是否有重複
    print(f"\n🔍 詳細檢查:")
    print(f"  - Collection 名稱: {collection.name}")
    print(f"  - Collection count: {collection.count()}")

    # 獲取一些樣本看看
    results = collection.get(limit=5, include=['metadatas'])
    print(f"\n📋 前 5 筆資料的 metadata:")
    for i, metadata in enumerate(results['metadatas'][:5], 1):
        print(f"  {i}. Headline: {metadata.get('headline', 'N/A')[:50]}... | ROAS: {metadata.get('roas', 0):.2f}")

    # 檢查是否有重複的 headline
    all_results = collection.get(include=['metadatas'])
    headlines = [m.get('headline') for m in all_results['metadatas']]
    unique_headlines = set(headlines)

    print(f"\n🔄 重複檢查:")
    print(f"  - 總文檔數: {len(headlines)}")
    print(f"  - 唯一 headline 數: {len(unique_headlines)}")
    print(f"  - 是否有重複: {'是' if len(headlines) != len(unique_headlines) else '否'}")

    if len(headlines) != len(unique_headlines):
        print(f"  ⚠️ 發現重複！平均每個 headline 重複 {len(headlines) / len(unique_headlines):.1f} 次")
else:
    print("❌ 知識庫載入失敗")
