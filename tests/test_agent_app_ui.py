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


if __name__ == "__main__":
    unittest.main()
