"""验证 LangChain 产品业务 Agent 的工具注册与查询能力。"""

import unittest

from product_agent.langchain_product_agent_service import (
    TRADE_LANGCHAIN_PRODUCT_TOOLS,
    run_langchain_product_tool,
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


if __name__ == "__main__":
    unittest.main()
