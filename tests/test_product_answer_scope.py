"""验证产品 Agent 只把用户询问的字段交给大模型。"""

import unittest

from product_agent.product_answer_scope import (
    select_product_fields_for_answer,
)


# 用完整模拟记录验证字段裁剪逻辑，不访问 API 或 CSV 文件。
FULL_A001_RESULT = {
    "success": True,
    "data": {
        "found": True,
        "product_id": "A001",
        "product_name_cn": "爵士白抛光瓷砖",
        "product_name_en": "Carrara White Polished Porcelain Tile",
        "size_mm": "600x600x9",
        "surface": "抛光面",
        "unit_price_usd": "8.50",
        "stock_square_meters": "2600",
        "min_order_square_meters": "1000",
        "lead_time_days": "25",
        "data_notice": "模拟测试数据，不代表真实企业。",
    },
}


class ProductAnswerScopeTest(unittest.TestCase):
    """验证字段筛选与用户问题范围一致。"""

    def test_price_and_stock_hides_unrequested_fields(self) -> None:
        """询问价格和库存时，规格、起订量和交期不应出现在工具结果。"""

        selected_result = select_product_fields_for_answer(
            product_tool_result=FULL_A001_RESULT,
            product_user_question="查询 A001 的价格和库存",
        )

        selected_data = selected_result["data"]
        self.assertIn("unit_price_usd", selected_data)
        self.assertIn("stock_square_meters", selected_data)
        self.assertNotIn("size_mm", selected_data)
        self.assertNotIn("min_order_square_meters", selected_data)
        self.assertNotIn("lead_time_days", selected_data)


if __name__ == "__main__":
    unittest.main()
