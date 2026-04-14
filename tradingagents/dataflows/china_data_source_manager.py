#!/usr/bin/env python3
"""
A股数据源管理器模块
管理A股数据源的选择和切换，支持Tushare、AKShare、BaoStock等
"""

import os
import time
from typing import List, Optional, Dict, Any
import warnings
import pandas as pd
import numpy as np

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')
warnings.filterwarnings('ignore')

# 导入统一日志系统
from tradingagents.utils.logging_init import setup_dataflow_logging
logger = setup_dataflow_logging()

# 导入统一数据源编码和枚举
from tradingagents.constants import DataSourceCode
from .data_source_enums import ChinaDataSource


class DataSourceManager:
    """A股数据源管理器"""

    def __init__(self):
        """初始化数据源管理器"""
        # 检查是否启用MongoDB缓存
        self.use_mongodb_cache = self._check_mongodb_enabled()

        # 初始化缓存管理器
        from .data_cache_manager import DataCacheManager
        self.cache_manager = DataCacheManager()
        self.cache_enabled = self.cache_manager.cache_enabled

        self.default_source = self._get_default_source()
        self.available_sources = self._check_available_sources()
        self.current_source = self.default_source

        logger.info(f"📊 数据源管理器初始化完成")
        logger.info(f"   MongoDB缓存: {'✅ 已启用' if self.use_mongodb_cache else '❌ 未启用'}")
        logger.info(f"   统一缓存: {'✅ 已启用' if self.cache_enabled else '❌ 未启用'}")
        logger.info(f"   默认数据源: {self.default_source.value}")
        logger.info(f"   可用数据源: {[s.value for s in self.available_sources]}")

    def _check_mongodb_enabled(self) -> bool:
        """检查是否启用MongoDB缓存"""
        from tradingagents.config.runtime_settings import use_app_cache_enabled
        return use_app_cache_enabled()

    def _get_data_source_priority_order(self, symbol: Optional[str] = None) -> List[ChinaDataSource]:
        """
        从数据库获取数据源优先级顺序（用于降级）

        Args:
            symbol: 股票代码，用于识别市场类型（A股/美股/港股）

        Returns:
            按优先级排序的数据源列表（不包含MongoDB，因为MongoDB是最高优先级）
        """
        # 🔥 识别市场类型
        market_category = self._identify_market_category(symbol)

        try:
            # 🔥 从数据库读取数据源配置（使用同步客户端）
            from app.core.database import get_mongo_db_sync
            db = get_mongo_db_sync()
            config_collection = db.system_configs

            # 获取最新的激活配置
            config_data = config_collection.find_one(
                {"is_active": True},
                sort=[("version", -1)]
            )

            if config_data and config_data.get('data_source_configs'):
                data_source_configs = config_data.get('data_source_configs', [])

                # 🔥 过滤出启用的数据源，并按市场分类过滤
                enabled_sources = []
                for ds in data_source_configs:
                    if not ds.get('enabled', True):
                        continue

                    # 检查数据源是否属于当前市场分类
                    market_categories = ds.get('market_categories', [])
                    if market_categories and market_category:
                        # 如果数据源配置了市场分类，只选择匹配的数据源
                        if market_category not in market_categories:
                            continue

                    enabled_sources.append(ds)

                # 按优先级排序（数字越大优先级越高）
                enabled_sources.sort(key=lambda x: x.get('priority', 0), reverse=True)

                # 转换为 ChinaDataSource 枚举（使用统一编码）
                source_mapping = {
                    DataSourceCode.TUSHARE: ChinaDataSource.TUSHARE,
                    DataSourceCode.AKSHARE: ChinaDataSource.AKSHARE,
                    DataSourceCode.BAOSTOCK: ChinaDataSource.BAOSTOCK,
                }

                result = []
                for ds in enabled_sources:
                    ds_type = ds.get('type', '').lower()
                    if ds_type in source_mapping:
                        source = source_mapping[ds_type]
                        # 排除 MongoDB（MongoDB 是最高优先级，不参与降级）
                        if source != ChinaDataSource.MONGODB and source in self.available_sources:
                            result.append(source)

                if result:
                    logger.info(f"✅ [数据源优先级] 市场={market_category or '全部'}, 从数据库读取: {[s.value for s in result]}")
                    return result
                else:
                    logger.warning(f"⚠️ [数据源优先级] 市场={market_category or '全部'}, 数据库配置中没有可用的数据源，使用默认顺序")
            else:
                logger.warning("⚠️ [数据源优先级] 数据库中没有数据源配置，使用默认顺序")
        except Exception as e:
            logger.warning(f"⚠️ [数据源优先级] 从数据库读取失败: {e}，使用默认顺序")

        # 🔥 回退到默认顺序（兼容性）
        # 默认顺序：AKShare > Tushare > BaoStock
        default_order = [
            ChinaDataSource.AKSHARE,
            ChinaDataSource.TUSHARE,
            ChinaDataSource.BAOSTOCK,
        ]
        # 只返回可用的数据源
        return [s for s in default_order if s in self.available_sources]

    def _identify_market_category(self, symbol: Optional[str]) -> Optional[str]:
        """
        识别股票代码所属的市场分类

        Args:
            symbol: 股票代码

        Returns:
            市场分类ID（a_shares/us_stocks/hk_stocks），如果无法识别则返回None
        """
        if not symbol:
            return None

        try:
            from tradingagents.utils.stock_utils import StockUtils, StockMarket

            market = StockUtils.identify_stock_market(symbol)

            # 映射到市场分类ID
            market_mapping = {
                StockMarket.CHINA_A: 'a_shares',
                StockMarket.US: 'us_stocks',
                StockMarket.HONG_KONG: 'hk_stocks',
            }

            category = market_mapping.get(market)
            if category:
                logger.debug(f"🔍 [市场识别] {symbol} → {category}")
            return category
        except Exception as e:
            logger.warning(f"⚠️ [市场识别] 识别失败: {e}")
            return None

    def _get_default_source(self) -> ChinaDataSource:
        """获取默认数据源"""
        # 如果启用MongoDB缓存，MongoDB作为最高优先级数据源
        if self.use_mongodb_cache:
            return ChinaDataSource.MONGODB

        # 从环境变量获取，默认使用AKShare作为第一优先级数据源
        env_source = os.getenv('DEFAULT_CHINA_DATA_SOURCE', DataSourceCode.AKSHARE).lower()

        # 映射到枚举（使用统一编码）
        source_mapping = {
            DataSourceCode.TUSHARE: ChinaDataSource.TUSHARE,
            DataSourceCode.AKSHARE: ChinaDataSource.AKSHARE,
            DataSourceCode.BAOSTOCK: ChinaDataSource.BAOSTOCK,
        }

        return source_mapping.get(env_source, ChinaDataSource.AKSHARE)

    def _check_available_sources(self) -> List[ChinaDataSource]:
        """
        检查可用的数据源

        检查逻辑：
        1. 检查依赖包是否安装（技术可用性）
        2. 检查数据库配置中是否启用（业务可用性）

        Returns:
            可用且已启用的数据源列表
        """
        available = []

        # 🔥 从数据库读取数据源配置，获取启用状态
        enabled_sources_in_db = set()
        try:
            from app.core.database import get_mongo_db_sync
            db = get_mongo_db_sync()
            config_collection = db.system_configs

            # 获取最新的激活配置
            config_data = config_collection.find_one(
                {"is_active": True},
                sort=[("version", -1)]
            )

            if config_data and config_data.get('data_source_configs'):
                data_source_configs = config_data.get('data_source_configs', [])

                # 提取已启用的数据源类型
                for ds in data_source_configs:
                    if ds.get('enabled', True):
                        ds_type = ds.get('type', '').lower()
                        enabled_sources_in_db.add(ds_type)

                logger.info(f"✅ [数据源配置] 从数据库读取到已启用的数据源: {enabled_sources_in_db}")
            else:
                logger.warning("⚠️ [数据源配置] 数据库中没有数据源配置，将检查所有已安装的数据源")
                # 如果数据库中没有配置，默认所有数据源都启用
                enabled_sources_in_db = {'mongodb', 'tushare', 'akshare', 'baostock'}
        except Exception as e:
            logger.warning(f"⚠️ [数据源配置] 从数据库读取失败: {e}，将检查所有已安装的数据源")
            # 如果读取失败，默认所有数据源都启用
            enabled_sources_in_db = {'mongodb', 'tushare', 'akshare', 'baostock'}

        # 检查MongoDB（最高优先级）
        if self.use_mongodb_cache and 'mongodb' in enabled_sources_in_db:
            try:
                from tradingagents.dataflows.cache.mongodb_cache_adapter import get_mongodb_cache_adapter
                adapter = get_mongodb_cache_adapter()
                if adapter.use_app_cache and adapter.db is not None:
                    available.append(ChinaDataSource.MONGODB)
                    logger.info("✅ MongoDB数据源可用且已启用（最高优先级）")
                else:
                    logger.warning("⚠️ MongoDB数据源不可用: 数据库未连接")
            except Exception as e:
                logger.warning(f"⚠️ MongoDB数据源不可用: {e}")
        elif self.use_mongodb_cache and 'mongodb' not in enabled_sources_in_db:
            logger.info("ℹ️ MongoDB数据源已在数据库中禁用")

        # 从数据库读取数据源配置
        datasource_configs = self._get_datasource_configs_from_db()

        # 检查Tushare
        if 'tushare' in enabled_sources_in_db:
            try:
                import tushare as ts
                # 优先从数据库配置读取 API Key，其次从环境变量读取
                token = datasource_configs.get('tushare', {}).get('api_key') or os.getenv('TUSHARE_TOKEN')
                if token:
                    available.append(ChinaDataSource.TUSHARE)
                    source = "数据库配置" if datasource_configs.get('tushare', {}).get('api_key') else "环境变量"
                    logger.info(f"✅ Tushare数据源可用且已启用 (API Key来源: {source})")
                else:
                    logger.warning("⚠️ Tushare数据源不可用: API Key未配置（数据库和环境变量均未找到）")
            except ImportError:
                logger.warning("⚠️ Tushare数据源不可用: 库未安装")
        else:
            logger.info("ℹ️ Tushare数据源已在数据库中禁用")

        # 检查AKShare
        if 'akshare' in enabled_sources_in_db:
            try:
                import akshare as ak
                available.append(ChinaDataSource.AKSHARE)
                logger.info("✅ AKShare数据源可用且已启用")
            except ImportError:
                logger.warning("⚠️ AKShare数据源不可用: 库未安装")
        else:
            logger.info("ℹ️ AKShare数据源已在数据库中禁用")

        # 检查BaoStock
        if 'baostock' in enabled_sources_in_db:
            try:
                import baostock as bs
                available.append(ChinaDataSource.BAOSTOCK)
                logger.info(f"✅ BaoStock数据源可用且已启用")
            except ImportError:
                logger.warning(f"⚠️ BaoStock数据源不可用: 库未安装")
        else:
            logger.info("ℹ️ BaoStock数据源已在数据库中禁用")

        return available

    def _get_datasource_configs_from_db(self) -> dict:
        """从数据库读取数据源配置（包括 API Key）"""
        try:
            from app.core.database import get_mongo_db_sync
            db = get_mongo_db_sync()

            # 从 system_configs 集合读取激活的配置
            config = db.system_configs.find_one({"is_active": True})
            if not config:
                return {}

            # 提取数据源配置
            datasource_configs = config.get('data_source_configs', [])

            # 构建配置字典 {数据源名称: {api_key, api_secret, ...}}
            result = {}
            for ds_config in datasource_configs:
                name = ds_config.get('name', '').lower()
                result[name] = {
                    'api_key': ds_config.get('api_key', ''),
                    'api_secret': ds_config.get('api_secret', ''),
                    'config_params': ds_config.get('config_params', {})
                }

            return result
        except Exception as e:
            logger.warning(f"⚠️ 从数据库读取数据源配置失败: {e}")
            return {}

    def get_current_source(self) -> ChinaDataSource:
        """获取当前数据源"""
        return self.current_source

    def set_current_source(self, source: ChinaDataSource) -> bool:
        """设置当前数据源"""
        if source in self.available_sources:
            self.current_source = source
            logger.info(f"✅ 数据源已切换到: {source.value}")
            return True
        else:
            logger.error(f"❌ 数据源不可用: {source.value}")
            return False


# 全局数据源管理器实例
_data_source_manager = None

def get_data_source_manager() -> DataSourceManager:
    """获取全局数据源管理器实例"""
    global _data_source_manager
    if _data_source_manager is None:
        _data_source_manager = DataSourceManager()
    return _data_source_manager


__all__ = [
    'DataSourceManager',
    'get_data_source_manager',
]
