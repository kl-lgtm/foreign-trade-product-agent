# 导入json，用于读取Agent评测题库和生成评测报告
import json

# 导入Path，用于可靠定位项目文件
from pathlib import Path

# 导入Callable，用于描述可替换的Agent执行函数
from collections.abc import Callable


# 取得当前评测模块文件的绝对路径
product_evaluator_file = Path(__file__).resolve()

# 当前文件位于product_agent目录，向上两级得到项目根目录
product_project_root = product_evaluator_file.parent.parent

# 设置项目默认的Agent评测题库路径
TRADE_AGENT_EVALUATION_CASES_FILE = (
    product_project_root
    / "trade_data"
    / "evaluation"
    / "agent_evaluation_cases.json"
)

# 设置项目默认的Agent评测报告路径
TRADE_AGENT_EVALUATION_REPORT_FILE = (
    product_project_root
    / "trade_data"
    / "evaluation"
    / "agent_evaluation_report.json"
)


def load_product_agent_evaluation_cases(
    product_evaluation_file: Path = (
        TRADE_AGENT_EVALUATION_CASES_FILE
    ),
) -> list[dict[str, object]]:
    """从UTF-8 JSON文件中读取Agent评测用例。"""

    # 文件不存在时给出包含完整路径的明确错误
    if not product_evaluation_file.exists():
        raise FileNotFoundError(
            f"没有找到Agent评测题库："
            f"{product_evaluation_file}"
        )

    # 使用UTF-8读取JSON文本并转换成Python对象
    product_evaluation_data = json.loads(
        product_evaluation_file.read_text(
            encoding="utf-8"
        )
    )

    # 评测题库顶层必须是JSON数组
    if not isinstance(
        product_evaluation_data,
        list,
    ):
        raise ValueError(
            "Agent评测题库的顶层必须是JSON数组。"
        )

    # 每一条测试用例都必须是JSON对象
    if not all(
        isinstance(product_evaluation_case, dict)
        for product_evaluation_case
        in product_evaluation_data
    ):
        raise ValueError(
            "Agent评测题库中的每条用例必须是JSON对象。"
        )

    # 返回验证后的测试用例列表
    return product_evaluation_data


