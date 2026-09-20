"""验证产品查询工具能够读取项目内置的模拟 CSV 数据。"""

import unittest

from product_agent.agent_evaluator import (
    load_product_agent_evaluation_cases,
)
from product_agent.product_agent_service import (
    TRADE_AGENT_TOOL_DEFINITIONS,
)
from product_agent.product_tools import query_product


class ProductToolsTest(unittest.TestCase):
    """验证真实产品数据文件与查询工具的集成。"""

    def test_query_existing_product_from_project_csv(self) -> None:
        """查询 A001 时，应从项目自带 CSV 返回对应产品。"""

        product_result = query_product("A001")

        self.assertTrue(product_result["found"])
        self.assertEqual(product_result["product_id"], "A001")
        self.assertEqual(product_result["unit_price_usd"], 8.5)

    def test_evaluation_cases_reference_registered_tools(self) -> None:
        """题库中的工具名应与 Agent 实际注册的工具保持一致。"""

        product_registered_tool_names = {
            product_tool_definition["function"]["name"]
            for product_tool_definition
            in TRADE_AGENT_TOOL_DEFINITIONS
        }

        for product_evaluation_case in (
            load_product_agent_evaluation_cases()
        ):
            product_expected_tool = (
                product_evaluation_case.get("expected_tool")
            )

            if product_expected_tool is not None:
                self.assertIn(
                    product_expected_tool,
                    product_registered_tool_names,
                )


if __name__ == "__main__":
    unittest.main()
