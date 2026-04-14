"""
极简化交易分析CLI - TradingAgents Minimal CLI
去掉了所有UI相关代码，保留核心分析功能
Minimal trading analysis CLI without UI, keeping core functionality
"""

# 标准库导入
import re
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 第三方库导入
from dotenv import load_dotenv

# 项目内部导入
from cli.models import AnalystType
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph_v1 import TradingAgentsGraph

# 加载环境变量
load_dotenv()

# 硬编码配置 - 保持不变
SELECTIONS = {
    "selected_market": 2,
    "ticker": "000001",
    "analysis_date": '2026-4-10',
    "analysts": [AnalystType.MARKET, AnalystType.SOCIAL, AnalystType.NEWS, AnalystType.FUNDAMENTALS],
    "research_depth": 1,
}


class SimpleReportSaver:
    """简化的报告保存类"""

    def __init__(self, report_dir: Path):
        self.report_dir = report_dir
        self.reports = {}

    def save_report(self, section_name: str, content: str):
        """保存报告到文件"""
        if content:
            self.reports[section_name] = content
            file_path = self.report_dir / f"{section_name}.md"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)


def run_analysis():
    """执行分析的主函数"""
    # 配置
    config = DEFAULT_CONFIG.copy()
    config["max_debate_rounds"] = SELECTIONS["research_depth"]
    config["max_risk_discuss_rounds"] = SELECTIONS["research_depth"]

    # 初始化图
    try:
        graph = TradingAgentsGraph(
            [analyst.value for analyst in SELECTIONS["analysts"]],
            config=config,
            debug=True
        )
    except Exception as e:
        return

    # 创建结果目录
    results_dir = Path(config["results_dir"]) / SELECTIONS["ticker"] / SELECTIONS["analysis_date"]
    results_dir.mkdir(parents=True, exist_ok=True)
    report_dir = results_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    # 初始化报告保存器
    report_saver = SimpleReportSaver(report_dir)

    # 数据验证
    try:
        from tradingagents.utils.stock_validator_v1 import prepare_stock_data

        # 确定市场类型
        if re.match(r'^\d{6}$', SELECTIONS["ticker"]):
            market_type = "A股"
        elif ".HK" in SELECTIONS["ticker"].upper():
            market_type = "港股"
        else:
            market_type = "美股"

        # 预获取数据
        preparation_result = prepare_stock_data(
            stock_code=SELECTIONS["ticker"],
            market_type=market_type,
            period_days=30,
            analysis_date=SELECTIONS["analysis_date"]
        )

        if not preparation_result.is_valid:
            return

    except Exception as e:
        return

    # 执行分析
    try:
        init_agent_state = graph.propagator.create_initial_state(
            SELECTIONS["ticker"], SELECTIONS["analysis_date"]
        )
        args = graph.propagator.get_graph_args()

        # 流式处理
        completed_reports = set()

        for chunk in graph.graph.stream(init_agent_state, **args):

            # 处理市场分析报告
            if "market_report" in chunk and chunk["market_report"]:
                if "market_report" not in completed_reports:
                    completed_reports.add("market_report")
                report_saver.save_report("market_report", chunk["market_report"])

            # 处理情感分析报告
            if "sentiment_report" in chunk and chunk["sentiment_report"]:
                if "sentiment_report" not in completed_reports:
                    completed_reports.add("sentiment_report")
                report_saver.save_report("sentiment_report", chunk["sentiment_report"])

            # 处理新闻分析报告
            if "news_report" in chunk and chunk["news_report"]:
                if "news_report" not in completed_reports:
                    completed_reports.add("news_report")
                report_saver.save_report("news_report", chunk["news_report"])

            # 处理基本面分析报告
            if "fundamentals_report" in chunk and chunk["fundamentals_report"]:
                if "fundamentals_report" not in completed_reports:
                    completed_reports.add("fundamentals_report")
                report_saver.save_report("fundamentals_report", chunk["fundamentals_report"])

            # 处理投资决策
            if "investment_plan" in chunk and chunk["investment_plan"]:
                if "investment_plan" not in completed_reports:
                    completed_reports.add("investment_plan")
                report_saver.save_report("investment_plan", chunk["investment_plan"])

            # 处理最终决策
            if "final_trade_decision" in chunk and chunk["final_trade_decision"]:
                if "final_trade_decision" not in completed_reports:
                    completed_reports.add("final_trade_decision")
                report_saver.save_report("final_trade_decision", chunk["final_trade_decision"])

    except Exception as e:
        import traceback
        traceback.print_exc()


def main():
    """程序入口"""
    try:
        run_analysis()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