def save_product_agent_evaluation_report(
    product_evaluation_report: dict[str, object],
    product_report_file: Path = (
        TRADE_AGENT_EVALUATION_REPORT_FILE
    ),
) -> Path:
    """把完整Agent评测报告保存为UTF-8 JSON文件。"""

    # 确保报告文件所在目录已经创建
    product_report_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 将报告转换成便于人工阅读的缩进JSON
    product_report_json = json.dumps(
        product_evaluation_report,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    # 使用UTF-8写入报告，并在末尾保留换行
    product_report_file.write_text(
        product_report_json + "\n",
        encoding="utf-8",
    )

    # 返回实际报告路径，方便命令行提示用户
    return product_report_file


def evaluate_product_agent_result(
    product_evaluation_case: dict[str, object],
    product_agent_result: dict[str, object],
) -> dict[str, object]:
    """检查一次Agent执行结果是否符合评测标准。"""

    # 取得Agent生成的最终回答
    product_agent_answer = str(
        product_agent_result.get(
            "answer",
            "",
        )
    )

    # 取得Agent返回的原始工具调用记录
    product_raw_tool_events = (
        product_agent_result.get(
            "tool_events",
            [],
        )
    )

    # 防止tool_events不是列表
    if isinstance(product_raw_tool_events, list):
        product_tool_events = [
            product_tool_event
            for product_tool_event
            in product_raw_tool_events
            if isinstance(
                product_tool_event,
                dict,
            )
        ]
    else:
        product_tool_events = []

    # 取得评测标准中的正确工具名称
    product_expected_tool = (
        product_evaluation_case.get(
            "expected_tool"
        )
    )

    # 取得评测标准中的正确产品编号
    product_expected_product_id = (
        product_evaluation_case.get(
            "expected_product_id"
        )
    )

    # 判断当前用例是否要求检查工具返回的found字段
    product_should_check_found = (
        "expected_tool_result_found"
        in product_evaluation_case
    )

    # 取得工具返回的预期产品存在状态
    product_expected_found = (
        product_evaluation_case.get(
            "expected_tool_result_found"
        )
    )

    # 取得回答中应该出现的关键词
    product_expected_keywords = (
        product_evaluation_case.get(
            "expected_answer_keywords",
            [],
        )
    )

    # 保存Agent实际调用过的全部工具名称
    product_actual_tools = []

    # 保存Agent实际查询过的全部产品编号
    product_actual_product_ids = []

    # 标记是否存在工具和产品编号都正确的调用
    product_matching_tool_call_found = False

    # 保存工具和产品编号匹配时的全部found返回值
    product_matching_found_values = []

    # 遍历全部工具调用，而不是只检查第一次
    for product_tool_event in product_tool_events:

        # 取得当前工具调用的名称
        product_actual_tool = (
            product_tool_event.get(
                "tool_name"
            )
        )

        # 记录有效的工具名称
        if product_actual_tool is not None:
            product_actual_tools.append(
                product_actual_tool
            )

        # 取得当前工具调用的参数
        product_actual_arguments = (
            product_tool_event.get(
                "arguments",
                {},
            )
        )

        # 防止arguments不是字典
        if not isinstance(
            product_actual_arguments,
            dict,
        ):
            product_actual_arguments = {}

        # 优先读取真实工具定义使用的product_id参数
        # 同时兼容早期测试记录中的product_id字段
        product_actual_product_id = (
            product_actual_arguments.get(
                "product_id",
                product_actual_arguments.get(
                    "product_id"
                ),
            )
        )

        # 记录有效的产品编号
        if product_actual_product_id is not None:
            product_actual_product_ids.append(
                product_actual_product_id
            )

        # 检查当前调用是否同时符合工具和参数要求
        if (
            product_actual_tool
            == product_expected_tool
            and product_actual_product_id
            == product_expected_product_id
        ):
            product_matching_tool_call_found = True

            # 取得真实工具返回结果
            product_actual_tool_result = (
                product_tool_event.get(
                    "result",
                    {},
                )
            )

            # 只有字典结果才读取found字段
            if isinstance(
                product_actual_tool_result,
                dict,
            ):
                # 真实工具把业务数据放在result.data中
                product_actual_tool_data = (
                    product_actual_tool_result.get(
                        "data",
                        {},
                    )
                )

                # 防止工具data字段不是字典
                if not isinstance(
                    product_actual_tool_data,
                    dict,
                ):
                    product_actual_tool_data = {}

                # 优先读取真实嵌套字段
                # 同时兼容早期记录中的直接found字段
                product_actual_found = (
                    product_actual_tool_data.get(
                        "found",
                        product_actual_tool_result.get(
                            "found"
                        ),
                    )
                )

                # 保存当前匹配工具返回的产品存在状态
                product_matching_found_values.append(
                    product_actual_found
                )

    # 如果评测题不应该调用工具
    if product_expected_tool is None:

        # 实际也没有调用任何工具才算通过
        product_tool_passed = (
            len(product_tool_events) == 0
        )

    # 如果评测题要求调用工具
    else:

        # 检查全部调用中是否出现了正确工具
        product_tool_passed = (
            product_expected_tool
            in product_actual_tools
        )

    # 如果评测题不需要产品编号
    if product_expected_product_id is None:
        product_id_passed = True

    # 如果评测题要求指定产品编号
    else:

        # 必须存在工具和产品编号同时正确的调用
        product_id_passed = (
            product_matching_tool_call_found
        )

    # 题库没有规定found状态时不执行此项限制
    if not product_should_check_found:
        product_tool_result_passed = True

    # 题库规定了found状态时检查真实工具返回值
    else:
        product_tool_result_passed = (
            product_expected_found
            in product_matching_found_values
        )

    # 去除中英文千位分隔符，避免2600与2,600被误判
    product_normalized_answer = (
        product_agent_answer
        .replace(",", "")
        .replace("，", "")
    )

    # 找出最终回答中缺失的关键词
    product_missing_keywords = [
        str(product_expected_keyword)
        for product_expected_keyword
        in product_expected_keywords
        if (
            str(product_expected_keyword)
            .replace(",", "")
            .replace("，", "")
        )
        not in product_normalized_answer
    ]

    # 没有缺少关键词时通过关键词检查
    product_keywords_passed = (
        len(product_missing_keywords) == 0
    )

    # 三项评分必须全部通过
    product_evaluation_passed = all(
        [
            product_tool_passed,
            product_id_passed,
            product_tool_result_passed,
            product_keywords_passed,
        ]
    )

    # 返回评分和详细诊断信息
    return {
        "passed": product_evaluation_passed,
        "tool_passed": product_tool_passed,
        "product_id_passed": (
            product_id_passed
        ),
        "tool_result_passed": (
            product_tool_result_passed
        ),
        "keywords_passed": (
            product_keywords_passed
        ),
        "actual_tools": product_actual_tools,
        "actual_product_ids": (
            product_actual_product_ids
        ),
        "actual_found_values": (
            product_matching_found_values
        ),
        "missing_keywords": (
            product_missing_keywords
        ),
    }


def summarize_product_agent_evaluation_results(
    product_evaluation_results: list[dict[str, object]],
) -> dict[str, object]:
    """统计Agent评测的通过数量、失败数量和通过率。"""

    # 统计本次执行的测试用例总数
    product_total_count = len(
        product_evaluation_results
    )

    # 统计passed字段为真的评测结果数量
    product_passed_count = sum(
        1
        for product_evaluation_result
        in product_evaluation_results
        if product_evaluation_result.get(
            "passed",
            False,
        )
    )

    # 用总数减去通过数量得到失败数量
    product_failed_count = (
        product_total_count
        - product_passed_count
    )

    # 空结果不能直接做除法，因此通过率定义为0%
    if product_total_count == 0:
        product_pass_rate = 0.0

    # 有评测结果时换算百分比，并保留两位小数
    else:
        product_pass_rate = round(
            product_passed_count
            / product_total_count
            * 100,
            2,
        )

    # 返回结构化汇总结果
    return {
        "total_count": product_total_count,
        "passed_count": product_passed_count,
        "failed_count": product_failed_count,
        "pass_rate": product_pass_rate,
    }


def run_product_agent_evaluation_cases(
    product_evaluation_cases: list[dict[str, object]],
    product_agent_runner: Callable[
        [str],
        dict[str, object],
    ],
) -> dict[str, object]:
    """逐条运行Agent评测用例并返回完整报告。"""

    # 创建用于保存每道题详细结果的列表
    product_evaluation_results = []

    # 按题库顺序逐条执行评测
    for product_evaluation_case in (
        product_evaluation_cases
    ):

        # 取得当前测试用例的用户问题
        product_user_question = str(
            product_evaluation_case.get(
                "question",
                "",
            )
        )

        try:
            # 调用传入的Agent执行函数
            # 单元测试传本地函数，真实评测传产品Agent
            product_agent_result = product_agent_runner(
                product_user_question
            )

            # 对Agent返回内容执行确定性评分
            product_score_result = (
                evaluate_product_agent_result(
                    product_evaluation_case=(
                        product_evaluation_case
                    ),
                    product_agent_result=(
                        product_agent_result
                    ),
                )
            )

        # 单题发生API或Agent异常时不能中断整批评测
        except Exception as product_agent_error:

            # 将异常整理成一条明确的失败结果
            product_case_result = {
                "case_id": product_evaluation_case.get(
                    "case_id"
                ),
                "question": product_user_question,
                "answer": "",
                "passed": False,
                "tool_passed": False,
                "product_id_passed": False,
                "keywords_passed": False,
                "actual_tools": [],
                "actual_product_ids": [],
                "missing_keywords": (
                    product_evaluation_case.get(
                        "expected_answer_keywords",
                        [],
                    )
                ),
                "error_type": type(
                    product_agent_error
                ).__name__,
                "error_message": str(
                    product_agent_error
                ),
            }

        # Agent正常返回时生成评分明细
        else:
            product_case_result = {
                # 保存测试用例编号
                "case_id": product_evaluation_case.get(
                    "case_id"
                ),

                # 保存原始问题，方便查看失败用例
                "question": product_user_question,

                # 保存Agent答案用于人工复核
                "answer": product_agent_result.get(
                    "answer",
                    "",
                ),

                # 合并工具、参数和关键词评分结果
                **product_score_result,
            }

        # 将本题结果加入报告列表
        product_evaluation_results.append(
            product_case_result
        )

    # 根据全部题目结果生成汇总指标
    product_evaluation_summary = (
        summarize_product_agent_evaluation_results(
            product_evaluation_results
        )
    )

    # 返回汇总信息和逐题明细
    return {
        "summary": product_evaluation_summary,
        "results": product_evaluation_results,
    }


def main() -> None:
    """运行真实产品Agent评测并在终端输出报告。"""

    # 延迟导入真实Agent
    # 这样普通单元测试不会初始化外部API相关模块
    from product_agent.product_agent_service import (
        run_product_agent,
    )

    # 从项目默认JSON文件加载固定评测题库
    product_evaluation_cases = (
        load_product_agent_evaluation_cases()
    )

    # 提示本次真实评测需要逐题调用大模型API
    print(
        "外贸产品Agent自动评测开始，"
        f"共{len(product_evaluation_cases)}条测试用例。"
    )

    # 使用真实产品Agent运行全部测试用例
    product_evaluation_report = (
        run_product_agent_evaluation_cases(
            product_evaluation_cases=(
                product_evaluation_cases
            ),
            product_agent_runner=(
                run_product_agent
            ),
        )
    )

    # 把完整评测结果保存到项目JSON报告
    product_saved_report_file = (
        save_product_agent_evaluation_report(
            product_evaluation_report
        )
    )

    # 逐条输出测试用例的通过或失败状态
    for product_case_result in (
        product_evaluation_report["results"]
    ):
        product_case_status = (
            "PASS"
            if product_case_result["passed"]
            else "FAIL"
        )
        print(
            f"[{product_case_status}] "
            f"{product_case_result['case_id']}："
            f"{product_case_result['question']}"
        )

        # 失败用例额外输出具体评分或异常信息
        if not product_case_result["passed"]:
            print(
                "  工具检查："
                f"{product_case_result['tool_passed']}"
            )
            print(
                "  产品编号检查："
                f"{product_case_result['product_id_passed']}"
            )
            print(
                "  关键词检查："
                f"{product_case_result['keywords_passed']}"
            )
            print(
                "  缺失关键词："
                f"{product_case_result['missing_keywords']}"
            )

            # API异常存在时输出异常类型和消息
            if "error_type" in product_case_result:
                print(
                    "  执行异常："
                    f"{product_case_result['error_type']} - "
                    f"{product_case_result['error_message']}"
                )

    # 取得最终汇总指标
    product_evaluation_summary = (
        product_evaluation_report["summary"]
    )

    # 在终端显示便于简历记录的量化结果
    print("\n评测汇总：")
    print(
        "  测试总数："
        f"{product_evaluation_summary['total_count']}"
    )
    print(
        "  通过数量："
        f"{product_evaluation_summary['passed_count']}"
    )
    print(
        "  失败数量："
        f"{product_evaluation_summary['failed_count']}"
    )
    print(
        "  通过率："
        f"{product_evaluation_summary['pass_rate']}%"
    )
    print(
        "  JSON报告："
        f"{product_saved_report_file}"
    )


# 只有直接运行评测模块时才启动真实API评测
if __name__ == "__main__":
    main()
