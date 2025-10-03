"""
常數定義 - Meta 廣告儀表板
"""

# ==================== 顏色配置 ====================

# 品質排名顏色
QUALITY_COLORS = {
    '平均以上': '#2ecc71',
    '平均': '#f39c12',
    '平均以下': '#e74c3c',
    '未知': '#95a5a6',
    'Above Average': '#2ecc71',
    'Average': '#f39c12',
    'Below Average': '#e74c3c'
}

# 主題配色
THEME_COLORS = {
    'primary': '#3498db',      # 藍色 - 主要
    'success': '#2ecc71',      # 綠色 - 成功/高績效
    'warning': '#f39c12',      # 橘色 - 警告/中等
    'danger': '#e74c3c',       # 紅色 - 危險/低績效
    'info': '#3498db',         # 藍色 - 資訊
    'secondary': '#95a5a6',    # 灰色 - 次要
    'purple': '#9b59b6',       # 紫色 - 特殊
    'dark': '#34495e',         # 深灰 - 文字
    'light': '#ecf0f1'         # 淺灰 - 背景
}

# 漏斗階段顏色（8個階段）
FUNNEL_COLORS = [
    '#2ecc71',  # 觸及 - 綠色
    '#27ae60',  # 曝光 - 深綠
    '#3498db',  # 點擊 - 藍色
    '#2980b9',  # 頁面瀏覽 - 深藍
    '#9b59b6',  # 內容瀏覽 - 紫色
    '#8e44ad',  # 加購 - 深紫
    '#e67e22',  # 結帳 - 橘色
    '#d35400'   # 購買 - 深橘
]

# 圖表配色方案
CHART_COLOR_SCALES = {
    'performance': 'RdYlGn',      # 紅黃綠 - 績效
    'sequential': 'Blues',         # 藍色系 - 連續值
    'diverging': 'RdBu',          # 紅藍 - 分歧值
    'quality': 'Viridis',         # 多彩 - 品質
    'categorical': 'Set3'         # 分類色
}

# ==================== ROAS 評級 ====================

ROAS_GRADES = {
    'excellent': {'min': 3.0, 'label': '優秀', 'color': THEME_COLORS['success']},
    'good': {'min': 2.0, 'label': '良好', 'color': '#27ae60'},
    'average': {'min': 1.0, 'label': '一般', 'color': THEME_COLORS['warning']},
    'poor': {'min': 0.0, 'label': '需改善', 'color': THEME_COLORS['danger']}
}

# ==================== 漏斗階段定義 ====================

FUNNEL_STAGES = [
    {'name': '觸及', 'field': '觸及人數', 'description': '看到廣告的人數'},
    {'name': '曝光', 'field': '曝光次數', 'description': '廣告顯示次數'},
    {'name': '點擊', 'field': '連結點擊次數', 'description': '點擊廣告的次數'},
    {'name': '頁面瀏覽', 'field': '連結頁面瀏覽次數', 'description': '瀏覽著陸頁的次數'},
    {'name': '內容瀏覽', 'field': '內容瀏覽次數', 'description': '瀏覽產品內容的次數'},
    {'name': '加入購物車', 'field': '加到購物車次數', 'description': '加入購物車的次數'},
    {'name': '開始結帳', 'field': '開始結帳次數', 'description': '開始結帳流程的次數'},
    {'name': '完成購買', 'field': '購買次數', 'description': '完成購買的次數'}
]

# ==================== 成本指標定義 ====================

COST_METRICS = [
    {'name': 'CPC', 'label': '單次點擊成本', 'field': 'CPC（單次連結點擊成本）'},
    {'name': 'CPM', 'label': '千次曝光成本', 'field': 'CPM（每千次廣告曝光成本）'},
    {'name': 'CPA', 'label': '每次購買成本', 'field': '每次購買的成本'},
    {'name': 'CPV', 'label': '每次頁面瀏覽成本', 'field': '每次連結頁面瀏覽成本'}
]

# ==================== 轉換率指標定義 ====================

CONVERSION_METRICS = [
    {'name': 'CTR', 'label': '點擊率', 'field': 'CTR（全部）', 'format': '%.2f%%'},
    {'name': 'ROAS', 'label': 'ROAS', 'field': '購買 ROAS（廣告投資報酬率）', 'format': '%.2f'},
    {'name': '頻率', 'label': '頻率', 'field': '頻率', 'format': '%.2f'}
]

# ==================== 品質排名欄位 ====================

QUALITY_RANKING_FIELDS = [
    {'name': '品質排名', 'field': '品質排名', 'description': '廣告整體品質評級'},
    {'name': '互動率排名', 'field': '互動率排名', 'description': '用戶互動程度評級'},
    {'name': '轉換率排名', 'field': '轉換率排名', 'description': '轉換效果評級'}
]

# ==================== 品質排名映射 ====================

QUALITY_RANKING_MAP = {
    '平均以上': 3,
    'Above Average': 3,
    '平均': 2,
    'Average': 2,
    '平均以下': 1,
    'Below Average': 1,
    '未知': 0,
    '-': 0,
    '': 0
}

