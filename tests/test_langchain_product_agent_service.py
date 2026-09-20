"""验证 LangChain 产品业务 Agent 的工具注册与查询能力。"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.messages import AIMessage

from product_agent.langchain_product_agent_service import (
    TRADE_LANGCHAIN_PRODUCT_TOOLS,
    run_langchain_product_agent,
    run_langchain_product_tool,
    select_langchain_product_fields,
)


class LangChainProductAgentServiceTest(unittest.TestCase):
    """验证 LangChain 服务使用项目内置的真实产品 CSV。"""

    def test_langchain_product_tool_uses_project_csv(self) -> None:
        """LangChain Tool 应注册为 query_product 并查询 A001。"""

        product_tool_names = {
            product_tool.name
            for product_tool in TRADE_LANGCHAIN_PRODUCT_TOOLS
        }
        product_tool_result = run_langchain_product_tool("A001")

        self.assertEqual(product_tool_names, {"query_product"})
        self.assertTrue(product_tool_result["success"])
        self.assertTrue(product_tool_result["data"]["found"])
        self.assertEqual(
            product_tool_result["data"]["unit_price_usd"],
            8.5,
        )

    def test_price_and_stock_tool_result_hides_unrequested_fields(
        self,
    ) -> None:
        """价格和库存问题的工具结果不应携带未请求的业务字段。"""

        product_result = run_langchain_product_tool("A001")
        product_selected_result = select_langchain_product_fields(
            product_tool_result=product_result,
            product_user_question="查询 A001 价格和库存",
        )
        product_data = product_selected_result["data"]

        self.assertIn("unit_price_usd", product_data)
        self.assertIn("stock_square_meters", product_data)
        self.assertNotIn("size_mm", product_data)
        self.assertNotIn("min_order_square_meters", product_data)
        self.assertNotIn("lead_time_days", product_data)

    @patch(
        "product_agent.langchain_product_agent_service."
        "create_langchain_product_model"
    )
    def test_agent_records_query_product_tool_event(
        self,
        product_model_factory_mock,
    ) -> None:
        """Agent 应通过 LangChain Tool 查询 A001 并保存可评测事件。"""

        class FakeBoundProductModel:
            """按顺序返回工具调用和最终回答的模拟绑定模型。"""

            def __init__(self) -> None:
                """初始化当前模拟模型的调用次数。"""

                self.product_invoke_count = 0

            def invoke(self, product_messages):
                """第一次请求工具，第二次根据工具结果回答。"""

                self.product_invoke_count += 1

                if self.product_invoke_count == 1:
                    return AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "query_product",
                                "args": {"product_id": "A001"},
                                "id": "call_a001",
                            }
                        ],
                    )

                return AIMessage(
                    content="A001 的价格为 8.5 美元，库存为 2600 平方米。",
                )

        class FakeProductModel:
            """提供 bind_tools 方法的模拟 LangChain 模型。"""

            def __init__(self) -> None:
                """创建同一个绑定后的模拟模型。"""

                self.product_bound_model = FakeBoundProductModel()

            def bind_tools(self, product_tools):
                """接收 LangChain Tool 列表并返回可调用模型。"""

                self.product_received_tools = product_tools
                return self.product_bound_model

        product_model_factory_mock.return_value = FakeProductModel()

        product_agent_result = run_langchain_product_agent(
            "查询 A001 价格和库存"
        )

        self.assertIn("8.5", product_agent_result["answer"])
        self.assertEqual(
            product_agent_result["tool_events"][0]["tool_name"],
            "query_product",
        )
        self.assertEqual(
            product_agent_result["tool_events"][0]["arguments"],
            {"product_id": "A001"},
        )
        self.assertTrue(
            product_agent_result["tool_events"][0]["result"]["data"]["found"]
        )

    @patch(
        "product_agent.langchain_product_agent_service."
        "create_langchain_product_model"
    )
    def test_agent_returns_tool_parameter_error_without_crashing(
        self,
        product_model_factory_mock,
    ) -> None:
        """非字典工具参数应作为结果回传，而不是中断 Agent。"""

        class FakeBoundProductModel:
            """先返回错误参数，再返回模型最终回答。"""

            def __init__(self) -> None:
                """初始化模拟模型的调用次数。"""

                self.product_invoke_count = 0

            def invoke(self, product_messages):
                """模拟一条参数错误的工具调用和后续回答。"""

                self.product_invoke_count += 1
                if self.product_invoke_count == 1:
                    return SimpleNamespace(
                        content="",
                        tool_calls=[
                            {
                                "name": "query_product",
                                "args": ["A001"],
                                "id": "call_invalid_arguments",
                            }
                        ],
                    )
                return SimpleNamespace(
                    content="产品查询参数格式不正确。",
                    tool_calls=[],
                )

        class FakeProductModel:
            """提供绑定工具能力的模拟模型。"""

            def bind_tools(self, product_tools):
                """返回可按顺序执行的模拟模型。"""

                return FakeBoundProductModel()

        product_model_factory_mock.return_value = FakeProductModel()

        product_agent_result = run_langchain_product_agent("查询 A001")

        self.assertIn("参数格式", product_agent_result["answer"])
        self.assertEqual(
            product_agent_result["tool_events"][0]["result"]["error"],
            "工具参数必须是 JSON 对象。",
        )

    @patch(
        "product_agent.langchain_product_agent_service."
        "create_langchain_product_model"
    )
    def test_agent_stops_after_configured_tool_step_limit(
        self,
        product_model_factory_mock,
    ) -> None:
        """模型持续请求工具时，Agent 应在指定步数后中止。"""

        class FakeBoundProductModel:
            """每轮都请求同一个有效的产品查询工具。"""

            def __init__(self) -> None:
                """初始化调用序号，用于生成唯一工具调用标识。"""

                self.product_invoke_count = 0

            def invoke(self, product_messages):
                """返回不会结束的工具调用。"""

                self.product_invoke_count += 1
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "query_product",
                            "args": {"product_id": "A001"},
                            "id": f"call_{self.product_invoke_count}",
                        }
                    ],
                )

        class FakeProductModel:
            """提供绑定工具能力的模拟模型。"""

            def bind_tools(self, product_tools):
                """返回会持续请求工具的模拟模型。"""

                return FakeBoundProductModel()

        product_model_factory_mock.return_value = FakeProductModel()

        with self.assertRaisesRegex(RuntimeError, "2 步内未完成"):
            run_langchain_product_agent(
                "查询 A001 价格",
                product_max_steps=2,
            )


if __name__ == "__main__":
    unittest.main()
