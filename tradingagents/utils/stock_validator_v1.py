#!/usr/bin/env python3
"""
股票数据预获取和验证模块
用于在分析流程开始前验证股票是否存在，并预先获取和缓存必要的数据
"""

import re
from typing import Dict
from datetime import datetime, timedelta


class StockDataPreparationResult:
    """股票数据预获取结果类"""

    def __init__(self, is_valid: bool, stock_code: str, market_type: str = "",
                 stock_name: str = "", error_message: str = "", suggestion: str = "",
                 has_historical_data: bool = False, has_basic_info: bool = False,
                 data_period_days: int = 0, cache_status: str = ""):
        self.is_valid = is_valid
        self.stock_code = stock_code
        self.market_type = market_type
        self.stock_name = stock_name
        self.error_message = error_message
        self.suggestion = suggestion
        self.has_historical_data = has_historical_data
        self.has_basic_info = has_basic_info
        self.data_period_days = data_period_days
        self.cache_status = cache_status

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'is_valid': self.is_valid,
            'stock_code': self.stock_code,
            'market_type': self.market_type,
            'stock_name': self.stock_name,
            'error_message': self.error_message,
            'suggestion': self.suggestion,
            'has_historical_data': self.has_historical_data,
            'has_basic_info': self.has_basic_info,
            'data_period_days': self.data_period_days,
            'cache_status': self.cache_status
        }


# 保持向后兼容
StockValidationResult = StockDataPreparationResult


