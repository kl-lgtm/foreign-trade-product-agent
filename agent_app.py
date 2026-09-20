"""外贸产品业务 Agent 的 Streamlit 网页入口。"""

from time import perf_counter
from uuid import UUID, uuid4

import streamlit as st

from product_agent.agent_chat_repository import (
    clear_product_chat_messages,
    initialize_product_chat_database,
    load_product_chat_messages,
    save_product_chat_message,
)
from product_agent.agent_logging_service import (
    record_product_error,
    record_product_event,
)
from product_agent.langchain_product_agent_service import (
    run_langchain_product_agent,
)


# 页面配置必须最先执行。
st.set_page_config(
    page_title="外贸产品业务 Agent",
    page_icon=":material/smart_toy:",
    layout="centered",
)

# Agent 项目只有一个保存到 SQLite 的固定模式。
PRODUCT_AGENT_MODE = "产品业务Agent"


def get_or_create_agent_conversation_id() -> str:
    """从 URL 恢复会话编号，不存在时生成新的 UUID。"""

    agent_url_value = st.query_params.get("conversation")
    if isinstance(agent_url_value, list):
        agent_url_value = agent_url_value[0] if agent_url_value else None
    try:
        return UUID(str(agent_url_value)).hex
    except (ValueError, TypeError, AttributeError):
        agent_conversation_id = uuid4().hex
        st.query_params["conversation"] = agent_conversation_id
        return agent_conversation_id


def display_agent_tool_events(
    agent_tool_events: list[dict[str, object]],
) -> None:
    """折叠展示 Agent 实际执行过的 CSV 工具调用。"""

    if not agent_tool_events:
        return
    with st.expander("查看 Agent 工具调用记录", expanded=False):
        for agent_tool_event in agent_tool_events:
            with st.container(border=True):
                st.subheader(
                    f"步骤 {agent_tool_event['step']} · "
                    f"{agent_tool_event['tool_name']}"
                )
                st.write("工具参数")
                st.json(agent_tool_event["arguments"])
                st.write("工具结果")
                st.json(agent_tool_event["result"])


# 首次启动仅初始化这个项目自己的空会话数据库。
initialize_product_chat_database()
agent_conversation_id = get_or_create_agent_conversation_id()

st.title("外贸产品业务 Agent")
st.caption("Foreign Trade Product Business Agent")
st.info(
    "用于查询模拟产品 CSV 中的价格、库存、规格、起订量和交期。"
    "模型会自主决定是否调用产品查询工具，最多执行三步。"
)
st.sidebar.header("产品业务会话")
st.sidebar.caption(f"当前会话：{agent_conversation_id[:8]} · 刷新可恢复")
st.sidebar.caption("所有产品数据均为模拟测试数据，不代表真实企业。")

# 读取当前 URL 会话的历史消息，网页没有文件上传或 RAG 功能。
agent_chat_messages = load_product_chat_messages(
    product_conversation_id=agent_conversation_id,
    product_mode=PRODUCT_AGENT_MODE,
)
for agent_chat_message in agent_chat_messages:
    with st.chat_message(agent_chat_message["role"]):
        st.write(agent_chat_message["content"])
        if agent_chat_message["role"] == "assistant":
            display_agent_tool_events(
                list(agent_chat_message["debug"].get("tool_events", []))
            )

# 清空只删除当前 Agent 会话的聊天消息，不影响 CSV 文件。
if st.sidebar.button(
    "清空当前会话",
    icon=":material/delete_sweep:",
    width="stretch",
    key="agent_clear_chat",
):
    clear_product_chat_messages(
        product_conversation_id=agent_conversation_id,
        product_mode=PRODUCT_AGENT_MODE,
    )
    st.rerun()

# 用户提交的问题会先保存，再运行有上限的工具调用循环。
agent_question = st.chat_input(
    "询问产品数据库，例如：查询 A001 价格和库存",
    key="agent_question_input",
)
if agent_question:
    save_product_chat_message(
        product_conversation_id=agent_conversation_id,
        product_mode=PRODUCT_AGENT_MODE,
        product_role="user",
        product_content=agent_question,
    )
    with st.chat_message("user"):
        st.write(agent_question)

    with st.chat_message("assistant"):
        try:
            agent_started_at = perf_counter()
            with st.status("Agent 正在分析并调用工具", expanded=False) as status:
                agent_result = run_langchain_product_agent(agent_question)
                status.update(label="Agent 回答完成", state="complete")
            agent_answer = str(agent_result["answer"])
            agent_debug_data = {"tool_events": agent_result["tool_events"]}
            st.write(agent_answer)
            display_agent_tool_events(list(agent_result["tool_events"]))
            record_product_event(
                "agent_answer",
                "success",
                {
                    "conversation_id": agent_conversation_id,
                    "duration_ms": round((perf_counter() - agent_started_at) * 1000),
                },
            )
            agent_is_error = False
        except Exception as agent_error:
            agent_answer = f"产品业务问答失败：{agent_error}"
            agent_debug_data = {"tool_events": []}
            agent_is_error = True
            st.error(agent_answer)
            record_product_error(
                "agent_answer",
                agent_error,
                {"conversation_id": agent_conversation_id},
            )

    save_product_chat_message(
        product_conversation_id=agent_conversation_id,
        product_mode=PRODUCT_AGENT_MODE,
        product_role="assistant",
        product_content=agent_answer,
        product_debug_data=agent_debug_data,
        product_is_error=agent_is_error,
    )
