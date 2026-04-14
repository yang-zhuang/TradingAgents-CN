"""
统一数据接口 - interface_v1.py (重构版)
这是模块化重构后的版本，提供所有子模块的统一导入接口

重构说明：
- 原始文件（interface.py）保持1945行不变，作为备份
- 本文件（interface_v1.py）从1945行重构为约200行的统一导入层
- 所有实际功能已分解到以下模块：
  * interface_config.py - 配置管理
  * interface_news.py - 新闻数据
  * interface_fundamentals.py - 基本面分析
  * interface_indicators.py - 技术指标
  * interface_core.py - 核心数据接口
"""

from typing import Annotated, Dict
import time
import os
from datetime import datetime

# 导入统一日志系统
from tradingagents.utils.logging_init import setup_dataflow_logging
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('agents')
logger = setup_dataflow_logging()

# ==================== 导入核心功能 ====================
from .interface_core import (
    get_china_stock_data_tushare,
    get_china_stock_info_tushare,
    get_china_stock_fundamentals_tushare,
    get_china_stock_data_unified,
    get_china_stock_info_unified,
    get_hk_stock_data_unified,
    get_hk_stock_info_unified,
    get_stock_data_by_market,
)

# ==================== 导入新闻功能 ====================
from .interface_news import (
    get_finnhub_news,
    get_finnhub_company_insider_sentiment,
    get_finnhub_company_insider_transactions,
    get_google_news,
    get_reddit_global_news,
    get_reddit_company_news,
    get_stock_news_openai,
    get_global_news_openai,
    get_chinese_social_sentiment,
)

# ==================== 导入基本面功能 ====================
from .interface_fundamentals import (
    get_simfin_balance_sheet,
    get_simfin_cashflow,
    get_simfin_income_statements,
    get_fundamentals_finnhub,
    get_fundamentals_openai,
    _get_fundamentals_alpha_vantage,
    _get_fundamentals_yfinance,
    _get_fundamentals_openai_impl,
)

# ==================== 导入技术指标功能 ====================
from .interface_indicators import (
    get_stock_stats_indicators_window,
    get_stockstats_indicator,
    get_YFin_data_window,
    get_YFin_data_online,
    get_YFin_data,
)

# ==================== 导入配置功能 ====================
from .interface_config import (
    _get_enabled_hk_data_sources,
    _get_enabled_us_data_sources,
    get_config,
    set_config,
    switch_china_data_source,
    get_current_china_data_source,
)

# ==================== 向后兼容的导出 ====================
__all__ = [
    # 核心功能
    'get_china_stock_data_tushare',
    'get_china_stock_info_tushare',
    'get_china_stock_fundamentals_tushare',
    'get_china_stock_data_unified',
    'get_china_stock_info_unified',
    'get_hk_stock_data_unified',
    'get_hk_stock_info_unified',
    'get_stock_data_by_market',

    # 新闻功能
    'get_finnhub_news',
    'get_finnhub_company_insider_sentiment',
    'get_finnhub_company_insider_transactions',
    'get_google_news',
    'get_reddit_global_news',
    'get_reddit_company_news',
    'get_stock_news_openai',
    'get_global_news_openai',
    'get_chinese_social_sentiment',

    # 基本面功能
    'get_simfin_balance_sheet',
    'get_simfin_cashflow',
    'get_simfin_income_statements',
    'get_fundamentals_finnhub',
    'get_fundamentals_openai',
    '_get_fundamentals_alpha_vantage',
    '_get_fundamentals_yfinance',
    '_get_fundamentals_openai_impl',

    # 技术指标功能
    'get_stock_stats_indicators_window',
    'get_stockstats_indicator',
    'get_YFin_data_window',
    'get_YFin_data_online',
    'get_YFin_data',

    # 配置功能
    '_get_enabled_hk_data_sources',
    '_get_enabled_us_data_sources',
    'get_config',
    'set_config',
    'switch_china_data_source',
    'get_current_china_data_source',
]


# ==================== 模块信息 ====================
__version__ = "2.0.0"
__author__ = "TradingAgents Team"
__description__ = "模块化重构后的统一数据接口"

def get_module_info():
    """获取模块信息"""
    return {
        "version": __version__,
        "description": __description__,
        "modules": {
            "interface_config": "配置管理模块",
            "interface_news": "新闻数据模块",
            "interface_fundamentals": "基本面分析模块",
            "interface_indicators": "技术指标模块",
            "interface_core": "核心数据接口模块",
        },
        "total_functions": len(__all__),
        "refactored_from": "1945 lines",
        "refactored_to": f"{len(__all__)} imports + ~153 active lines"
    }