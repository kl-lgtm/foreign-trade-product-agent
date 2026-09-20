# 导入json，用于保存和恢复RAG来源、工具事件等调试信息
import json

# 导入closing，确保SQLite连接在事务结束后真正释放文件句柄。
from contextlib import closing

# 导入sqlite3，用于操作本地SQLite数据库
import sqlite3

# 导入datetime，用于保存消息创建时间
from datetime import datetime

# 导入Path，用于构造数据库文件路径
from pathlib import Path


# 获取当前代码文件的绝对路径
product_repository_file = Path(__file__).resolve()

# 向上两级取得项目根目录
product_project_root = product_repository_file.parent.parent

# 设置SQLite数据库目录
TRADE_DATABASE_DIRECTORY = (
    product_project_root
    / "trade_data"
    / "database"
)

# 设置SQLite数据库文件
TRADE_DATABASE_FILE = (
    TRADE_DATABASE_DIRECTORY
    / "product_agent.db"
)

# 定义允许写入数据库的问答模式
TRADE_ALLOWED_MODES = {
    "产品业务Agent",
}

# 定义允许写入数据库的消息角色
TRADE_ALLOWED_ROLES = {
    "user",
    "assistant",
}


def connect_trade_database() -> sqlite3.Connection:
    """创建并返回SQLite数据库连接。"""

    # 确保数据库目录存在
    TRADE_DATABASE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 创建SQLite连接
    trade_database_connection = sqlite3.connect(
        # 指定数据库文件
        database=TRADE_DATABASE_FILE,

        # 数据库繁忙时最多等待10秒
        timeout=10,
    )

    # 让查询结果支持通过字段名称读取
    trade_database_connection.row_factory = (
        sqlite3.Row
    )

    # 返回数据库连接
    return trade_database_connection


def initialize_product_chat_database() -> None:
    """初始化会话消息表和查询索引。"""

    # 使用with确保操作结束后自动提交或回滚
    with closing(connect_trade_database()) as product_connection, product_connection:

        # 启用WAL模式，改善读写并发能力
        product_connection.execute(
            "PRAGMA journal_mode=WAL"
        )

        # 创建会话消息表
        # IF NOT EXISTS可以避免重复创建时报错
        product_connection.execute(
            """
            CREATE TABLE IF NOT EXISTS product_chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                debug_json TEXT NOT NULL DEFAULT '{}',
                is_error INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )

        # 创建会话和模式组合索引
        # 它可以加快聊天记录查询速度
        product_connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_product_chat_conversation_mode
            ON product_chat_messages (
                conversation_id,
                mode,
                id
            )
            """
        )


def validate_product_chat_message(
    product_conversation_id: str,
    product_mode: str,
    product_role: str,
    product_content: str,
) -> None:
    """验证准备写入数据库的消息字段。"""

    # 会话编号不能为空
    if not product_conversation_id.strip():
        raise ValueError("会话编号不能为空。")

    # 模式必须属于项目允许的范围
    if product_mode not in TRADE_ALLOWED_MODES:
        raise ValueError(
            f"不支持的问答模式：{product_mode}"
        )

    # 角色只能是用户或助手
    if product_role not in TRADE_ALLOWED_ROLES:
        raise ValueError(
            f"不支持的消息角色：{product_role}"
        )

    # 消息正文不能为空
    if not product_content.strip():
        raise ValueError("消息正文不能为空。")


