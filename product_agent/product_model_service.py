# 导入os模块，用于读取操作系统环境变量
import os

# 导入Path，用于可靠地定位项目根目录和.env文件
from pathlib import Path

# 导入load_dotenv，用于读取.env文件中的配置
from dotenv import load_dotenv

# 导入OpenAI客户端，用来调用兼容OpenAI格式的大模型API
from openai import OpenAI


# 获取当前Python文件所在的绝对路径
product_current_file = Path(__file__).resolve()

# 当前文件位于product_agent目录中，因此向上两级得到项目根目录
product_project_root = product_current_file.parent.parent

# 拼接出项目根目录下.env文件的完整路径
product_env_file = product_project_root / ".env"

# 加载.env文件中的API配置
load_dotenv(dotenv_path=product_env_file)


def create_product_model_client() -> OpenAI:
    """创建并返回外贸文档智能体使用的大模型客户端。"""

    # 从.env中读取API密钥
    product_api_key = os.getenv("TRADE_AGENT_API_KEY")

    # 从.env中读取API地址
    # 如果没有设置，就使用DeepSeek官方API地址
    product_base_url = os.getenv(
        "TRADE_AGENT_BASE_URL",
        "https://api.deepseek.com",
    )

    # 如果没有读取到API密钥，主动终止程序并给出明确提示
    if not product_api_key:
        raise ValueError(
            "没有读取到TRADE_AGENT_API_KEY，请检查项目根目录下的.env文件。"
        )

    # 创建兼容OpenAI格式的大模型客户端
    product_model_client = OpenAI(
        api_key=product_api_key,
        base_url=product_base_url,
    )

    # 将创建好的客户端返回给调用者
    return product_model_client


def ask_product_model(product_user_question: str) -> str:
    """向大模型发送用户问题，并返回文本回答。"""

    # 删除问题首尾的空格，避免把空白内容发送给API
    product_clean_question = product_user_question.strip()

    # 检查用户是否输入了有效问题
    if not product_clean_question:
        raise ValueError("问题不能为空，请输入有效问题。")

    # 创建大模型客户端
    product_model_client = create_product_model_client()

    # 从.env中读取模型名称
    # 如果没有设置，就使用默认模型
    product_model_name = os.getenv(
        "TRADE_AGENT_MODEL",
        "deepseek-v4-flash",
    )

    # 调用大模型的聊天接口
    product_response = product_model_client.chat.completions.create(
        # 指定本次请求使用的模型
        model=product_model_name,

        # messages用于描述对话中的不同角色和内容
        messages=[
            {
                # system消息用于规定智能体的身份和回答规则
                "role": "system",

                # 当前还没有接入企业知识库，所以要求模型不要假装掌握企业资料
                "content": (
                    "你是外贸文档智能体的基础问答助手。"
                    "当前尚未接入企业知识库，只能回答一般性问题。"
                    "如果问题依赖具体企业资料，请明确说明无法确定，"
                    "不要编造产品规格、价格或库存。"
                ),
            },
            {
                # user消息表示真实用户提交的问题
                "role": "user",

                # 把清理后的用户问题发送给模型
                "content": product_clean_question,
            },
        ],
    )

    # 从API响应中取出模型生成的文本
    product_model_answer = product_response.choices[0].message.content

    # 防止API成功返回但回答内容为空
    if not product_model_answer:
        raise RuntimeError("大模型没有返回有效回答。")

    # 清除回答首尾多余空格后返回
    return product_model_answer.strip()


# 只有直接运行当前文件时，才执行下面的测试代码
# 以后网页导入这个模块时，这部分代码不会自动执行
if __name__ == "__main__":

    # 提示用户当前正在进行命令行测试
    print("外贸文档智能体：大模型API命令行测试")

    # 接收用户在命令行中输入的问题
    product_test_question = input("请输入测试问题：")

    try:
        # 调用前面编写的函数获取模型回答
        product_test_answer = ask_product_model(product_test_question)

    # 在程序最外层捕获错误，避免只显示难以理解的错误堆栈
    except Exception as product_test_error:

        # 输出具体错误，方便后续定位API或配置问题
        print(f"模型调用失败：{product_test_error}")

    else:
        # API调用成功后输出模型回答
        print("\n模型回答：")
        print(product_test_answer)
