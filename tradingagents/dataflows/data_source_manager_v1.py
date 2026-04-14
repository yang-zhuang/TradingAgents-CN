#!/usr/bin/env python3
"""
数据源管理器 - 统一接口层 (重构版)
这是模块化重构后的版本，提供所有子模块的统一导入接口

重构说明：
- 原始文件（data_source_manager.py）保持2474行不变，作为备份
- 本文件（data_source_manager_v1.py）从2474行重构为约200行的统一导入层
- 所有实际功能已分解到以下模块：
  * data_source_enums.py - 数据源枚举定义
  * data_cache_manager.py - 缓存管理
  * china_data_source_manager.py - A股数据源管理器
  * us_data_source_manager.py - 美股数据源管理器
  * data_fetchers.py - 数据获取工具
"""

from typing import Dict, List, Optional, Any

# 导入统一日志系统
from tradingagents.utils.logging_init import setup_dataflow_logging
logger = setup_dataflow_logging()

# ==================== 导入数据源枚举 ====================
from .data_source_enums import (
    ChinaDataSource,
    USDataSource,
)

# ==================== 导入缓存管理 ====================
from .data_cache_manager import (
    DataCacheManager,
    CacheType,
)

# ==================== 导入A股数据源管理器 ====================
from .china_data_source_manager import (
    DataSourceManager,
    get_data_source_manager,
)

# ==================== 导入美股数据源管理器 ====================
from .us_data_source_manager import (
    USDataSourceManager,
    get_us_data_source_manager,
)

# ==================== 导入数据获取工具 ====================
from .data_fetchers import (
    DataFetchers,
)

# ==================== 向后兼容的导出 ====================
__all__ = [
    # 数据源枚举
    'ChinaDataSource',
    'USDataSource',

    # 缓存管理
    'DataCacheManager',
    'CacheType',

    # A股数据源管理器
    'DataSourceManager',
    'get_data_source_manager',

    # 美股数据源管理器
    'USDataSourceManager',
    'get_us_data_source_manager',

    # 数据获取工具
    'DataFetchers',

    # 兼容性接口
    'get_stock_data_service',
    'get_china_stock_data_unified',
    'get_china_stock_info_unified',
    'get_fundamentals_data_unified',
    'get_news_data_unified',
]


# ==================== 兼容性接口 ====================
# 为了兼容旧代码，提供相同的接口

def get_stock_data_service() -> DataSourceManager:
    """
    获取股票数据服务实例（兼容 stock_data_service 接口）

    ⚠️ 此函数为兼容性接口，实际返回 DataSourceManager 实例
    推荐直接使用 get_data_source_manager()

    Returns:
        DataSourceManager: 数据源管理器实例

    Raises:
        Exception: 当获取管理器实例失败时
    """
    try:
        return get_data_source_manager()
    except Exception as e:
        logger.error(f"❌ 获取数据源管理器失败: {e}")
        raise


def get_china_stock_data_unified(symbol: str, start_date: str, end_date: str) -> str:
    """
    统一的中国股票数据获取接口（兼容旧接口）

    Args:
        symbol: 股票代码（格式：6位数字）
        start_date: 开始日期（格式：YYYY-MM-DD）
        end_date: 结束日期（格式：YYYY-MM-DD）

    Returns:
        str: 格式化的股票数据报告

    Raises:
        ValueError: 当参数格式不正确时
        Exception: 当数据获取失败时
    """
    # 参数验证
    if not symbol or not isinstance(symbol, str):
        raise ValueError(f"无效的股票代码: {symbol}")
    if not start_date or not end_date:
        raise ValueError("开始日期和结束日期不能为空")

    # 简化的日志
    logger.info(f"📊 获取股票数据: {symbol} ({start_date} to {end_date})")

    try:
        manager = get_data_source_manager()
        result = manager.get_stock_data(symbol, start_date, end_date)

        # 简化的结果日志
        if result:
            lines = result.split('\n')
            data_lines = [line for line in lines if '2025-' in line and symbol in line]
            logger.info(f"📈 返回数据: {len(lines)}总行数, {len(data_lines)}数据行")
        else:
            logger.warning(f"⚠️ 未获取到股票 {symbol} 的数据")

        return result
    except Exception as e:
        logger.error(f"❌ 获取股票数据失败 {symbol}: {e}")
        raise


def get_china_stock_info_unified(symbol: str) -> Dict:
    """
    统一的中国股票信息获取接口（兼容旧接口）

    Args:
        symbol: 股票代码（格式：6位数字）

    Returns:
        Dict: 股票基本信息

    Raises:
        ValueError: 当股票代码格式不正确时
        Exception: 当获取股票信息失败时
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError(f"无效的股票代码: {symbol}")

    try:
        manager = get_data_source_manager()
        return manager.get_stock_info(symbol)
    except Exception as e:
logger.error(f"❌ 获取股票信息失败 {symbol}: {e}")
        raise


def get_fundamentals_data_unified(symbol: str) -> str:
    """
    统一的基本面数据获取接口（兼容旧接口）

    Args:
        symbol: 股票代码（格式：6位数字）

    Returns:
        str: 基本面分析报告

    Raises:
        ValueError: 当股票代码格式不正确时
        Exception: 当获取基本面数据失败时
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError(f"无效的股票代码: {symbol}")

    try:
        manager = get_data_source_manager()
        return manager.get_fundamentals_data(symbol)
    except Exception as e:
        logger.error(f"❌ 获取基本面数据失败 {symbol}: {e}")
        raise


def get_news_data_unified(symbol: str = None, hours_back: int = 24, limit: int = 20) -> List:
    """
    统一的新闻数据获取接口（兼容旧接口）

    Args:
        symbol: 股票代码，为空则获取市场新闻
        hours_back: 回溯小时数（必须为正整数）
        limit: 返回数量限制（必须为正整数）

    Returns:
        List: 新闻数据列表

    Raises:
        ValueError: 当参数格式不正确时
        Exception: 当获取新闻数据失败时
    """
    # 参数验证
    if symbol is not None and not isinstance(symbol, str):
        raise ValueError(f"无效的股票代码: {symbol}")
    if not isinstance(hours_back, int) or hours_back <= 0:
        raise ValueError(f"无效的回溯小时数: {hours_back}")
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError(f"无效的返回数量限制: {limit}")

    try:
        manager = get_data_source_manager()
        return manager.get_news_data(symbol, hours_back, limit)
    except Exception as e:
        logger.error(f"❌ 获取新闻数据失败: {e}")
        raise


# ==================== 模块信息 ====================
__version__ = "2.0.0"
__author__ = "TradingAgents Team"
__description__ = "模块化重构后的数据源管理器"

def get_module_info():
    """获取模块信息"""
    return {
        "version": __version__,
        "description": __description__,
        "modules": {
            "data_source_enums": "数据源枚举定义",
            "data_cache_manager": "缓存管理模块",
            "china_data_source_manager": "A股数据源管理器",
            "us_data_source_manager": "美股数据源管理器",
            "data_fetchers": "数据获取工具",
        },
        "total_functions": len(__all__),
        "refactored_from": "2474 lines",
        "refactored_to": f"{len(__all__)} imports + ~200 active lines"
    }
