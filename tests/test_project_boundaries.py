"""验证产品 Agent 项目从干净的运行数据状态开始。"""

import unittest
from pathlib import Path


# 通过测试文件位置定位 Agent 项目根目录，避免依赖当前终端目录。
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ProductAgentProjectBoundaryTest(unittest.TestCase):
    """验证 Agent 项目的配置文件和运行数据边界。"""

    def test_project_has_safe_configuration_files(self) -> None:
        """项目应提供依赖清单和不含真实密钥的环境变量示例。"""

        requirements_file = PROJECT_ROOT / "requirements.txt"
        environment_example_file = PROJECT_ROOT / ".env.example"

        self.assertTrue(requirements_file.is_file())
        self.assertTrue(environment_example_file.is_file())

        environment_example_text = environment_example_file.read_text(
            encoding="utf-8"
        )
        self.assertIn("TRADE_AGENT_API_KEY=", environment_example_text)
        self.assertNotIn("sk-", environment_example_text)

    def test_project_does_not_package_old_runtime_data(self) -> None:
        """新项目只允许页面初始化产生空数据库，不携带旧运行数据。"""

        product_database_directory = (
            PROJECT_ROOT / "trade_data" / "database"
        )

        # SQLite 空数据库会在首次打开网页时创建；它必须位于本项目内。
        if product_database_directory.exists():
            self.assertEqual(
                [
                    product_database_file.name
                    for product_database_file in product_database_directory.glob("*.db")
                ],
                ["product_agent.db"],
            )

        # 上传资料不属于产品 Agent 的数据模型，不应被迁入新项目。
        self.assertFalse(
            (PROJECT_ROOT / "trade_data" / "uploads").exists()
        )


if __name__ == "__main__":
    unittest.main()