def save_product_chat_message(
    product_conversation_id: str,
    product_mode: str,
    product_role: str,
    product_content: str,
    product_debug_data: dict[str, object] | None = None,
    product_is_error: bool = False,
) -> int:
    """保存一条聊天消息，并返回数据库消息编号。"""

    # 验证所有关键消息字段
    validate_product_chat_message(
        product_conversation_id=product_conversation_id,
        product_mode=product_mode,
        product_role=product_role,
        product_content=product_content,
    )

    # 没有调试信息时使用空字典
    if product_debug_data is None:
        product_debug_data = {}

    # 将调试字典转换成JSON字符串
    product_debug_json = json.dumps(
        product_debug_data,
        ensure_ascii=False,
        default=str,
    )

    # 生成带本地时区的消息时间
    product_created_at = (
        datetime.now()
        .astimezone()
        .isoformat(timespec="seconds")
    )

    # 打开数据库连接
    with closing(connect_trade_database()) as product_connection, product_connection:

        # 使用参数化SQL写入消息
        # 问号参数可以避免SQL注入和引号问题
        product_cursor = product_connection.execute(
            """
            INSERT INTO product_chat_messages (
                conversation_id,
                mode,
                role,
                content,
                debug_json,
                is_error,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_conversation_id,
                product_mode,
                product_role,
                product_content,
                product_debug_json,
                int(product_is_error),
                product_created_at,
            ),
        )

        # 取得SQLite自动生成的消息编号
        product_message_id = product_cursor.lastrowid

    # 防止数据库没有返回有效编号
    if product_message_id is None:
        raise RuntimeError(
            "数据库没有返回消息编号。"
        )

    # 返回新消息的整数编号
    return int(product_message_id)


def load_product_chat_messages(
    product_conversation_id: str,
    product_mode: str,
) -> list[dict[str, object]]:
    """按会话编号和模式读取历史消息。"""

    # 验证会话编号
    if not product_conversation_id.strip():
        raise ValueError("会话编号不能为空。")

    # 验证问答模式
    if product_mode not in TRADE_ALLOWED_MODES:
        raise ValueError(
            f"不支持的问答模式：{product_mode}"
        )

    # 打开数据库连接
    with closing(connect_trade_database()) as product_connection, product_connection:

        # 按消息编号升序读取历史记录
        product_message_rows = product_connection.execute(
            """
            SELECT
                id,
                role,
                content,
                debug_json,
                is_error,
                created_at
            FROM product_chat_messages
            WHERE conversation_id = ?
              AND mode = ?
            ORDER BY id ASC
            """,
            (
                product_conversation_id,
                product_mode,
            ),
        ).fetchall()

    # 创建转换后的消息列表
    product_chat_messages = []

    # 逐条处理数据库查询结果
    for product_message_row in product_message_rows:

        try:
            # 将调试JSON恢复成Python字典
            product_debug_data = json.loads(
                product_message_row["debug_json"]
            )

        # 如果某条历史JSON损坏，则使用空字典
        except json.JSONDecodeError:
            product_debug_data = {}

        # 整理成网页当前使用的消息结构
        product_chat_messages.append(
            {
                # 保存数据库消息编号
                "id": product_message_row["id"],

                # 保存用户或助手角色
                "role": product_message_row["role"],

                # 保存消息正文
                "content": product_message_row["content"],

                # 保存RAG来源或Agent工具记录
                "debug": product_debug_data,

                # 将SQLite整数恢复成布尔值
                "is_error": bool(
                    product_message_row["is_error"]
                ),

                # 保存消息创建时间
                "created_at": (
                    product_message_row["created_at"]
                ),
            }
        )

    # 返回全部历史消息
    return product_chat_messages


def clear_product_chat_messages(
    product_conversation_id: str,
    product_mode: str,
) -> int:
    """清空指定会话和模式中的消息。"""

    # 验证会话编号
    if not product_conversation_id.strip():
        raise ValueError("会话编号不能为空。")

    # 验证问答模式
    if product_mode not in TRADE_ALLOWED_MODES:
        raise ValueError(
            f"不支持的问答模式：{product_mode}"
        )

    # 打开数据库连接
    with closing(connect_trade_database()) as product_connection, product_connection:

        # 只删除当前会话和当前模式的消息
        product_cursor = product_connection.execute(
            """
            DELETE FROM product_chat_messages
            WHERE conversation_id = ?
              AND mode = ?
            """,
            (
                product_conversation_id,
                product_mode,
            ),
        )

        # 取得本次实际删除的消息数量
        product_deleted_count = product_cursor.rowcount

    # 返回删除数量
    return product_deleted_count


# 只有直接运行当前模块时，才执行测试
if __name__ == "__main__":

    # 创建数据库和消息表
    initialize_product_chat_database()

    # 使用独立测试会话，避免影响真实聊天
    product_test_conversation_id = (
        "product_repository_test"
    )

    # 测试前清除旧测试数据
    clear_product_chat_messages(
        product_conversation_id=(
            product_test_conversation_id
        ),
        product_mode="产品业务Agent",
    )

    # 保存一条模拟用户消息
    save_product_chat_message(
        product_conversation_id=(
            product_test_conversation_id
        ),
        product_mode="产品业务Agent",
        product_role="user",
        product_content="查询A001价格和库存",
    )

    # 保存一条带工具记录的模拟助手消息
    save_product_chat_message(
        product_conversation_id=(
            product_test_conversation_id
        ),
        product_mode="产品业务Agent",
        product_role="assistant",
        product_content=(
            "A001价格为8.50美元/平方米，"
            "库存为2600平方米。"
        ),
        product_debug_data={
            "tool_events": [
                {
                    "step": 1,
                    "tool_name": (
                        "query_product"
                    ),
                }
            ]
        },
    )

    # 从数据库重新读取测试消息
    product_test_messages = load_product_chat_messages(
        product_conversation_id=(
            product_test_conversation_id
        ),
        product_mode="产品业务Agent",
    )

    # 显示数据库文件路径
    print(f"数据库文件：{TRADE_DATABASE_FILE}")

    # 显示读取到的消息数量
    print(
        f"成功读取"
        f"{len(product_test_messages)}条消息。"
    )

    # 逐条显示恢复后的消息
    for product_test_message in product_test_messages:

        # 将消息转换成便于阅读的JSON
        print(
            json.dumps(
                product_test_message,
                ensure_ascii=False,
                indent=2,
            )
        )
