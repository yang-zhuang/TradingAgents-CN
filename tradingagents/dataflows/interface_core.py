"""
核心股票数据接口模块
包含A股、港股、美股的核心数据获取功能
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

# 导入港股工具
try:
    from .providers.hk.hk_stock import get_hk_stock_data, get_hk_stock_info
    HK_STOCK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ 港股工具不可用: {e}")
    HK_STOCK_AVAILABLE = False

# 导入AKShare港股工具
try:
    from .providers.hk.improved_hk import get_hk_stock_data_akshare, get_hk_stock_info_akshare
    AKSHARE_HK_AVAILABLE = True
except (ImportError, AttributeError) as e:
    logger.warning(f"⚠️ AKShare港股工具不可用: {e}")
    AKSHARE_HK_AVAILABLE = False
    # 定义占位函数
    def get_hk_stock_data_akshare(*args, **kwargs):
        return None
    def get_hk_stock_info_akshare(*args, **kwargs):
        return None

# 导入配置函数
from .interface_config import _get_enabled_hk_data_sources


def get_china_stock_data_tushare(
    ticker: Annotated[str, "中国股票代码，如：000001、600036等"],
    start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
    end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"]
) -> str:
    """
    使用Tushare获取中国A股历史数据
    重定向到data_source_manager，避免循环调用

    Args:
        ticker: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        str: 格式化的股票数据报告
    """
    try:
        from .data_source_manager import get_data_source_manager

        logger.debug(f"📊 [Tushare] 获取{ticker}股票数据...")

        # 添加详细的股票代码追踪日志
        logger.info(f"🔍 [股票代码追踪] get_china_stock_data_tushare 接收到的股票代码: '{ticker}' (类型: {type(ticker)})")
        logger.info(f"🔍 [股票代码追踪] 重定向到data_source_manager")

        manager = get_data_source_manager()
        return manager.get_china_stock_data_tushare(ticker, start_date, end_date)

    except Exception as e:
        logger.error(f"❌ [Tushare] 获取股票数据失败: {e}")
        return f"❌ 获取{ticker}股票数据失败: {e}"


def get_china_stock_info_tushare(
    ticker: Annotated[str, "中国股票代码，如：000001、600036等"]
) -> str:
    """
    使用Tushare获取中国A股基本信息
    直接调用 Tushare 适配器，避免循环调用

    Args:
        ticker: 股票代码

    Returns:
        str: 格式化的股票基本信息
    """
    try:
        from .data_source_manager import get_data_source_manager

        logger.debug(f"📊 [Tushare] 获取{ticker}股票信息...")
        logger.info(f"🔍 [股票代码追踪] get_china_stock_info_tushare 接收到的股票代码: '{ticker}' (类型: {type(ticker)})")
        logger.info(f"🔍 [股票代码追踪] 直接调用 Tushare 适配器")

        manager = get_data_source_manager()

        # 🔥 直接调用 _get_tushare_stock_info()，避免循环调用
        # 不要调用 get_stock_info()，因为它会再次调用 get_china_stock_info_tushare()
        info = manager._get_tushare_stock_info(ticker)

        # 格式化返回字符串
        if info and isinstance(info, dict):
            return f"""股票代码: {info.get('symbol', ticker)}
