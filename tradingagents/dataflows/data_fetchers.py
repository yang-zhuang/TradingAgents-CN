#!/usr/bin/env python3
"""
数据获取工具模块
包含具体的数据获取实现、数据格式化和标准化、错误处理和重试逻辑
"""

import asyncio
import time
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')

# 导入统一日志系统
from tradingagents.utils.logging_init import setup_dataflow_logging
logger = setup_dataflow_logging()


class DataFetchers:
    """数据获取工具类"""

    @staticmethod
    def get_volume_safely(data: pd.DataFrame) -> float:
        """
        安全获取成交量数据

        Args:
            data: 股票数据DataFrame

        Returns:
            float: 成交量，如果获取失败返回0
        """
        try:
            if 'volume' in data.columns:
                return data['volume'].iloc[-1]
            elif 'vol' in data.columns:
                return data['vol'].iloc[-1]
            else:
                return 0
        except Exception:
            return 0

    @staticmethod
    def format_stock_data_response(data: pd.DataFrame, symbol: str, stock_name: str,
                                   start_date: str, end_date: str) -> str:
        """
        格式化股票数据响应（包含技术指标）

        Args:
            data: 股票数据DataFrame
            symbol: 股票代码
            stock_name: 股票名称
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            str: 格式化的数据报告（包含技术指标）
        """
        try:
            original_data_count = len(data)
            logger.info(f"📊 [技术指标] 开始计算技术指标，原始数据: {original_data_count}条")

            # 🔧 计算技术指标（使用完整数据）
            # 确保数据按日期排序
            if 'date' in data.columns:
                data = data.sort_values('date')

            # 计算移动平均线
            data['ma5'] = data['close'].rolling(window=5, min_periods=1).mean()
            data['ma10'] = data['close'].rolling(window=10, min_periods=1).mean()
            data['ma20'] = data['close'].rolling(window=20, min_periods=1).mean()
            data['ma60'] = data['close'].rolling(window=60, min_periods=1).mean()

            # 计算RSI（相对强弱指标）- 同花顺风格：使用中国式SMA（EMA with adjust=True）
            # 参考：https://blog.csdn.net/u011218867/article/details/117427927
            # 同花顺/通达信的RSI使用SMA函数，等价于pandas的ewm(com=N-1, adjust=True)
            delta = data['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            # RSI6 - 使用中国式SMA
            avg_gain6 = gain.ewm(com=5, adjust=True).mean()  # com = N - 1
            avg_loss6 = loss.ewm(com=5, adjust=True).mean()
            rs6 = avg_gain6 / avg_loss6.replace(0, np.nan)
            data['rsi6'] = 100 - (100 / (1 + rs6))

            # RSI12 - 使用中国式SMA
            avg_gain12 = gain.ewm(com=11, adjust=True).mean()
            avg_loss12 = loss.ewm(com=11, adjust=True).mean()
            rs12 = avg_gain12 / avg_loss12.replace(0, np.nan)
            data['rsi12'] = 100 - (100 / (1 + rs12))

            # RSI24 - 使用中国式SMA
            avg_gain24 = gain.ewm(com=23, adjust=True).mean()
            avg_loss24 = loss.ewm(com=23, adjust=True).mean()
            rs24 = avg_gain24 / avg_loss24.replace(0, np.nan)
            data['rsi24'] = 100 - (100 / (1 + rs24))

            # 保留RSI14作为国际标准参考（使用简单移动平均）
            gain14 = gain.rolling(window=14, min_periods=1).mean()
            loss14 = loss.rolling(window=14, min_periods=1).mean()
            rs14 = gain14 / loss14.replace(0, np.nan)
            data['rsi14'] = 100 - (100 / (1 + rs14))

            # 计算MACD
            ema12 = data['close'].ewm(span=12, adjust=False).mean()
            ema26 = data['close'].ewm(span=26, adjust=False).mean()
            data['macd_dif'] = ema12 - ema26
            data['macd_dea'] = data['macd_dif'].ewm(span=9, adjust=False).mean()
            data['macd'] = (data['macd_dif'] - data['macd_dea']) * 2

            # 计算布林带
            data['boll_mid'] = data['close'].rolling(window=20, min_periods=1).mean()
            std20 = data['close'].rolling(window=20, min_periods=1).std()
            data['boll_ub'] = data['boll_mid'] + 2 * std20
            data['boll_lb'] = data['boll_mid'] - 2 * std20

            # 生成输出字符串
            output = f"""
# {stock_name} ({symbol}) 历史数据
## 时间范围: {start_date} 至 {end_date}

### 📊 最新价格信息
- 收盘价: {data['close'].iloc[-1]:.2f}
- 最高价: {data['high'].iloc[-1]:.2f}
- 最低价: {data['low'].iloc[-1]:.2f}
- 开盘价: {data['open'].iloc[-1]:.2f}
- 成交量: {data['volume'].iloc[-1]:.0f}

### 📈 技术指标
#### 移动平均线
- MA5: {data['ma5'].iloc[-1]:.2f}
- MA10: {data['ma10'].iloc[-1]:.2f}
- MA20: {data['ma20'].iloc[-1]:.2f}
- MA60: {data['ma60'].iloc[-1]:.2f}

#### RSI相对强弱指标
- RSI6: {data['rsi6'].iloc[-1]:.2f}
- RSI12: {data['rsi12'].iloc[-1]:.2f}
- RSI14: {data['rsi14'].iloc[-1]:.2f}
- RSI24: {data['rsi24'].iloc[-1]:.2f}

#### MACD指标
- DIF: {data['macd_dif'].iloc[-1]:.2f}
- DEA: {data['macd_dea'].iloc[-1]:.2f}
- MACD: {data['macd'].iloc[-1]:.2f}

#### 布林带
- 中轨: {data['boll_mid'].iloc[-1]:.2f}
- 上轨: {data['boll_ub'].iloc[-1]:.2f}
- 下轨: {data['boll_lb'].iloc[-1]:.2f}

### 📅 历史数据
"""
            # 添加最近10天的数据
            recent_data = data.tail(10)
            for _, row in recent_data.iterrows():
                date_str = row.get('date', 'N/A')
                output += f"\n{date_str}: 收盘 {row['close']:.2f}, 成交量 {row['volume']:.0f}"

            return output

        except Exception as e:
            logger.error(f"❌ 格式化股票数据失败: {e}")
            return f"❌ 格式化数据失败: {str(e)}"

    @staticmethod
    def get_event_loop():
        """获取或创建事件循环"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop
        except RuntimeError:
            # 在线程池中没有事件循环，创建新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    @staticmethod
    def get_tushare_adapter():
        """获取Tushare提供器"""
        try:
            from tradingagents.dataflows.providers.china.tushare import get_tushare_provider
            return get_tushare_provider()
        except ImportError as e:
            logger.error(f"❌ Tushare提供器导入失败: {e}")
            return None

    @staticmethod
    def get_akshare_adapter():
        """获取AKShare适配器"""
        try:
            from tradingagents.dataflows.providers.china.akshare import get_akshare_provider
            return get_akshare_provider()
        except ImportError as e:
            logger.error(f"❌ AKShare适配器导入失败: {e}")
            return None

    @staticmethod
    def get_baostock_adapter():
        """获取BaoStock适配器"""
        try:
            from tradingagents.dataflows.providers.china.baostock import get_baostock_provider
            return get_baostock_provider()
        except ImportError as e:
            logger.error(f"❌ BaoStock适配器导入失败: {e}")
            return None

    @staticmethod
    def get_mongodb_adapter():
        """获取MongoDB适配器"""
        try:
            from tradingagents.dataflows.cache.mongodb_cache_adapter import get_mongodb_cache_adapter
            return get_mongodb_cache_adapter()
        except Exception as e:
            logger.warning(f"⚠️ 获取MongoDB适配器失败: {e}")
            return None


__all__ = [
    'DataFetchers',
]
