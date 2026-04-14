"""
数据源配置管理模块
包含数据源配置和切换功能
"""

from typing import Annotated, Dict
import logging

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')


def _get_enabled_hk_data_sources() -> list:
    """
    从数据库读取用户启用的港股数据源配置

    Returns:
        list: 按优先级排序的数据源列表，如 ['akshare', 'yfinance']
    """
    try:
        # 尝试从数据库读取配置
        from app.core.database import get_mongo_db_sync
        db = get_mongo_db_sync()

        # 获取最新的激活配置
        config_data = db.system_configs.find_one(
            {"is_active": True},
            sort=[("version", -1)]
        )

        if config_data and config_data.get('data_source_configs'):
            data_source_configs = config_data.get('data_source_configs', [])

            # 过滤出启用的港股数据源
            enabled_sources = []
            for ds in data_source_configs:
                if not ds.get('enabled', True):
                    continue

                # 检查是否支持港股市场（支持中英文标识）
                market_categories = ds.get('market_categories', [])
                if market_categories:
                    # 支持 '港股' 或 'hk_stocks'
                    if '港股' not in market_categories and 'hk_stocks' not in market_categories:
                        continue

                # 映射数据源类型
                ds_type = ds.get('type', '').lower()
                if ds_type in ['akshare', 'yfinance', 'finnhub']:
                    enabled_sources.append({
                        'type': ds_type,
                        'priority': ds.get('priority', 0)
                    })

            # 按优先级排序（数字越大优先级越高）
            enabled_sources.sort(key=lambda x: x['priority'], reverse=True)

            result = [s['type'] for s in enabled_sources]
            if result:
                logger.info(f"✅ [港股数据源] 从数据库读取: {result}")
                return result
            else:
                logger.warning(f"⚠️ [港股数据源] 数据库中没有启用的港股数据源，使用默认顺序")
        else:
            logger.warning("⚠️ [港股数据源] 数据库中没有配置，使用默认顺序")
    except Exception as e:
        logger.warning(f"⚠️ [港股数据源] 从数据库读取失败: {e}，使用默认顺序")

    # 回退到默认顺序
    return ['akshare', 'yfinance']


def _get_enabled_us_data_sources() -> list:
    """
    从数据库读取用户启用的美股数据源配置

    Returns:
        list: 按优先级排序的数据源列表，如 ['yfinance', 'finnhub']
    """
    try:
        # 尝试从数据库读取配置
        from app.core.database import get_mongo_db_sync
        db = get_mongo_db_sync()

        # 获取最新的激活配置
        config_data = db.system_configs.find_one(
            {"is_active": True},
            sort=[("version", -1)]
        )

        if config_data and config_data.get('data_source_configs'):
            data_source_configs = config_data.get('data_source_configs', [])

            # 过滤出启用的美股数据源
            enabled_sources = []
            for ds in data_source_configs:
                if not ds.get('enabled', True):
                    continue

                # 检查是否支持美股市场（支持中英文标识）
                market_categories = ds.get('market_categories', [])
                if market_categories:
                    # 支持 '美股' 或 'us_stocks'
                    if '美股' not in market_categories and 'us_stocks' not in market_categories:
                        continue

                # 映射数据源类型
                ds_type = ds.get('type', '').lower()
                if ds_type in ['yfinance', 'finnhub']:
                    enabled_sources.append({
                        'type': ds_type,
                        'priority': ds.get('priority', 0)
                    })

            # 按优先级排序（数字越大优先级越高）
            enabled_sources.sort(key=lambda x: x['priority'], reverse=True)

            result = [s['type'] for s in enabled_sources]
            if result:
                logger.info(f"✅ [美股数据源] 从数据库读取: {result}")
                return result
            else:
                logger.warning(f"⚠️ [美股数据源] 数据库中没有启用的美股数据源，使用默认顺序")
        else:
            logger.warning("⚠️ [美股数据源] 数据库中没有配置，使用默认顺序")
    except Exception as e:
        logger.warning(f"⚠️ [美股数据源] 从数据库读取失败: {e}，使用默认顺序")

    # 回退到默认顺序
    return ['yfinance', 'finnhub']


def get_config():
    """获取配置（兼容性包装）"""
    from tradingagents.config.config_manager import config_manager
    return config_manager.load_settings()


def set_config(config):
    """设置配置（兼容性包装）"""
    from tradingagents.config.config_manager import config_manager
    config_manager.save_settings(config)


def switch_china_data_source(
    source: Annotated[str, "数据源名称：tushare, akshare, baostock"]
) -> str:
    """
    切换中国股票数据源

    Args:
        source: 数据源名称

    Returns:
        str: 切换结果
    """
    try:
        from .data_source_manager import get_data_source_manager, ChinaDataSource

        # 映射字符串到枚举（TDX 已移除）
        source_mapping = {
            'tushare': ChinaDataSource.TUSHARE,
            'akshare': ChinaDataSource.AKSHARE,
            'baostock': ChinaDataSource.BAOSTOCK,
            # 'tdx': ChinaDataSource.TDX  # 已移除
        }

        if source.lower() not in source_mapping:
            return f"❌ 不支持的数据源: {source}。支持的数据源: {list(source_mapping.keys())}"

        manager = get_data_source_manager()
        target_source = source_mapping[source.lower()]

        if manager.set_current_source(target_source):
            return f"✅ 数据源已切换到: {source}"
        else:
            return f"❌ 数据源切换失败: {source} 不可用"

    except Exception as e:
        logger.error(f"❌ 数据源切换失败: {e}")
        return f"❌ 数据源切换失败: {e}"


def get_current_china_data_source() -> str:
    """
    获取当前中国股票数据源

    Returns:
        str: 当前数据源信息
    """
    try:
        from .data_source_manager import get_data_source_manager

        manager = get_data_source_manager()
        current_source = manager.get_current_source()

        if current_source:
            source_name = current_source.value
            status = "可用" if current_source.is_available else "不可用"
            return f"当前数据源: {source_name} (状态: {status})"
        else:
            return "当前数据源: 未设置"

    except Exception as e:
        logger.error(f"❌ 获取当前数据源失败: {e}")
        return f"获取当前数据源失败: {e}"


__all__ = [
    '_get_enabled_hk_data_sources',
    '_get_enabled_us_data_sources',
    'get_config',
    'set_config',
    'switch_china_data_source',
    'get_current_china_data_source',
]