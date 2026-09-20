"""验证原生 Function Calling 学习示例可独立导入和使用。"""

import unittest

from examples.native_function_calling_reference import (
    run_product_agent,
)


class NativeFunctionCallingReferenceTest(unittest.TestCase):
    """验证归档示例不依赖正式 LangChain 运行入口。"""

    def test_reference_rejects_empty_question_before_calling_api(
        self,
    ) -> None:
        """示例应在空问题时本地校验，避免无意义的模型请求。"""

        with self.assertRaisesRegex(ValueError, "不能为空"):
            run_product_agent("")


if __name__ == "__main__":
    unittest.main()
