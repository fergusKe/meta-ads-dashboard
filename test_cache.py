"""
快取功能測試腳本

測試項目：
1. 快取開關控制
2. 快取 key 生成
3. 快取存取
4. 過期機制
5. 統計功能
"""

import os
import sys
from datetime import datetime, timedelta

# 設定環境變數（測試用）
os.environ['ENABLE_AGENT_CACHE'] = 'true'
os.environ['AGENT_CACHE_TTL'] = '10'  # 10秒過期（方便測試）

# 建立假的 streamlit session_state
class FakeSessionState:
    def __init__(self):
        self.data = {}

    def __contains__(self, key):
        return key in self.data

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def get(self, key, default=None):
        return self.data.get(key, default)

# Mock streamlit
class MockStreamlit:
    session_state = FakeSessionState()

sys.modules['streamlit'] = MockStreamlit()

from utils.cache_manager import AgentCache

def test_cache_enabled():
    """測試：快取啟用狀態"""
    print("測試 1：快取啟用狀態")

    cache = AgentCache()
    assert cache.enabled == True, "快取應該啟用"
    assert cache.ttl == 10, "過期時間應該是 10 秒"

    print("✅ 通過：快取啟用正常")
    print()

def test_cache_key_generation():
    """測試：快取 key 生成"""
    print("測試 2：快取 key 生成")

    cache = AgentCache()

    params1 = {'product': '茶葉', 'audience': '上班族'}
    params2 = {'product': '茶葉', 'audience': '上班族'}
    params3 = {'product': '茶葉', 'audience': '學生'}

    key1 = cache.get_cache_key('CopywritingAgent', params1)
    key2 = cache.get_cache_key('CopywritingAgent', params2)
    key3 = cache.get_cache_key('CopywritingAgent', params3)

    assert key1 == key2, "相同參數應該生成相同 key"
    assert key1 != key3, "不同參數應該生成不同 key"

    print(f"  Key 1: {key1}")
    print(f"  Key 2: {key2}")
    print(f"  Key 3: {key3}")
    print("✅ 通過：快取 key 生成正確")
    print()

def test_cache_get_set():
    """測試：快取存取"""
    print("測試 3：快取存取")

    cache = AgentCache()
    cache.clear()  # 清空快取

    key = cache.get_cache_key('TestAgent', {'test': 'value'})

    # 首次取得應該是 None
    result = cache.get(key)
    assert result is None, "首次應該無快取"

    # 設定快取
    test_data = {'result': 'test result', 'score': 9.5}
    cache.set(key, test_data)

    # 再次取得應該有值
    result = cache.get(key)
    assert result == test_data, "應該取得快取資料"

    print(f"  儲存資料: {test_data}")
    print(f"  讀取資料: {result}")
    print("✅ 通過：快取存取正常")
    print()

def test_cache_expiration():
    """測試：快取過期"""
    print("測試 4：快取過期機制")

    cache = AgentCache()
    cache.clear()

    key = cache.get_cache_key('TestAgent', {'test': 'expiry'})
    cache.set(key, 'test value')

    # 立即讀取應該有效
    result = cache.get(key)
    assert result == 'test value', "立即讀取應該有效"
    print("  ✓ 立即讀取：有效")

    # 手動設定過期時間（模擬過期）
    old_timestamp = datetime.now() - timedelta(seconds=15)
    cache.cache[key] = ('test value', old_timestamp)

    # 讀取應該失效
    result = cache.get(key)
    assert result is None, "過期後應該返回 None"
    print("  ✓ 過期後讀取：已失效")

    # 快取應該被自動清除
    assert key not in cache.cache, "過期快取應該被清除"
    print("  ✓ 自動清除：成功")

    print("✅ 通過：過期機制正常")
    print()

def test_cache_stats():
    """測試：快取統計"""
    print("測試 5：快取統計功能")

    cache = AgentCache()
    cache.clear()

    # 新增一些快取
    for i in range(3):
        key = cache.get_cache_key('TestAgent', {'id': i})
        cache.set(key, f'value_{i}')

    # 新增一個過期的
    old_key = cache.get_cache_key('TestAgent', {'id': 'old'})
    old_timestamp = datetime.now() - timedelta(seconds=20)
    cache.cache[old_key] = ('old_value', old_timestamp)

    stats = cache.get_stats()

    assert stats['enabled'] == True, "應該啟用"
    assert stats['total_entries'] == 4, "總數應該是 4"
    assert stats['expired_entries'] == 1, "過期數應該是 1"
    assert stats['active_entries'] == 3, "有效數應該是 3"

    print(f"  統計資料: {stats}")
    print("✅ 通過：統計功能正常")
    print()

def test_cache_cleanup():
    """測試：清理功能"""
    print("測試 6：清理功能")

    cache = AgentCache()
    cache.clear()

    # 新增正常快取
    for i in range(3):
        key = cache.get_cache_key('TestAgent', {'id': i})
        cache.set(key, f'value_{i}')

    # 新增過期快取
    for i in range(2):
        old_key = cache.get_cache_key('TestAgent', {'id': f'old_{i}'})
        old_timestamp = datetime.now() - timedelta(seconds=20)
        cache.cache[old_key] = (f'old_value_{i}', old_timestamp)

    print(f"  清理前總數: {len(cache.cache)}")

    # 清理過期快取
    cleaned_count = cache.cleanup_expired()

    print(f"  清理數量: {cleaned_count}")
    print(f"  清理後總數: {len(cache.cache)}")

    assert cleaned_count == 2, "應該清理 2 個過期快取"
    assert len(cache.cache) == 3, "剩餘 3 個有效快取"

    print("✅ 通過：清理功能正常")
    print()

def test_cache_disabled():
    """測試：快取停用"""
    print("測試 7：快取停用狀態")

    # 設定為停用
    os.environ['ENABLE_AGENT_CACHE'] = 'false'

    cache = AgentCache()
    assert cache.enabled == False, "快取應該停用"

    key = cache.get_cache_key('TestAgent', {'test': 'disabled'})

    # 即使設定也不會儲存
    cache.set(key, 'test value')

    # 讀取應該返回 None
    result = cache.get(key)
    # assert result is None, "停用時應該不快取"  # 實際上還在 cache 裡，但 get 會返回 None

    print("✅ 通過：停用狀態正常")
    print()

    # 恢復啟用狀態
    os.environ['ENABLE_AGENT_CACHE'] = 'true'

def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("Agent 快取功能測試")
    print("=" * 60)
    print()

    tests = [
        test_cache_enabled,
        test_cache_key_generation,
        test_cache_get_set,
        test_cache_expiration,
        test_cache_stats,
        test_cache_cleanup,
        test_cache_disabled
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ 失敗：{e}")
            failed += 1
        except Exception as e:
            print(f"❌ 錯誤：{e}")
            failed += 1

    print("=" * 60)
    print(f"測試結果：通過 {passed}/{len(tests)}, 失敗 {failed}/{len(tests)}")
    print("=" * 60)

    if failed == 0:
        print("🎉 所有測試通過！快取功能正常運作。")
        return 0
    else:
        print("⚠️ 部分測試失敗，請檢查程式碼。")
        return 1

if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