class StockDataPreparer:
    """股票数据预获取和验证器"""

    def __init__(self, default_period_days: int = 30):
        self.timeout_seconds = 15
        self.default_period_days = default_period_days

    def prepare_stock_data(self, stock_code: str, market_type: str = "auto",
                          period_days: int = None, analysis_date: str = None) -> StockDataPreparationResult:
        """预获取和验证股票数据"""
        if period_days is None:
            period_days = self.default_period_days

        if analysis_date is None:
            analysis_date = datetime.now().strftime('%Y-%m-%d')

        # 1. 基本格式验证
        format_result = self._validate_format(stock_code, market_type)
        if not format_result.is_valid:
            return format_result

        # 2. 自动检测市场类型
        if market_type == "auto":
            market_type = self._detect_market_type(stock_code)

        # 3. 预获取数据并验证
        return self._prepare_market_data(stock_code, market_type, period_days, analysis_date)

    def _validate_format(self, stock_code: str, market_type: str) -> StockDataPreparationResult:
        """验证股票代码格式"""
        stock_code = stock_code.strip()

        if not stock_code:
            return StockDataPreparationResult(
                is_valid=False, stock_code=stock_code,
                error_message="股票代码不能为空",
                suggestion="请输入有效的股票代码"
            )

        if len(stock_code) > 10:
            return StockDataPreparationResult(
                is_valid=False, stock_code=stock_code,
                error_message="股票代码长度不能超过10个字符",
                suggestion="请检查股票代码格式"
            )

        # 根据市场类型验证格式
        if market_type == "A股":
            if not re.match(r'^\d{6}$', stock_code):
                return StockDataPreparationResult(
                    is_valid=False, stock_code=stock_code, market_type="A股",
                    error_message="A股代码格式错误，应为6位数字",
                    suggestion="请输入6位数字的A股代码，如：000001、600519"
                )
        elif market_type == "港股":
            stock_code_upper = stock_code.upper()
            if not (re.match(r'^\d{4,5}\.HK$', stock_code_upper) or re.match(r'^\d{4,5}$', stock_code)):
                return StockDataPreparationResult(
                    is_valid=False, stock_code=stock_code, market_type="港股",
                    error_message="港股代码格式错误",
                    suggestion="请输入4-5位数字.HK格式（如：0700.HK）或4-5位数字（如：0700）"
                )
        elif market_type == "美股":
            if not re.match(r'^[A-Z]{1,5}$', stock_code.upper()):
                return StockDataPreparationResult(
                    is_valid=False, stock_code=stock_code, market_type="美股",
                    error_message="美股代码格式错误，应为1-5位字母",
                    suggestion="请输入1-5位字母的美股代码，如：AAPL、TSLA"
                )

        return StockDataPreparationResult(is_valid=True, stock_code=stock_code, market_type=market_type)

    def _detect_market_type(self, stock_code: str) -> str:
        """自动检测市场类型"""
        stock_code = stock_code.strip().upper()

        if re.match(r'^\d{6}$', stock_code):
            return "A股"

        if re.match(r'^\d{4,5}\.HK$', stock_code) or re.match(r'^\d{4,5}$', stock_code):
            return "港股"

        if re.match(r'^[A-Z]{1,5}$', stock_code):
            return "美股"

        return "未知"

    def _extract_stock_name(self, stock_info, stock_code: str) -> str:
        """从股票信息中提取股票名称"""
        if not stock_info:
            return stock_code

        # 处理字典类型
        if isinstance(stock_info, dict):
            name_fields = ['name', 'longName', 'shortName', 'companyName', '公司名称', '股票名称']
            for field in name_fields:
                if field in stock_info and stock_info[field]:
                    name = str(stock_info[field]).strip()
                    if name and name != "未知":
                        return name
            return stock_code if len(stock_info) > 0 else stock_code

        # 处理字符串类型
        stock_info_str = str(stock_info)

        # 标准格式 "公司名称: XXX" 或 "股票名称: XXX"
        for indicator in ["公司名称:", "股票名称:"]:
            if indicator in stock_info_str:
                lines = stock_info_str.split('\n')
                for line in lines:
                    if indicator in line:
                        name = line.split(':')[1].strip()
                        if name and name != "未知":
                            return name

        # Yahoo Finance格式
        if " -> " in stock_info_str:
            parts = stock_info_str.split(" -> ")
            if len(parts) > 1:
                name = parts[-1].strip()
                if name and name != "未知":
                    return name

        return stock_code

    def _prepare_market_data(self, stock_code: str, market_type: str,
                            period_days: int, analysis_date: str) -> StockDataPreparationResult:
        """统一的股票数据获取方法"""
        try:
            if market_type == "A股":
                return self._prepare_china_data(stock_code, period_days, analysis_date)
            elif market_type == "港股":
                return self._prepare_hk_data(stock_code, period_days, analysis_date)
            elif market_type == "美股":
                return self._prepare_us_data(stock_code, period_days, analysis_date)
            else:
                return StockDataPreparationResult(
                    is_valid=False, stock_code=stock_code, market_type=market_type,
                    error_message=f"不支持的市场类型: {market_type}",
                    suggestion="请选择支持的市场类型：A股、港股、美股"
                )
        except Exception as e:
            return StockDataPreparationResult(
                is_valid=False, stock_code=stock_code, market_type=market_type,
                error_message=f"数据准备失败: {str(e)}",
                suggestion="请检查网络连接或稍后重试"
            )

    def _prepare_china_data(self, stock_code: str, period_days: int, analysis_date: str) -> StockDataPreparationResult:
        """简化的A股数据获取"""
        try:
            from app.core.config import settings
            lookback_days = getattr(settings, 'MARKET_ANALYST_LOOKBACK_DAYS', 365)

            end_date = datetime.strptime(analysis_date, '%Y-%m-%d')
            start_date = end_date - timedelta(days=lookback_days)

            from tradingagents.dataflows.interface_v1 import get_china_stock_info_unified

            stock_info = get_china_stock_info_unified(stock_code)
            stock_name = self._extract_stock_name(stock_info, stock_code)

            if stock_info and "❌" not in stock_info and "未能获取" not in stock_info:
                if stock_name == stock_code or stock_name.startswith(f"股票{stock_code}"):
                    return StockDataPreparationResult(
                        is_valid=False, stock_code=stock_code, market_type="A股",
                        error_message=f"股票代码 {stock_code} 不存在或信息无效",
                        suggestion="请检查股票代码是否正确，或确认该股票是否已上市"
                    )
            else:
                return StockDataPreparationResult(
                    is_valid=False, stock_code=stock_code, market_type="A股",
                    error_message=f"无法获取股票 {stock_code} 的基本信息",
                    suggestion="请检查股票代码是否正确，或稍后重试"
                )

            from tradingagents.dataflows.interface_v1 import get_china_stock_data_unified

            historical_data = get_china_stock_data_unified(
                stock_code, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
            )

            has_historical_data = (
                historical_data and
                "❌" not in historical_data and
                "获取失败" not in historical_data and
                len(historical_data) > 100
            )

            if not has_historical_data:
                return StockDataPreparationResult(
                    is_valid=False, stock_code=stock_code, market_type="A股",
                    stock_name=stock_name, has_basic_info=True,
                    error_message=f"股票 {stock_code} 的历史数据不足",
                    suggestion="该股票可能为新上市股票，请稍后重试"
                )

            return StockDataPreparationResult(
                is_valid=True, stock_code=stock_code, market_type="A股",
                stock_name=stock_name, has_basic_info=True,
                has_historical_data=True, data_period_days=lookback_days,
                cache_status=f"基本信息已缓存; 历史数据已缓存({lookback_days}天)"
            )

        except Exception as e:
            return StockDataPreparationResult(
                is_valid=False, stock_code=stock_code, market_type="A股",
                error_message=f"A股数据获取失败: {str(e)}",
                suggestion="请检查网络连接或稍后重试"
            )

    def _prepare_hk_data(self, stock_code: str, period_days: int, analysis_date: str) -> StockDataPreparationResult:
        """简化的港股数据获取"""
        # 格式化代码
        if not stock_code.upper().endswith('.HK'):
            clean_code = stock_code.lstrip('0') or '0'
            formatted_code = f"{clean_code.zfill(4)}.HK"
        else:
            formatted_code = stock_code.upper()

        stock_name = formatted_code  # 默认值，避免异常处理时未定义

        try:
            end_date = datetime.strptime(analysis_date, '%Y-%m-%d')
            start_date = end_date - timedelta(days=period_days)

            from tradingagents.dataflows.interface_v1 import get_hk_stock_info_unified

            stock_info = get_hk_stock_info_unified(formatted_code)

            if stock_info and "❌" not in stock_info and "未找到" not in stock_info:
                stock_name = self._extract_stock_name(stock_info, formatted_code)

            if stock_info and "❌" not in stock_info and "未找到" not in stock_info:
                if stock_name == formatted_code:
                    return StockDataPreparationResult(
                        is_valid=False, stock_code=formatted_code, market_type="港股",
                        error_message=f"港股代码 {formatted_code} 不存在或信息无效",
                        suggestion="请检查港股代码是否正确，格式如：0700.HK"
                    )
            else:
                # 检查网络限制
                network_error_indicators = ["Too Many Requests", "Rate limited", "Connection aborted",
                                          "Remote end closed connection", "网络连接", "超时", "限制"]

                if any(indicator in str(stock_info) for indicator in network_error_indicators):
                    return StockDataPreparationResult(
                        is_valid=False, stock_code=formatted_code, market_type="港股",
                        error_message="港股数据获取受到网络限制影响",
                        suggestion="等待5-10分钟后重试，或检查网络连接是否稳定"
                    )
                else:
                    return StockDataPreparationResult(
                        is_valid=False, stock_code=formatted_code, market_type="港股",
                        error_message=f"港股代码 {formatted_code} 可能不存在或数据源暂时不可用",
                        suggestion="请检查港股代码是否正确，格式如：0700.HK，或稍后重试"
                    )

            from tradingagents.dataflows.interface_v1 import get_hk_stock_data_unified

            historical_data = get_hk_stock_data_unified(
                formatted_code, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
            )

            data_indicators = ["开盘价", "收盘价", "最高价", "最低价", "成交量",
                             "open", "close", "high", "low", "volume"]

            has_valid_data = (
                historical_data and
                "❌" not in historical_data and
                "获取失败" not in historical_data and
                len(historical_data) > 50 and
                any(indicator in historical_data for indicator in data_indicators)
            )

            if not has_valid_data:
                return StockDataPreparationResult(
                    is_valid=False, stock_code=formatted_code, market_type="港股",
                    stock_name=stock_name, has_basic_info=True,
                    error_message=f"港股 {formatted_code} 的历史数据不足",
                    suggestion="该股票可能为新上市股票或数据源暂时不可用，请稍后重试"
                )

            return StockDataPreparationResult(
                is_valid=True, stock_code=formatted_code, market_type="港股",
                stock_name=stock_name, has_basic_info=True,
                has_historical_data=True, data_period_days=period_days,
                cache_status=f"基本信息已缓存; 历史数据已缓存({period_days}天)"
            )

        except Exception as e:
            return StockDataPreparationResult(
                is_valid=False, stock_code=formatted_code, market_type="港股",
                stock_name=stock_name, has_basic_info=True,
                error_message=f"港股数据获取失败: {str(e)}",
                suggestion="请检查网络连接或数据源配置"
            )

    def _prepare_us_data(self, stock_code: str, period_days: int, analysis_date: str) -> StockDataPreparationResult:
        """简化的美股数据获取"""
        formatted_code = stock_code.upper()

        try:
            end_date = datetime.strptime(analysis_date, '%Y-%m-%d')
            start_date = end_date - timedelta(days=period_days)

            # 尝试导入美股数据提供器
            try:
                from tradingagents.dataflows.providers.us import OptimizedUSDataProvider
                provider = OptimizedUSDataProvider()
                historical_data = provider.get_stock_data(
                    formatted_code, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
                )
            except (ImportError, Exception):
                from tradingagents.dataflows.providers.us.optimized import get_us_stock_data_cached
                historical_data = get_us_stock_data_cached(
                    formatted_code, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
                )

            data_indicators = ["开盘价", "收盘价", "最高价", "最低价", "成交量",
                             "Open", "Close", "High", "Low", "Volume"]

            has_valid_data = (
                historical_data and
                "❌" not in historical_data and
                "错误" not in historical_data and
                "无法获取" not in historical_data and
                len(historical_data) > 50 and
                any(indicator in historical_data for indicator in data_indicators)
            )

            if not has_valid_data:
                return StockDataPreparationResult(
                    is_valid=False, stock_code=formatted_code, market_type="美股",
                    error_message=f"美股 {formatted_code} 的历史数据无效或不足",
                    suggestion="该股票可能为新上市股票或数据源暂时不可用，请稍后重试"
                )

            return StockDataPreparationResult(
                is_valid=True, stock_code=formatted_code, market_type="美股",
                stock_name=formatted_code, has_basic_info=True,
                has_historical_data=True, data_period_days=period_days,
                cache_status=f"历史数据已缓存({period_days}天)"
            )

        except Exception as e:
            return StockDataPreparationResult(
                is_valid=False, stock_code=formatted_code, market_type="美股",
                error_message=f"美股数据获取失败: {str(e)}",
                suggestion="请检查网络连接或数据源配置"
            )


