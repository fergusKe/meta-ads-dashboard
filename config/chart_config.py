"""
圖表樣式配置 - Meta 廣告儀表板
"""

from .constants import THEME_COLORS, FUNNEL_COLORS, QUALITY_COLORS

# ==================== 通用圖表配置 ====================

DEFAULT_LAYOUT = {
    'font': {
        'family': 'Arial, sans-serif',
        'size': 12,
        'color': THEME_COLORS['dark']
    },
    'plot_bgcolor': 'white',
    'paper_bgcolor': 'white',
    'hovermode': 'closest',
    'showlegend': True,
    'legend': {
        'orientation': 'h',
        'yanchor': 'bottom',
        'y': -0.2,
        'xanchor': 'center',
        'x': 0.5
    }
}

# ==================== 漏斗圖配置 ====================

FUNNEL_CONFIG = {
    'layout': {
        **DEFAULT_LAYOUT,
        'height': 600,
        'margin': {'l': 20, 'r': 20, 't': 40, 'b': 20}
    },
    'marker': {
        'color': FUNNEL_COLORS,
        'line': {
            'width': 2,
            'color': 'white'
        }
    },
    'connector': {
        'line': {
            'color': 'gray',
            'width': 2
        }
    },
    'textposition': 'inside',
    'textinfo': 'value+percent initial'
}

# ==================== 圓餅圖配置 ====================

PIE_CONFIG = {
    'layout': {
        **DEFAULT_LAYOUT,
        'height': 400,
        'showlegend': True
    },
    'hole': 0.4,  # 甜甜圈圖
    'textposition': 'auto',
    'textinfo': 'label+percent',
    'marker': {
        'line': {
            'color': 'white',
            'width': 2
        }
    }
}

# ==================== 長條圖配置 ====================

BAR_CONFIG = {
    'layout': {
        **DEFAULT_LAYOUT,
        'height': 450,
        'bargap': 0.1,
        'bargroupgap': 0.1
    },
    'marker': {
        'line': {
            'width': 1,
            'color': 'white'
        }
    },
    'textposition': 'outside',
    'texttemplate': '%{text:.2f}'
}

# ==================== 散點圖配置 ====================

SCATTER_CONFIG = {
    'layout': {
        **DEFAULT_LAYOUT,
        'height': 500
    },
    'mode': 'markers',
    'marker': {
        'size': 10,
        'opacity': 0.6,
        'line': {
            'width': 1,
            'color': 'white'
        }
    }
}

# ==================== 折線圖配置 ====================

LINE_CONFIG = {
    'layout': {
        **DEFAULT_LAYOUT,
        'height': 450
    },
    'mode': 'lines+markers',
    'line': {
        'width': 3
    },
    'marker': {
        'size': 8
    }
}

# ==================== 熱力圖配置 ====================

HEATMAP_CONFIG = {
    'layout': {
        **DEFAULT_LAYOUT,
        'height': 500
    },
    'colorscale': 'RdYlGn',
    'texttemplate': '%{z:.2f}',
    'textfont': {
        'size': 12
    },
    'showscale': True,
    'colorbar': {
        'title': '',
        'thickness': 15,
        'len': 0.7
    }
}

# ==================== 瀑布圖配置 ====================

WATERFALL_CONFIG = {
    'layout': {
        **DEFAULT_LAYOUT,
        'height': 500,
        'showlegend': False
    },
    'connector': {
        'line': {
            'color': 'rgb(63, 63, 63)',
            'width': 2
        }
    },
    'decreasing': {
        'marker': {
            'color': THEME_COLORS['danger']
        }
    },
    'increasing': {
        'marker': {
            'color': THEME_COLORS['success']
        }
    },
    'totals': {
        'marker': {
            'color': THEME_COLORS['primary']
        }
    },
    'textposition': 'outside'
}

# ==================== 雙軸圖配置 ====================

DUAL_AXIS_CONFIG = {
    'layout': {
        **DEFAULT_LAYOUT,
        'height': 450,
        'hovermode': 'x unified'
    },
    'yaxis': {
        'title': '',
        'side': 'left',
        'showgrid': True,
        'gridcolor': '#f0f0f0'
    },
    'yaxis2': {
        'title': '',
        'side': 'right',
        'overlaying': 'y',
        'showgrid': False
    }
}

# ==================== 氣泡圖配置 ====================

