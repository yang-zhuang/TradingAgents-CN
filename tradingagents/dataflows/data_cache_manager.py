#!/usr/bin/env python3
"""
缓存管理模块
提供统一的数据缓存管理功能，支持MongoDB和内存缓存
"""

import pandas as pd
from typing import Optional, Dict, Any
from enum import Enum

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')

# 导入统一日志系统
from tradingagents.utils.logging_init import setup_dataflow_logging
logger = setup_dataflow_logging()


class CacheType(Enum):
    """缓存类型枚举"""
    MONGODB = "mongodb"      # MongoDB持久化缓存
    MEMORY = "memory"        # 内存缓存
    UNIFIED = "unified"      # 统一缓存管理器


class DataCacheManager:
    """数据缓存管理器"""

    def __init__(self):
        """初始化缓存管理器"""
        self.cache_enabled = False
        self.cache_manager = None
        self.use_mongodb_cache = self._check_mongodb_enabled()

        # 初始化统一缓存管理器
        try:
            from tradingagents.dataflows.cache import get_cache
            self.cache_manager = get_cache()
            self.cache_enabled = True
            logger.info("✅ 统一缓存管理器已启用")
        except Exception as e:
            logger.warning(f"⚠️ 统一缓存管理器初始化失败: {e}")

    def _check_mongodb_enabled(self) -> bool:
        """检查是否启用MongoDB缓存"""
        try:
            from tradingagents.config.runtime_settings import use_app_cache_enabled
            return use_app_cache_enabled()
        except Exception:
            return False

    def get_cached_data(self, symbol: str, start_date: str = None, end_date: str = None, max_age_hours: int = 24) -> Optional[pd.DataFrame]:
        """
        从缓存获取数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            max_age_hours: 最大缓存时间（小时）

        Returns:
            DataFrame: 缓存的数据，如果没有则返回None
        """
        if not self.cache_enabled or not self.cache_manager:
            return None

        try:
            cache_key = self.cache_manager.find_cached_stock_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                max_age_hours=max_age_hours
            )

            if cache_key:
                cached_data = self.cache_manager.load_stock_data(cache_key)
                if cached_data is not None and hasattr(cached_data, 'empty') and not cached_data.empty:
                    logger.debug(f"📦 从缓存获取{symbol}数据: {len(cached_data)}条")
                    return cached_data
        except Exception as e:
            logger.warning(f"⚠️ 从缓存读取数据失败: {e}")

        return None

    def save_to_cache(self, symbol: str, data: pd.DataFrame, start_date: str = None, end_date: str = None):
        """
        保存数据到缓存

        Args:
            symbol: 股票代码
            data: 数据
            start_date: 开始日期
            end_date: 结束日期
        """
        if not self.cache_enabled or not self.cache_manager:
            return

        try:
            if data is not None and hasattr(data, 'empty') and not data.empty:
                self.cache_manager.save_stock_data(symbol, data, start_date, end_date)
                logger.debug(f"💾 保存{symbol}数据到缓存: {len(data)}条")
        except Exception as e:
            logger.warning(f"⚠️ 保存数据到缓存失败: {e}")

    def get_mongodb_adapter(self):
        """获取MongoDB适配器"""
        try:
            from tradingagents.dataflows.cache.mongodb_cache_adapter import get_mongodb_cache_adapter
            return get_mongodb_cache_adapter()
        except Exception as e:
            logger.warning(f"⚠️ 获取MongoDB适配器失败: {e}")
            return None

    def is_mongodb_available(self) -> bool:
        """检查MongoDB缓存是否可用"""
        if not self.use_mongodb_cache:
            return False

        try:
            adapter = self.get_mongodb_adapter()
            if adapter and hasattr(adapter, 'use_app_cache') and adapter.use_app_cache:
                if hasattr(adapter, 'db') and adapter.db is not None:
                    return True
            return False
        except Exception:
            return False

    def get_mongodb_data(self, symbol: str, start_date: str, end_date: str, period: str = "daily") -> tuple[pd.DataFrame, str]:
        """
        从MongoDB获取数据

        Returns:
            tuple: (DataFrame, 实际数据源名称)
        """
        try:
            adapter = self.get_mongodb_adapter()
            if not adapter:
                return None, "mongodb"

            df = adapter.get_historical_data(symbol, start_date, end_date, period=period)
            return df, "mongodb"
        except Exception as e:
            logger.error(f"❌ 从MongoDB获取数据失败: {e}")
            return None, "mongodb"

    def clear_cache(self, symbol: str = None):
        """
        清除缓存

        Args:
            symbol: 股票代码，如果为None则清除所有缓存
        """
        if not self.cache_enabled or not self.cache_manager:
            return

        try:
            if symbol:
                logger.debug(f"🗑️ 清除{symbol}的缓存")
                # 这里可以实现特定股票的缓存清理逻辑
            else:
                logger.debug("🗑️ 清除所有缓存")
                # 这里可以实现全部缓存清理逻辑
        except Exception as e:
            logger.warning(f"⚠️ 清除缓存失败: {e}")


__all__ = [
    'DataCacheManager',
    'CacheType',
]
