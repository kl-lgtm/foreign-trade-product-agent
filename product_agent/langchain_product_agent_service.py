"""使用 LangChain 编排外贸产品查询工具与大模型的服务模块。"""

# 导入 LangChain 的基础工具类型和工具装饰器。
from langchain_core.tools import BaseTool, tool

# 导入项目唯一的产品 CSV 查询函数。
from product_agent.product_tools import query_product


def run_langchain_product_tool(
    product_id: str,
) -> dict[str, object]:
    """查询产品 CSV，并将成功或失败结果整理为统一工具返回结构。"""

    try:
        # 调用项目既有的 CSV 查询逻辑，避免重复实现产品数据访问。
        product_tool_data = query_product(product_id)

    # CSV 缺失、字段格式错误等异常需要作为工具结果返回给 Agent。
    except Exception as product_tool_error:
        return {
            "success": False,
            "error": str(product_tool_error),
        }

    # 正常查询时保留完整的业务数据，供后续字段筛选和评测使用。
    return {
        "success": True,
        "data": product_tool_data,
    }


@tool("query_product")
def query_product_tool(
    product_id: str,
) -> dict[str, object]:
    """根据产品编号查询本地 CSV 中的产品业务信息。"""

    # 将 LangChain Tool 的调用委托给统一的产品查询包装函数。
    return run_langchain_product_tool(product_id)


# 当前 Agent 仅向模型注册一个白名单工具，名称需与评测题库保持一致。
TRADE_LANGCHAIN_PRODUCT_TOOLS: list[BaseTool] = [
    query_product_tool,
]