BUBBLE_CONFIG = {
    'layout': {
        **DEFAULT_LAYOUT,
        'height': 500
    },
    'mode': 'markers',
    'marker': {
        'sizemode': 'diameter',
        'sizeref': 2,
        'sizemin': 4,
        'opacity': 0.6,
        'line': {
            'width': 2,
            'color': 'white'
        }
    }
}

# ==================== 直方圖配置 ====================

HISTOGRAM_CONFIG = {
    'layout': {
        **DEFAULT_LAYOUT,
        'height': 400,
        'bargap': 0.05
    },
    'marker': {
        'line': {
            'width': 1,
            'color': 'white'
        }
    },
    'nbins': 30
}

# ==================== KPI 卡片配置 ====================

KPI_CARD_STYLE = """
<div style="
    background: linear-gradient(135deg, {bg_color_start} 0%, {bg_color_end} 100%);
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    text-align: center;
    color: white;
">
    <h4 style="margin: 0; font-size: 14px; opacity: 0.9;">{label}</h4>
    <h2 style="margin: 10px 0; font-size: 32px; font-weight: bold;">{value}</h2>
    <p style="margin: 0; font-size: 12px; opacity: 0.8;">{delta}</p>
</div>
"""

KPI_COLORS = {
    'primary': {'start': '#3498db', 'end': '#2980b9'},
    'success': {'start': '#2ecc71', 'end': '#27ae60'},
    'warning': {'start': '#f39c12', 'end': '#e67e22'},
    'danger': {'start': '#e74c3c', 'end': '#c0392b'},
    'purple': {'start': '#9b59b6', 'end': '#8e44ad'},
    'info': {'start': '#1abc9c', 'end': '#16a085'}
}

# ==================== 圖表通用函數 ====================

def get_layout_config(chart_type='default', **kwargs):
    """
    獲取圖表佈局配置

    Args:
        chart_type: 圖表類型
        **kwargs: 額外配置參數

    Returns:
        dict: 佈局配置
    """
    configs = {
        'funnel': FUNNEL_CONFIG,
        'pie': PIE_CONFIG,
        'bar': BAR_CONFIG,
        'scatter': SCATTER_CONFIG,
        'line': LINE_CONFIG,
        'heatmap': HEATMAP_CONFIG,
        'waterfall': WATERFALL_CONFIG,
        'dual_axis': DUAL_AXIS_CONFIG,
        'bubble': BUBBLE_CONFIG,
        'histogram': HISTOGRAM_CONFIG,
        'default': {'layout': DEFAULT_LAYOUT}
    }

    config = configs.get(chart_type, configs['default']).copy()

    # 合併自訂配置
    if 'layout' in config and kwargs:
        config['layout'].update(kwargs)

    return config

def apply_quality_colors(data, quality_field='品質排名'):
    """
    應用品質排名顏色

    Args:
        data: 數據
        quality_field: 品質欄位名稱

    Returns:
        list: 顏色列表
    """
    if quality_field in data:
        return [QUALITY_COLORS.get(val, THEME_COLORS['secondary']) for val in data[quality_field]]
    return None

def get_performance_color(value, metric='roas'):
    """
    根據績效值獲取顏色

    Args:
        value: 數值
        metric: 指標類型（roas, ctr, cpa等）

    Returns:
        str: 顏色碼
    """
    if metric == 'roas':
        if value >= 3.0:
            return THEME_COLORS['success']
        elif value >= 2.0:
            return '#27ae60'
        elif value >= 1.0:
            return THEME_COLORS['warning']
        else:
            return THEME_COLORS['danger']

    elif metric == 'ctr':
        if value >= 3.0:
            return THEME_COLORS['success']
        elif value >= 2.0:
            return THEME_COLORS['warning']
        else:
            return THEME_COLORS['danger']

    return THEME_COLORS['primary']

def format_number(value, format_type='number'):
    """
    格式化數字顯示

    Args:
        value: 數值
        format_type: 格式類型（number, currency, percent等）

    Returns:
        str: 格式化後的字串
    """
    if value is None or (isinstance(value, float) and value != value):  # NaN check
        return 'N/A'

    if format_type == 'currency':
        return f'NT$ {value:,.0f}'
    elif format_type == 'percent':
        return f'{value:.2f}%'
    elif format_type == 'decimal':
        return f'{value:.2f}'
    elif format_type == 'integer':
        return f'{value:,.0f}'
    else:
        return f'{value:,}'