# 全局实例
_preparer_instance = None


def get_stock_preparer() -> StockDataPreparer:
    """获取StockDataPreparer实例"""
    global _preparer_instance
    if _preparer_instance is None:
        _preparer_instance = StockDataPreparer()
    return _preparer_instance


def prepare_stock_data(stock_code: str, market_type: str = "auto",
                      period_days: int = None, analysis_date: str = None) -> StockDataPreparationResult:
    """预获取和验证股票数据（便捷函数）"""
    preparer = get_stock_preparer()
    return preparer.prepare_stock_data(stock_code, market_type, period_days, analysis_date)


def get_stock_preparation_message(stock_code: str, market_type: str = "auto",
                                 period_days: int = None, analysis_date: str = None) -> str:
    """获取股票数据准备消息"""
    result = prepare_stock_data(stock_code, market_type, period_days, analysis_date)

    if result.is_valid:
        return f"✅ 数据准备成功: {result.stock_code} ({result.market_type}) - {result.stock_name}\n📊 {result.cache_status}"
    else:
        return f"❌ 数据准备失败: {result.error_message}\n💡 建议: {result.suggestion}"


async def prepare_stock_data_async(stock_code: str, market_type: str = "auto",
                                   period_days: int = None, analysis_date: str = None) -> StockDataPreparationResult:
    """异步版本：预获取和验证股票数据（用于FastAPI异步上下文）"""
    preparer = get_stock_preparer()

    if period_days is None:
        period_days = preparer.default_period_days

    if analysis_date is None:
        analysis_date = datetime.now().strftime('%Y-%m-%d')

    # 基本格式验证
    format_result = preparer._validate_format(stock_code, market_type)
    if not format_result.is_valid:
        return format_result

    # 自动检测市场类型
    if market_type == "auto":
        market_type = preparer._detect_market_type(stock_code)

    # 同步调用数据准备（在实际应用中可改为真正的异步操作）
    return preparer._prepare_market_data(stock_code, market_type, period_days, analysis_date)