股票名称: {info.get('name', '未知')}
所属行业: {info.get('industry', '未知')}
上市日期: {info.get('list_date', '未知')}
交易所: {info.get('exchange', '未知')}"""
        else:
            return f"❌ 未找到{ticker}的股票信息"

    except Exception as e:
        logger.error(f"❌ [Tushare] 获取股票信息失败: {e}")
        return f"❌ 获取{ticker}股票信息失败: {e}"


def get_china_stock_fundamentals_tushare(
    ticker: Annotated[str, "中国股票代码，如：000001、600036等"]
) -> str:
    """
    获取中国A股基本面数据（统一接口）
    支持多数据源：MongoDB → Tushare → AKShare → 生成分析

    Args:
        ticker: 股票代码

    Returns:
        str: 基本面分析报告
    """
    try:
        from .data_source_manager import get_data_source_manager

        logger.debug(f"📊 获取{ticker}基本面数据...")
        logger.info(f"🔍 [股票代码追踪] 重定向到data_source_manager.get_fundamentals_data")

        manager = get_data_source_manager()
        # 使用新的统一接口，支持多数据源和自动降级
        return manager.get_fundamentals_data(ticker)

    except Exception as e:
        logger.error(f"❌ 获取基本面数据失败: {e}")
        return f"❌ 获取{ticker}基本面数据失败: {e}"


def get_china_stock_data_unified(
    ticker: Annotated[str, "中国股票代码，如：000001、600036等"],
    start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
    end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"]
) -> str:
    """
    统一的中国A股数据获取接口
    自动使用配置的数据源（默认Tushare），支持备用数据源

    Args:
        ticker: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        str: 格式化的股票数据报告
    """
    # 🔧 智能日期范围处理：自动扩展到配置的回溯天数，处理周末/节假日
    from tradingagents.utils.dataflow_utils import get_trading_date_range
    from app.core.config import get_settings

    original_start_date = start_date
    original_end_date = end_date

    # 从配置获取市场分析回溯天数（默认30天）
    try:
        settings = get_settings()
        lookback_days = settings.MARKET_ANALYST_LOOKBACK_DAYS
        logger.info(f"📅 [配置验证] ===== MARKET_ANALYST_LOOKBACK_DAYS 配置检查 =====")
        logger.info(f"📅 [配置验证] 从配置文件读取: {lookback_days}天")
        logger.info(f"📅 [配置验证] 配置来源: app.core.config.Settings")
        logger.info(f"📅 [配置验证] 环境变量: MARKET_ANALYST_LOOKBACK_DAYS={lookback_days}")
    except Exception as e:
        lookback_days = 30  # 默认30天
        logger.warning(f"⚠️ [配置验证] 无法获取配置，使用默认值: {lookback_days}天")
        logger.warning(f"⚠️ [配置验证] 错误详情: {e}")

    # 使用 end_date 作为目标日期，向前回溯指定天数
    start_date, end_date = get_trading_date_range(end_date, lookback_days=lookback_days)

    logger.info(f"📅 [智能日期] ===== 日期范围计算结果 =====")
    logger.info(f"📅 [智能日期] 原始输入: {original_start_date} 至 {original_end_date}")
    logger.info(f"📅 [智能日期] 回溯天数: {lookback_days}天")
    logger.info(f"📅 [智能日期] 计算结果: {start_date} 至 {end_date}")
    logger.info(f"📅 [智能日期] 实际天数: {(datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days}天")
    logger.info(f"💡 [智能日期] 说明: 自动扩展日期范围以处理周末、节假日和数据延迟")

    # 记录详细的输入参数
    logger.info(f"📊 [统一接口] 开始获取中国股票数据",
               extra={
                   'function': 'get_china_stock_data_unified',
                   'ticker': ticker,
                   'start_date': start_date,
                   'end_date': end_date,
                   'event_type': 'unified_data_call_start'
               })

    # 添加详细的股票代码追踪日志
    logger.info(f"🔍 [股票代码追踪] get_china_stock_data_unified 接收到的原始股票代码: '{ticker}' (类型: {type(ticker)})")
    logger.info(f"🔍 [股票代码追踪] 股票代码长度: {len(str(ticker))}")
    logger.info(f"🔍 [股票代码追踪] 股票代码字符: {list(str(ticker))}")

    start_time = time.time()

    try:
        from .data_source_manager import get_china_stock_data_unified

        result = get_china_stock_data_unified(ticker, start_date, end_date)

        # 记录详细的输出结果
        duration = time.time() - start_time
        result_length = len(result) if result else 0
        is_success = result and "❌" not in result and "错误" not in result

        if is_success:
            logger.info(f"✅ [统一接口] 中国股票数据获取成功",
                       extra={
                           'function': 'get_china_stock_data_unified',
                           'ticker': ticker,
                           'start_date': start_date,
                           'end_date': end_date,
                           'duration': duration,
                           'result_length': result_length,
                           'result_preview': result[:300] + '...' if result_length > 300 else result,
                           'event_type': 'unified_data_call_success'
                       })
        else:
            logger.warning(f"⚠️ [统一接口] 中国股票数据质量异常",
                          extra={
                              'function': 'get_china_stock_data_unified',
                              'ticker': ticker,
                              'start_date': start_date,
                              'end_date': end_date,
                              'duration': duration,
                              'result_length': result_length,
                              'result_preview': result[:300] + '...' if result_length > 300 else result,
                              'event_type': 'unified_data_call_warning'
                          })

        return result

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ [统一接口] 获取股票数据失败: {e}",
                    extra={
                        'function': 'get_china_stock_data_unified',
                        'ticker': ticker,
                        'start_date': start_date,
                        'end_date': end_date,
                        'duration': duration,
                        'error': str(e),
                        'event_type': 'unified_data_call_error'
                    }, exc_info=True)
        return f"❌ 获取{ticker}股票数据失败: {e}"


def get_china_stock_info_unified(
    ticker: Annotated[str, "中国股票代码，如：000001、600036等"]
) -> str:
    """
    统一的中国A股基本信息获取接口
    自动使用配置的数据源（默认Tushare）

    Args:
        ticker: 股票代码

    Returns:
        str: 股票基本信息
    """
    try:
        from .data_source_manager import get_china_stock_info_unified

        logger.info(f"📊 [统一接口] 获取{ticker}基本信息...")

        info = get_china_stock_info_unified(ticker)

        if info and info.get('name'):
            result = f"股票代码: {ticker}\n"
            result += f"股票名称: {info.get('name', '未知')}\n"
            result += f"所属地区: {info.get('area', '未知')}\n"
            result += f"所属行业: {info.get('industry', '未知')}\n"
            result += f"上市市场: {info.get('market', '未知')}\n"
            result += f"上市日期: {info.get('list_date', '未知')}\n"
            # 附加快照行情（若存在）
            cp = info.get('current_price')
            pct = info.get('change_pct')
            vol = info.get('volume')
            if cp is not None:
                result += f"当前价格: {cp}\n"
            if pct is not None:
                try:
                    pct_str = f"{float(pct):+.2f}%"
                except Exception:
                    pct_str = str(pct)
                result += f"涨跌幅: {pct_str}\n"
            if vol is not None:
                result += f"成交量: {vol}\n"
            result += f"数据来源: {info.get('source', 'unknown')}\n"

            return result
        else:
            return f"❌ 未能获取{ticker}的基本信息"

    except Exception as e:
        logger.error(f"❌ [统一接口] 获取股票信息失败: {e}")
        return f"❌ 获取{ticker}股票信息失败: {e}"


def get_hk_stock_data_unified(symbol: str, start_date: str = None, end_date: str = None) -> str:
    """
    获取港股数据的统一接口（根据用户配置选择数据源）

    Args:
        symbol: 港股代码 (如: 0700.HK)
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        str: 格式化的港股数据
    """
    try:
        logger.info(f"🇭🇰 获取港股数据: {symbol}")

        # 🔧 智能日期范围处理：自动扩展到配置的回溯天数，处理周末/节假日
        from tradingagents.utils.dataflow_utils import get_trading_date_range
        from app.core.config import get_settings

        original_start_date = start_date
        original_end_date = end_date

        # 从配置获取市场分析回溯天数（默认60天）
        try:
            settings = get_settings()
            lookback_days = settings.MARKET_ANALYST_LOOKBACK_DAYS
            logger.info(f"📅 [港股配置验证] MARKET_ANALYST_LOOKBACK_DAYS: {lookback_days}天")
        except Exception as e:
            lookback_days = 60  # 默认60天
            logger.warning(f"⚠️ [港股配置验证] 无法获取配置，使用默认值: {lookback_days}天")
            logger.warning(f"⚠️ [港股配置验证] 错误详情: {e}")

        # 使用 end_date 作为目标日期，向前回溯指定天数
        start_date, end_date = get_trading_date_range(end_date, lookback_days=lookback_days)

        logger.info(f"📅 [港股智能日期] 原始输入: {original_start_date} 至 {original_end_date}")
        logger.info(f"📅 [港股智能日期] 回溯天数: {lookback_days}天")
        logger.info(f"📅 [港股智能日期] 计算结果: {start_date} 至 {end_date}")
        logger.info(f"📅 [港股智能日期] 实际天数: {(datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days}天")

        # 🔥 从数据库读取用户启用的数据源配置
        enabled_sources = _get_enabled_hk_data_sources()

        # 按优先级尝试各个数据源
        for source in enabled_sources:
            if source == 'akshare' and AKSHARE_HK_AVAILABLE:
                try:
                    logger.info(f"🔄 使用AKShare获取港股数据: {symbol}")
                    result = get_hk_stock_data_akshare(symbol, start_date, end_date)
                    if result and "❌" not in result:
                        logger.info(f"✅ AKShare港股数据获取成功: {symbol}")
                        return result
                    else:
                        logger.warning(f"⚠️ AKShare返回错误结果，尝试下一个数据源")
                except Exception as e:
                    logger.error(f"⚠️ AKShare港股数据获取失败: {e}，尝试下一个数据源")

            elif source == 'yfinance' and HK_STOCK_AVAILABLE:
                try:
                    logger.info(f"🔄 使用Yahoo Finance获取港股数据: {symbol}")
                    result = get_hk_stock_data(symbol, start_date, end_date)
                    if result and "❌" not in result:
                        logger.info(f"✅ Yahoo Finance港股数据获取成功: {symbol}")
                        return result
                    else:
                        logger.warning(f"⚠️ Yahoo Finance返回错误结果，尝试下一个数据源")
                except Exception as e:
                    logger.error(f"⚠️ Yahoo Finance港股数据获取失败: {e}，尝试下一个数据源")

            elif source == 'finnhub':
                try:
                    # 导入美股数据提供器（支持新旧路径）
                    try:
                        from .providers.us import OptimizedUSDataProvider
                        provider = OptimizedUSDataProvider()
                        get_us_stock_data_cached = provider.get_stock_data
                    except ImportError:
                        from tradingagents.dataflows.providers.us.optimized import get_us_stock_data_cached

                    logger.info(f"🔄 使用FINNHUB获取港股数据: {symbol}")
                    result = get_us_stock_data_cached(symbol, start_date, end_date)
                    if result and "❌" not in result:
                        logger.info(f"✅ FINNHUB港股数据获取成功: {symbol}")
                        return result
                    else:
                        logger.warning(f"⚠️ FINNHUB返回错误结果，尝试下一个数据源")
                except Exception as e:
                    logger.error(f"⚠️ FINNHUB港股数据获取失败: {e}，尝试下一个数据源")

        # 所有数据源都失败
        error_msg = f"❌ 无法获取港股{symbol}数据 - 所有启用的数据源都不可用"
        logger.error(error_msg)
        return error_msg

    except Exception as e:
        logger.error(f"❌ 获取港股数据失败: {e}")
        return f"❌ 获取港股{symbol}数据失败: {e}"


def get_hk_stock_info_unified(symbol: str) -> Dict:
    """
    获取港股信息的统一接口（根据用户配置选择数据源）

    Args:
        symbol: 港股代码

    Returns:
        Dict: 港股信息
    """
    try:
        # 🔥 从数据库读取用户启用的数据源配置
        enabled_sources = _get_enabled_hk_data_sources()

        # 按优先级尝试各个数据源
        for source in enabled_sources:
            if source == 'akshare' and AKSHARE_HK_AVAILABLE:
                try:
                    logger.info(f"🔄 使用AKShare获取港股信息: {symbol}")
                    result = get_hk_stock_info_akshare(symbol)
                    if result and 'error' not in result and not result.get('name', '').startswith('港股'):
                        logger.info(f"✅ AKShare成功获取港股信息: {symbol} -> {result.get('name', 'N/A')}")
                        return result
                    else:
                        logger.warning(f"⚠️ AKShare返回默认信息，尝试下一个数据源")
                except Exception as e:
                    logger.error(f"⚠️ AKShare港股信息获取失败: {e}，尝试下一个数据源")

            elif source == 'yfinance' and HK_STOCK_AVAILABLE:
                try:
                    logger.info(f"🔄 使用Yahoo Finance获取港股信息: {symbol}")
                    result = get_hk_stock_info(symbol)
                    if result and 'error' not in result and not result.get('name', '').startswith('港股'):
                        logger.info(f"✅ Yahoo Finance成功获取港股信息: {symbol} -> {result.get('name', 'N/A')}")
                        return result
                    else:
                        logger.warning(f"⚠️ Yahoo Finance返回默认信息，尝试下一个数据源")
                except Exception as e:
                    logger.error(f"⚠️ Yahoo Finance港股信息获取失败: {e}，尝试下一个数据源")

        # 所有数据源都失败，返回基本信息
        logger.warning(f"⚠️ 所有启用的数据源都失败，使用默认信息: {symbol}")
        return {
            'symbol': symbol,
            'name': f'港股{symbol}',
            'currency': 'HKD',
            'exchange': 'HKG',
            'source': 'fallback'
        }

    except Exception as e:
        logger.error(f"❌ 获取港股信息失败: {e}")
        return {
            'symbol': symbol,
            'name': f'港股{symbol}',
            'currency': 'HKD',
            'exchange': 'HKG',
            'source': 'error',
            'error': str(e)
        }


def get_stock_data_by_market(symbol: str, start_date: str = None, end_date: str = None) -> str:
    """
    根据股票市场类型自动选择数据源获取数据

    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        str: 格式化的股票数据
    """
    try:
        from tradingagents.utils.stock_utils import StockUtils

        market_info = StockUtils.get_market_info(symbol)

        if market_info['is_china']:
            # 中国A股
            return get_china_stock_data_unified(symbol, start_date, end_date)
        elif market_info['is_hk']:
            # 港股
            return get_hk_stock_data_unified(symbol, start_date, end_date)
        else:
            # 美股或其他
            # 导入美股数据提供器（支持新旧路径）
            try:
                from .providers.us import OptimizedUSDataProvider
                provider = OptimizedUSDataProvider()
                return provider.get_stock_data(symbol, start_date, end_date)
            except ImportError:
                from tradingagents.dataflows.providers.us.optimized import get_us_stock_data_cached
                return get_us_stock_data_cached(symbol, start_date, end_date)

    except Exception as e:
        logger.error(f"❌ 获取股票数据失败: {e}")
        return f"❌ 获取股票{symbol}数据失败: {e}"


__all__ = [
    'get_china_stock_data_tushare',
    'get_china_stock_info_tushare',
    'get_china_stock_fundamentals_tushare',
    'get_china_stock_data_unified',
    'get_china_stock_info_unified',
    'get_hk_stock_data_unified',
    'get_hk_stock_info_unified',
    'get_stock_data_by_market',
]