# ==================== 數據欄位分類 ====================

# 核心欄位（預設顯示）
CORE_COLUMNS = [
    '行銷活動名稱',
    '廣告組合名稱',
    '廣告名稱',
    '花費金額 (TWD)',
    '購買次數',
    '購買 ROAS（廣告投資報酬率）',
    'CTR（全部）',
    '每次購買的成本',
    '觸及人數',
    '曝光次數',
    '投遞狀態',
    '年齡',
    '性別',
    '品質排名',
    '互動率排名',
    '轉換率排名'
]

# 成效指標欄位
PERFORMANCE_COLUMNS = [
    '購買 ROAS（廣告投資報酬率）',
    '每次購買的成本',
    'CTR（全部）',
    'CTR（連結點閱率）',
    'CPC（單次連結點擊成本）',
    'CPM（每千次廣告曝光成本）',
    '頻率'
]

# 轉換指標欄位
CONVERSION_COLUMNS = [
    '購買次數',
    '加到購物車次數',
    '開始結帳次數',
    '連結點擊次數',
    '連結頁面瀏覽次數',
    '內容瀏覽次數'
]

# 受眾欄位
AUDIENCE_COLUMNS = [
    '年齡',
    '性別',
    '國家',
    '地區'
]

# ==================== 篩選器預設值 ====================

DEFAULT_FILTERS = {
    'roas_min': 0.0,
    'roas_max': 100.0,
    'spend_min': 0,
    'spend_max': 1000000,
    'date_range_days': 90
}

# ==================== 分頁設定 ====================

PAGINATION_OPTIONS = [10, 25, 50, 100, 500, 1000]
DEFAULT_PAGE_SIZE = 50

# ==================== 圖表預設設定 ====================

DEFAULT_CHART_HEIGHT = 400
DEFAULT_FUNNEL_HEIGHT = 600
DEFAULT_HEATMAP_HEIGHT = 500

# ==================== 匯出設定 ====================

EXPORT_FORMATS = ['CSV', 'Excel', '篩選設定']
EXPORT_RANGES = ['當前頁', '當前篩選結果', '全部數據']

# ==================== 效能閾值 ====================

PERFORMANCE_THRESHOLDS = {
    'high_loss_rate': 50,          # 高流失率閾值（%）
    'low_ctr': 2.0,                # 低CTR閾值（%）
    'low_roas': 1.0,               # 低ROAS閾值
    'good_roas': 3.0,              # 良好ROAS閾值
    'min_impressions': 1000,       # 最小曝光次數（用於篩選）
    'fatigue_days': 30,            # 素材疲勞天數閾值
    'high_budget_percentile': 50   # 高預算百分位
}

# ==================== A/B 測試建議 ====================

AB_TEST_RECOMMENDATIONS = {
    '點擊': {
        'tests': ['廣告素材 A/B 測試', 'Headline A/B 測試'],
        'expected_improvement': '15-30%',
        'duration': '7-14 天'
    },
    '頁面瀏覽': {
        'tests': ['Landing Page A/B 測試'],
        'expected_improvement': '20-40%',
        'duration': '14-21 天'
    },
    '加入購物車': {
        'tests': ['價格呈現 A/B 測試'],
        'expected_improvement': '15-25%',
        'duration': '14-21 天'
    },
    '開始結帳': {
        'tests': ['結帳流程 A/B 測試'],
        'expected_improvement': '10-20%',
        'duration': '14-21 天'
    }
}

# ==================== 優化建議模板 ====================

OPTIMIZATION_SUGGESTIONS = {
    'low_quality': {
        'title': '品質排名低',
        'issues': ['廣告素材品質不佳', '隱藏資訊或誤導內容', '用戶反饋負面'],
        'actions': ['使用高解析度圖片/影片', '確保文案真實準確', '改善著陸頁體驗']
    },
    'low_engagement': {
        'title': '互動率排名低',
        'issues': ['素材不吸引人', '目標受眾不精準', 'CTA不明確'],
        'actions': ['測試不同素材風格', '重新定義受眾', '優化標題和文案']
    },
    'low_conversion': {
        'title': '轉換率排名低',
        'issues': ['著陸頁與廣告不符', '價格不具競爭力', '結帳流程複雜'],
        'actions': ['優化著陸頁一致性', '調整價格策略', '簡化購買流程']
    }
}

# ==================== 文字長度建議 ====================

TEXT_LENGTH_RECOMMENDATIONS = {
    'headline': {
        'very_short': (0, 20),
        'short': (21, 40),
        'medium': (41, 60),
        'long': (61, 80),
        'very_long': (81, 200)
    },
    'body': {
        'very_short': (0, 50),
        'short': (51, 100),
        'medium': (101, 150),
        'long': (151, 200),
        'very_long': (201, 1000)
    }
}

# ==================== 投放天數分組 ====================

DAYS_GROUPS = {
    'bins': [0, 7, 14, 21, 30, 60, 1000],
    'labels': ['0-7天', '8-14天', '15-21天', '22-30天', '31-60天', '60天+']
}
