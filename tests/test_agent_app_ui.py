"""验证独立产品 Agent 网页不包含 RAG 上传入口。"""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ProductAgentAppUiTest(unittest.TestCase):
    """验证 Agent 网页的独立入口。"""

    def test_agent_page_has_chat_input_without_document_uploader(self) -> None:
        """产品 Agent 应有聊天输入，但不应有任何文档上传控件。"""

        app = AppTest.from_file(
            str(PROJECT_ROOT / "agent_app.py")
        ).run(timeout=45)

        self.assertFalse(app.exception)
        self.assertEqual(len(app.file_uploader), 0)
        self.assertIsNotNone(app.chat_input(key="agent_question_input"))

    def test_agent_page_and_evaluator_use_langchain_service(
        self,
    ) -> None:
        """页面和真实评测器都应使用正式的 LangChain Agent 链路。"""

        product_agent_app_source = (
            PROJECT_ROOT / "agent_app.py"
        ).read_text(encoding="utf-8")
        product_evaluator_source = (
            PROJECT_ROOT
            / "product_agent"
            / "agent_evaluator.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "from product_agent.langchain_product_agent_service import (",
            product_agent_app_source,
        )
        self.assertIn(
            "run_langchain_product_agent",
            product_agent_app_source,
        )
        self.assertIn(
            "from product_agent.langchain_product_agent_service import (",
            product_evaluator_source,
        )
        self.assertIn(
            "run_langchain_product_agent",
            product_evaluator_source,
        )


if __name__ == "__main__":
    unittest.main()
