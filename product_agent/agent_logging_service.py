# 导入json，用于将日志保存成结构化JSON
import json

# 导入logging，用于记录程序运行信息
import logging

# 导入RotatingFileHandler
# 它可以在日志过大时自动轮换文件
from logging.handlers import RotatingFileHandler

# 导入datetime，用于记录带时区的事件时间
from datetime import datetime

# 导入Path，用于构造日志目录和文件路径
from pathlib import Path


# 取得当前日志模块的绝对路径
product_logging_file = Path(__file__).resolve()

# 向上两级取得项目根目录
product_project_root = product_logging_file.parent.parent

# 设置项目日志目录
TRADE_LOG_DIRECTORY = (
    product_project_root / "trade_logs"
)

# 设置项目主日志文件
TRADE_LOG_FILE = (
    TRADE_LOG_DIRECTORY / "product_agent.log"
)

# 定义需要自动脱敏的敏感字段关键词
TRADE_SENSITIVE_KEYWORDS = {
    "api_key",
    "authorization",
    "password",
    "secret",
    "token",
}


def sanitize_product_log_data(
    product_log_data: object,
) -> object:
    """递归清理日志数据中的敏感字段。"""

    # 如果当前数据是字典，则逐个检查字段
    if isinstance(product_log_data, dict):

        # 创建脱敏后的新字典
        product_clean_dictionary = {}

        # 逐个处理字典中的字段和值
        for product_key, product_value in product_log_data.items():

            # 将字段名转换成小写字符串
            product_lower_key = str(product_key).lower()

            # 判断字段名是否包含敏感关键词
            product_is_sensitive = any(
                product_sensitive_keyword
                in product_lower_key
                for product_sensitive_keyword
                in TRADE_SENSITIVE_KEYWORDS
            )

            # 敏感字段使用固定文字替换真实内容
            if product_is_sensitive:
                product_clean_dictionary[product_key] = (
                    "[REDACTED]"
                )

            # 非敏感字段继续递归检查
            else:
                product_clean_dictionary[product_key] = (
                    sanitize_product_log_data(
                        product_value
                    )
                )

        # 返回脱敏完成的字典
        return product_clean_dictionary

    # 如果当前数据是列表，则逐项递归清理
    if isinstance(product_log_data, list):
        return [
            sanitize_product_log_data(product_item)
            for product_item in product_log_data
        ]

    # 如果当前数据是元组，也逐项递归清理
    if isinstance(product_log_data, tuple):
        return [
            sanitize_product_log_data(product_item)
            for product_item in product_log_data
        ]

    # 普通字符串、数字等数据直接返回
    return product_log_data


def create_product_logger() -> logging.Logger:
    """创建外贸文档智能体专用日志记录器。"""

    # 如果日志目录不存在，就自动创建
    TRADE_LOG_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 获取项目专用日志记录器
    product_logger = logging.getLogger(
        "foreign_trade_product_agent"
    )

    # 设置最低记录级别为INFO
    product_logger.setLevel(logging.INFO)

    # 禁止日志继续传递给根记录器
    # 这样可以避免同一条日志重复输出
    product_logger.propagate = False

    # Streamlit每次重新运行代码时可能重复创建处理器
    # 只有当前记录器没有处理器时才添加
    if not product_logger.handlers:

        # 创建支持自动轮换的文件处理器
        product_log_handler = RotatingFileHandler(
            # 指定日志文件
            filename=TRADE_LOG_FILE,

            # 单个日志文件最大约1MB
            maxBytes=1_000_000,

            # 最多保留3个旧日志文件
            backupCount=3,

            # 使用UTF-8保存中文
            encoding="utf-8",
        )

        # 日志消息本身已经是JSON，因此不再添加其他格式
        product_log_handler.setFormatter(
            logging.Formatter("%(message)s")
        )

        # 将文件处理器加入项目记录器
        product_logger.addHandler(
            product_log_handler
        )

    # 返回配置完成的日志记录器
    return product_logger


# 创建整个项目共享的日志记录器
TRADE_AGENT_LOGGER = create_product_logger()


def record_product_event(
    product_event_type: str,
    product_event_status: str,
    product_event_details: dict[str, object] | None = None,
) -> None:
    """将一条结构化运行事件写入日志文件。"""

    # 如果调用者没有提供详情，就使用空字典
    if product_event_details is None:
        product_event_details = {}

    # 对日志详情中的敏感字段进行脱敏
    product_safe_details = sanitize_product_log_data(
        product_event_details
    )

    # 构造结构化日志记录
    product_log_record = {
        # 使用本地时区记录ISO格式时间
        "timestamp": (
            datetime.now()
            .astimezone()
            .isoformat(timespec="seconds")
        ),

        # 记录事件类型
        "event_type": product_event_type,

        # 记录成功、失败等状态
        "status": product_event_status,

        # 保存具体事件信息
        "details": product_safe_details,
    }

    # 将字典转换成一行JSON并写入日志
    TRADE_AGENT_LOGGER.info(
        json.dumps(
            product_log_record,
            ensure_ascii=False,
            default=str,
        )
    )


def record_product_error(
    product_event_type: str,
    product_error: Exception,
    product_event_details: dict[str, object] | None = None,
) -> None:
    """记录程序异常及其类型。"""

    # 复制调用者提供的详情，避免修改原字典
    product_error_details = dict(
        product_event_details or {}
    )

    # 记录异常所属的Python类型
    product_error_details["error_type"] = (
        type(product_error).__name__
    )

    # 记录异常消息
    product_error_details["error_message"] = str(
        product_error
    )

    # 调用统一事件函数记录失败日志
    record_product_event(
        product_event_type=product_event_type,
        product_event_status="failed",
        product_event_details=product_error_details,
    )


# 只有直接运行当前模块时，才执行日志测试
if __name__ == "__main__":

    # 记录一条模拟的成功事件
    record_product_event(
        product_event_type="agent_tool_call",
        product_event_status="success",
        product_event_details={
            "tool_name": "query_product",
            "product_id": "A001",
            "duration_ms": 125,
            "api_key": "这段内容应该被自动隐藏",
        },
    )

    try:
        # 主动制造一个模拟错误，用于测试错误日志
        raise ValueError("模拟的Agent参数错误")

    # 捕获刚刚制造的模拟错误
    except Exception as product_test_error:

        # 将错误写入结构化日志
        record_product_error(
            product_event_type="agent_execution",
            product_error=product_test_error,
            product_event_details={
                "agent_step": 2,
                "tool_name": "query_product",
            },
        )

    # 提示日志测试完成
    print("外贸文档智能体日志测试完成。")

    # 显示日志文件的实际位置
    print(f"日志文件：{TRADE_LOG_FILE}")

    # 读取日志文件中的全部记录
    product_log_lines = (
        TRADE_LOG_FILE
        .read_text(encoding="utf-8")
        .splitlines()
    )

    # 只显示最后两条测试日志
    for product_log_line in product_log_lines[-2:]:

        # 输出当前JSON日志
        print(product_log_line)
