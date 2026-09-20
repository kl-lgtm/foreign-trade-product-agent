"""验证产品 Agent 的 SQLite 会话记录能够保存、隔离并恢复。"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from product_agent import agent_chat_repository


class ProductAgentChatRepositoryConnectionTest(unittest.TestCase):
    """为产品 Agent 的独立会话数据库提供连接级回归测试。"""

    def setUp(self) -> None:
        """为每个测试创建相互隔离的临时 SQLite 数据库。"""

        self.temporary_directory = tempfile.TemporaryDirectory()
        database_file = Path(self.temporary_directory.name) / "agent.db"

        self.database_file_patch = patch.object(
            agent_chat_repository,
            "TRADE_DATABASE_FILE",
            database_file,
        )
        self.database_directory_patch = patch.object(
            agent_chat_repository,
            "TRADE_DATABASE_DIRECTORY",
            database_file.parent,
        )
        self.database_file_patch.start()
        self.database_directory_patch.start()
        agent_chat_repository.initialize_product_chat_database()

    def tearDown(self) -> None:
        """停止补丁并清理本测试创建的临时目录。"""

        self.database_directory_patch.stop()
        self.database_file_patch.stop()
        self.temporary_directory.cleanup()

    def test_messages_are_restored_only_for_the_same_conversation(self) -> None:
        """相同会话可恢复，其他会话不可见。"""

        agent_chat_repository.save_product_chat_message(
            product_conversation_id="conversation-a",
            product_mode="产品业务Agent",
            product_role="user",
            product_content="查询 A001 价格",
        )
        agent_chat_repository.save_product_chat_message(
            product_conversation_id="conversation-b",
            product_mode="产品业务Agent",
            product_role="user",
            product_content="查询 A002 库存",
        )

        conversation_a_messages = (
            agent_chat_repository.load_product_chat_messages(
                product_conversation_id="conversation-a",
                product_mode="产品业务Agent",
            )
        )

        self.assertEqual(len(conversation_a_messages), 1)
        self.assertEqual(
            conversation_a_messages[0]["content"],
            "查询 A001 价格",
        )


if __name__ == "__main__":
    unittest.main()
