"""验证 LangChain 产品业务 Agent 的工具注册与查询能力。"""

import unittest
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


if __name__ == "__main__":
    unittest.main()
