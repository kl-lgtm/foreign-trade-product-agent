# 导入Python内置的单元测试框架
import unittest

# 导入json，用于生成真实的临时评测数据文件
import json

# 导入TemporaryDirectory，用于测试结束后自动清理文件
from tempfile import TemporaryDirectory

# 导入Path，用于构造跨平台文件路径
from pathlib import Path

# 导入Agent单题评分函数和即将编写的汇总函数
from product_agent.agent_evaluator import (
    evaluate_product_agent_result,
    load_product_agent_evaluation_cases,
    run_product_agent_evaluation_cases,
    save_product_agent_evaluation_report,
    summarize_product_agent_evaluation_results,
)


# 创建外贸Agent评测器的测试类
class TradeAgentEvaluatorTest(unittest.TestCase):
    """测试Agent评测结果是否判断正确。"""

    def test_correct_product_agent_result_should_pass(
        self,
    ) -> None:
        """工具、参数和回答都正确时，评测应当通过。"""

        # 准备一条人工确定的评测标准
        product_evaluation_case = {
            "case_id": "product_agent_case_001",
            "question": "查询A001的价格和库存",
            "expected_tool": "query_product",
            "expected_product_id": "A001",
            "expected_answer_keywords": [
                "8.50",
                "2600",
            ],
        }

        # 模拟Agent真实返回的数据结构
        # 这里不调用大模型，因此不会消耗API额度
        product_agent_result = {
            "answer": (
                "A001的测试价格为8.50美元/平方米，"
                "当前库存为2600平方米。"
            ),
            "tool_events": [
                {
                    "step": 1,
                    "tool_name": "query_product",
                    "arguments": {
                        "product_id": "A001",
                    },
                    "result": {
                        "success": True,
                    },
                }
            ],
        }

        # 调用尚未实现的评测函数
        product_evaluation_result = (
            evaluate_product_agent_result(
                product_evaluation_case=(
                    product_evaluation_case
                ),
                product_agent_result=product_agent_result,
            )
        )

        # 正确的Agent执行结果应当通过评测
        self.assertTrue(
            product_evaluation_result["passed"]
        )

    def test_matching_later_tool_event_should_pass(
        self,
    ) -> None:
        """多个工具事件中存在正确调用时，评测应当通过。"""

        # 准备A001产品查询的评测标准
        product_evaluation_case = {
            "case_id": "product_agent_case_005",
            "question": "查询A001的价格",
            "expected_tool": "query_product",
            "expected_product_id": "A001",
            "expected_answer_keywords": [
                "8.50",
            ],
        }

        # 模拟Agent先查询A002，随后才正确查询A001
        product_agent_result = {
            "answer": (
                "A001的测试价格为8.50美元/平方米。"
            ),
            "tool_events": [
                {
                    "step": 1,
                    "tool_name": "query_product",
                    "arguments": {
                        "product_id": "A002",
                    },
                    "result": {
                        "success": True,
                    },
                },
                {
                    "step": 2,
                    "tool_name": "query_product",
                    "arguments": {
                        "product_id": "A001",
                    },
                    "result": {
                        "success": True,
                    },
                },
            ],
        }

        # 使用评测函数检查多次工具调用
        product_evaluation_result = (
            evaluate_product_agent_result(
                product_evaluation_case=(
                    product_evaluation_case
                ),
                product_agent_result=product_agent_result,
            )
        )

        # 只要存在一次完全正确的工具调用，就应通过
        self.assertTrue(
            product_evaluation_result["passed"]
        )

    def test_real_product_id_argument_should_pass(
        self,
    ) -> None:
        """评测器应识别真实工具使用的product_id参数。"""

        # 准备与真实题库一致的A001评测标准
        product_evaluation_case = {
            "case_id": "product_agent_case_real_argument",
            "question": "查询A001库存",
            "expected_tool": "query_product",
            "expected_product_id": "A001",
            "expected_answer_keywords": [
                "2600"
            ],
        }

        # 使用真实Agent工具定义中的product_id字段
        product_agent_result = {
            "answer": "A001当前库存为2600平方米。",
            "tool_events": [
                {
                    "step": 1,
                    "tool_name": "query_product",
                    "arguments": {
                        "product_id": "A001",
                    },
                    "result": {
                        "found": True,
                        "product_id": "A001",
                    },
                }
            ],
        }

        # 对真实参数字段执行评分
        product_evaluation_result = (
            evaluate_product_agent_result(
                product_evaluation_case=(
                    product_evaluation_case
                ),
                product_agent_result=product_agent_result,
            )
        )

        # 参数名与真实工具一致时应通过
        self.assertTrue(
            product_evaluation_result["passed"]
        )

    def test_number_with_thousands_separator_should_pass(
        self,
    ) -> None:
        """2600与2,600应被视为相同的回答数值。"""

        # 评测题库使用不带千位分隔符的库存数字
        product_evaluation_case = {
            "case_id": "product_agent_case_number_format",
            "question": "查询A001库存",
            "expected_tool": "query_product",
            "expected_product_id": "A001",
            "expected_answer_keywords": [
                "2600"
            ],
        }

        # Agent回答使用更易读的2,600格式
        product_agent_result = {
            "answer": "A001库存为2,600平方米。",
            "tool_events": [
                {
                    "step": 1,
                    "tool_name": "query_product",
                    "arguments": {
                        "product_id": "A001",
                    },
                    "result": {
                        "success": True,
                        "data": {
                            "found": True,
                            "product_id": "A001",
                        },
                    },
                }
            ],
        }

        # 对不同数字显示格式执行评分
        product_evaluation_result = (
            evaluate_product_agent_result(
                product_evaluation_case=(
                    product_evaluation_case
                ),
                product_agent_result=product_agent_result,
            )
        )

        # 千位分隔符不应造成关键词误判
        self.assertTrue(
            product_evaluation_result["passed"]
        )

    def test_expected_tool_found_result_should_be_checked(
        self,
    ) -> None:
        """评测器应读取真实工具结果中的嵌套found字段。"""

        # 评测标准要求A999在产品数据库中不存在
        product_evaluation_case = {
            "case_id": "product_agent_case_found_state",
            "question": "查询A999库存",
            "expected_tool": "query_product",
            "expected_product_id": "A999",
            "expected_tool_result_found": False,
            "expected_answer_keywords": [
                "A999"
            ],
        }

        # 模拟真实工具正确返回A999不存在
        product_agent_result = {
            "answer": "产品数据库中没有A999。",
            "tool_events": [
                {
                    "step": 1,
                    "tool_name": "query_product",
                    "arguments": {
                        "product_id": "A999",
                    },
                    "result": {
                        "success": True,
                        "data": {
                            "found": False,
                            "product_id": "A999",
                        },
                    },
                }
            ],
        }

        # 对工具返回的产品存在状态进行评分
        product_evaluation_result = (
            evaluate_product_agent_result(
                product_evaluation_case=(
                    product_evaluation_case
                ),
                product_agent_result=product_agent_result,
            )
        )

        # 嵌套found与预期一致，因此整题应该通过
        self.assertTrue(
            product_evaluation_result["passed"]
        )
        self.assertTrue(
            product_evaluation_result[
                "tool_result_passed"
            ]
        )

    def test_evaluation_summary_should_calculate_pass_rate(
        self,
    ) -> None:
        """汇总结果应正确计算通过数量和通过率。"""

        # 模拟三条已经完成评分的结果
        product_evaluation_results = [
            {
                "case_id": "product_agent_case_001",
                "passed": True,
            },
            {
                "case_id": "product_agent_case_002",
                "passed": False,
            },
            {
                "case_id": "product_agent_case_003",
                "passed": True,
            },
        ]

        # 调用尚未实现的评测汇总函数
        product_evaluation_summary = (
            summarize_product_agent_evaluation_results(
                product_evaluation_results
            )
        )

        # 总测试数量应为3
        self.assertEqual(
            product_evaluation_summary["total_count"],
            3,
        )

        # 通过数量应为2
        self.assertEqual(
            product_evaluation_summary["passed_count"],
            2,
        )

        # 失败数量应为1
        self.assertEqual(
            product_evaluation_summary["failed_count"],
            1,
        )

        # 通过率保留两位小数，应为66.67%
        self.assertEqual(
            product_evaluation_summary["pass_rate"],
            66.67,
        )

    def test_empty_evaluation_summary_should_return_zero(
        self,
    ) -> None:
        """没有评测结果时，汇总数值应全部为零。"""

        # 使用空列表模拟没有加载到任何测试用例
        product_evaluation_summary = (
            summarize_product_agent_evaluation_results(
                []
            )
        )

        # 空结果的总数、通过数和失败数都应为零
        self.assertEqual(
            product_evaluation_summary["total_count"],
            0,
        )
        self.assertEqual(
            product_evaluation_summary["passed_count"],
            0,
        )
        self.assertEqual(
            product_evaluation_summary["failed_count"],
            0,
        )

        # 空结果的通过率应定义为0%，不能发生除零错误
        self.assertEqual(
            product_evaluation_summary["pass_rate"],
            0.0,
        )

    def test_evaluation_cases_should_load_from_json(
        self,
    ) -> None:
        """评测器应从UTF-8 JSON文件读取测试用例。"""

        # 创建测试结束后会自动删除的临时目录
        with TemporaryDirectory() as product_temp_directory:

            # 在临时目录中创建评测数据文件路径
            product_test_file = (
                Path(product_temp_directory)
                / "product_agent_cases.json"
            )

            # 准备一条确定的评测数据
            product_expected_cases = [
                {
                    "case_id": "product_agent_case_test",
                    "question": "查询A001",
                    "expected_tool": (
                        "query_product"
                    ),
                    "expected_product_id": "A001",
                    "expected_answer_keywords": [
                        "8.50"
                    ],
                }
            ]

            # 使用UTF-8把测试数据写入真实JSON文件
            product_test_file.write_text(
                json.dumps(
                    product_expected_cases,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            # 调用尚未实现的加载函数
            product_loaded_cases = (
                load_product_agent_evaluation_cases(
                    product_test_file
                )
            )

        # 文件中写入和函数读取的内容应完全一致
        self.assertEqual(
            product_loaded_cases,
            product_expected_cases,
        )

    def test_evaluation_runner_should_score_all_cases(
        self,
    ) -> None:
        """评测执行器应运行测试用例并返回汇总结果。"""

        # 准备一条不依赖外部API的评测用例
        product_evaluation_cases = [
            {
                "case_id": "product_agent_case_test",
                "question": "查询A001价格和库存",
                "expected_tool": (
                    "query_product"
                ),
                "expected_product_id": "A001",
                "expected_answer_keywords": [
                    "8.50",
                    "2600",
                ],
            }
        ]

        # 使用本地函数代替收费且不稳定的外部大模型API
        # 返回结构与真实产品Agent保持一致
        def product_fake_agent_runner(
            product_user_question: str,
        ) -> dict[str, object]:
            """返回确定的Agent结果供执行器测试。"""

            # 确认测试用问题确实传到了Agent边界
            self.assertEqual(
                product_user_question,
                "查询A001价格和库存",
            )

            # 返回模拟的正确回答和真实格式工具事件
            return {
                "answer": (
                    "A001价格为8.50美元，"
                    "库存为2600平方米。"
                ),
                "tool_events": [
                    {
                        "step": 1,
                        "tool_name": (
                            "query_product"
                        ),
                        "arguments": {
                            "product_id": "A001",
                        },
                        "result": {
                            "success": True,
                        },
                    }
                ],
            }

        # 运行尚未实现的批量评测执行器
        product_evaluation_report = (
            run_product_agent_evaluation_cases(
                product_evaluation_cases=(
                    product_evaluation_cases
                ),
                product_agent_runner=(
                    product_fake_agent_runner
                ),
            )
        )

        # 一条正确用例应得到100%通过率
        self.assertEqual(
            product_evaluation_report["summary"],
            {
                "total_count": 1,
                "passed_count": 1,
                "failed_count": 0,
                "pass_rate": 100.0,
            },
        )

        # 报告中应保留测试用例编号和评分结果
        self.assertEqual(
            product_evaluation_report["results"][0][
                "case_id"
            ],
            "product_agent_case_test",
        )
        self.assertTrue(
            product_evaluation_report["results"][0][
                "passed"
            ]
        )

    def test_evaluation_runner_should_continue_after_error(
        self,
    ) -> None:
        """单题执行异常时，应记录失败并继续后续评测。"""

        # 准备一条故障用例和一条正常用例
        product_evaluation_cases = [
            {
                "case_id": "product_agent_case_error",
                "question": "触发连接错误",
                "expected_tool": None,
                "expected_product_id": None,
                "expected_answer_keywords": [],
            },
            {
                "case_id": "product_agent_case_success",
                "question": "解释FOB",
                "expected_tool": None,
                "expected_product_id": None,
                "expected_answer_keywords": [
                    "FOB"
                ],
            },
        ]

        # 模拟第一题连接失败、第二题正常返回
        def product_partly_failing_agent_runner(
            product_user_question: str,
        ) -> dict[str, object]:
            """根据问题返回异常或正常Agent结果。"""

            # 第一题模拟外部API连接错误
            if product_user_question == "触发连接错误":
                raise ConnectionError(
                    "模拟API连接失败"
                )

            # 第二题返回不调用工具的普通回答
            return {
                "answer": "FOB是一种国际贸易术语。",
                "tool_events": [],
            }

        # 运行包含故障题目的批量评测
        product_evaluation_report = (
            run_product_agent_evaluation_cases(
                product_evaluation_cases=(
                    product_evaluation_cases
                ),
                product_agent_runner=(
                    product_partly_failing_agent_runner
                ),
            )
        )

        # 两题都应出现在报告中，不能因第一题失败而中断
        self.assertEqual(
            product_evaluation_report["summary"][
                "total_count"
            ],
            2,
        )
        self.assertEqual(
            product_evaluation_report["summary"][
                "passed_count"
            ],
            1,
        )
        self.assertEqual(
            product_evaluation_report["summary"][
                "failed_count"
            ],
            1,
        )

        # 第一题应保存异常类型，便于排查故障
        self.assertEqual(
            product_evaluation_report["results"][0][
                "error_type"
            ],
            "ConnectionError",
        )

        # 第二题仍应被执行并通过
        self.assertTrue(
            product_evaluation_report["results"][1][
                "passed"
            ]
        )

    def test_evaluation_report_should_save_as_json(
        self,
    ) -> None:
        """完整评测报告应保存为可重新读取的JSON文件。"""

        # 准备一份最小但结构完整的评测报告
        product_evaluation_report = {
            "summary": {
                "total_count": 1,
                "passed_count": 1,
                "failed_count": 0,
                "pass_rate": 100.0,
            },
            "results": [
                {
                    "case_id": "product_agent_case_test",
                    "passed": True,
                }
            ],
        }

        # 使用临时目录避免测试污染真实项目报告
        with TemporaryDirectory() as product_temp_directory:
            product_report_file = (
                Path(product_temp_directory)
                / "product_agent_report.json"
            )

            # 调用尚未实现的报告保存函数
            save_product_agent_evaluation_report(
                product_evaluation_report=(
                    product_evaluation_report
                ),
                product_report_file=product_report_file,
            )

            # 从磁盘重新读取报告，验证真实文件内容
            product_saved_report = json.loads(
                product_report_file.read_text(
                    encoding="utf-8"
                )
            )

        # 保存前后的报告数据应该完全一致
        self.assertEqual(
            product_saved_report,
            product_evaluation_report,
        )


# 直接运行当前文件时启动单元测试

if __name__ == "__main__":
    unittest.main()
