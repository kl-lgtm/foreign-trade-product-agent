# LangChain 产品业务 Agent 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将外贸产品业务 Agent 的正式模型与工具调用链迁移到 LangChain，并保留现有 CSV、会话、日志和评测能力。

**Architecture:** 新建 LangChain 服务模块，以 `ChatOpenAI`、`@tool` 和 LangChain 消息对象完成最多三轮的工具调用循环。现有 `product_tools.py` 继续作为唯一产品数据访问层，字段范围筛选继续复用现有业务规则；页面和评测器改用新服务。

**Tech Stack:** Python 3.12、Streamlit 1.64、LangChain、langchain-openai、OpenAI 兼容 API、CSV、SQLite、unittest。

**Spec:** `docs/superpowers/specs/2026-09-20-langchain-product-agent-design.md`

## Global Constraints

- 产品数据只能从 `trade_data/structured_data/trade_products.csv` 读取，禁止在提示词或代码中硬编码价格、库存等事实数据。
- API Key 只能从本地 `.env` 读取，禁止打印、记录或提交密钥。
- 具体产品信息问题必须调用名称为 `query_product` 的工具；普通外贸概念问题不应调用该工具。
- Agent 工具循环最多执行 3 步，工具调用记录必须保持 `step`、`tool_name`、`arguments`、`result` 字段。
- 仅向模型回传用户明确询问的产品字段；用户要求详情时才回传完整字段。
- 保持现有 Streamlit 聊天入口、SQLite 会话恢复、日志和评测 JSON 报告功能。

## Review Focus

- API Key 缺失时，服务应抛出清晰配置错误，且异常信息不得包含密钥。
- 模型请求不存在的产品编号时，工具事件应保存 `found: false`，最终回答不得编造库存。
- 模型返回非字典工具参数时，服务应将参数解析错误作为工具结果处理，不应使页面崩溃。
- 价格与库存问题的工具结果不得泄露规格、起订量和交期字段。
- 连续三轮仍要求工具调用时，服务应中止并给出明确的步数限制错误。

---

### Task 1: LangChain 依赖与产品查询 Tool

**Files:**
- Modify: `requirements.txt`
- Create: `product_agent/langchain_product_agent_service.py`
- Create: `tests/test_langchain_product_agent_service.py`

**Interfaces:**
- Consumes: `product_agent.product_tools.query_product(product_id: str) -> dict[str, object]`。
- Produces: `TRADE_LANGCHAIN_PRODUCT_TOOLS: list[BaseTool]`，其中唯一工具名称为 `query_product`；`run_langchain_product_tool(product_id: str) -> dict[str, object]`，返回 `{"success": bool, "data": dict}` 或 `{"success": false, "error": str}`。
- Used by: Task 2 的 Agent 循环与 Task 3 的页面、评测器。

- [ ] **Step 1: 写入失败测试，验证 Tool 名称和真实 CSV 数据查询**

```python
from product_agent.langchain_product_agent_service import (
    TRADE_LANGCHAIN_PRODUCT_TOOLS,
    run_langchain_product_tool,
)

def test_langchain_product_tool_uses_project_csv(self) -> None:
    product_tool_names = {
        product_tool.name
        for product_tool in TRADE_LANGCHAIN_PRODUCT_TOOLS
    }
    product_tool_result = run_langchain_product_tool("A001")

    self.assertEqual(product_tool_names, {"query_product"})
    self.assertTrue(product_tool_result["success"])
    self.assertTrue(product_tool_result["data"]["found"])
    self.assertEqual(product_tool_result["data"]["unit_price_usd"], 8.5)
```

- [ ] **Step 2: 运行测试，确认其因模块不存在而失败**

Run: `python -m unittest tests.test_langchain_product_agent_service.LangChainProductAgentServiceTest.test_langchain_product_tool_uses_project_csv -v`

Expected: `ModuleNotFoundError: No module named 'product_agent.langchain_product_agent_service'`。

- [ ] **Step 3: 安装并声明 LangChain 依赖，创建最小 Tool 封装**

在 `requirements.txt` 新增：

```text
langchain
langchain-openai
```

在新服务模块中实现：

```python
from langchain_core.tools import tool
from product_agent.product_tools import query_product

@tool("query_product")
def query_product_tool(product_id: str) -> dict[str, object]:
    """根据产品编号查询本地 CSV 中的产品业务信息。"""
    return run_langchain_product_tool(product_id)

def run_langchain_product_tool(product_id: str) -> dict[str, object]:
    try:
        return {"success": True, "data": query_product(product_id)}
    except Exception as product_tool_error:
        return {"success": False, "error": str(product_tool_error)}

TRADE_LANGCHAIN_PRODUCT_TOOLS = [query_product_tool]
```

- [ ] **Step 4: 安装依赖并运行专项测试，确认通过**

Run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest tests.test_langchain_product_agent_service.LangChainProductAgentServiceTest.test_langchain_product_tool_uses_project_csv -v
```

Expected: 测试通过，A001 价格为 `8.5`。

- [ ] **Step 5: 提交独立的 Tool 改造**

```powershell
git add requirements.txt product_agent/langchain_product_agent_service.py tests/test_langchain_product_agent_service.py
git commit -m "feat: 添加 LangChain 产品查询工具"
```

### Task 2: LangChain Agent 循环与字段范围控制

**Files:**
- Modify: `product_agent/langchain_product_agent_service.py`
- Modify: `tests/test_langchain_product_agent_service.py`

**Interfaces:**
- Consumes: `TRADE_LANGCHAIN_PRODUCT_TOOLS`、`run_langchain_product_tool()` 和 `select_product_fields_for_answer()`。
- Produces: `run_langchain_product_agent(product_user_question: str, product_max_steps: int = 3) -> dict[str, object]`，返回 `{"answer": str, "tool_events": list[dict[str, object]]}`。
- Used by: Task 3 的 Streamlit 页面和真实评测器。

- [ ] **Step 1: 写入失败测试，验证字段筛选与工具事件结构**

```python
from product_agent.langchain_product_agent_service import (
    select_langchain_product_fields,
)

def test_price_and_stock_tool_result_hides_unrequested_fields(self) -> None:
    product_result = run_langchain_product_tool("A001")
    product_selected_result = select_langchain_product_fields(
        product_tool_result=product_result,
        product_user_question="查询 A001 价格和库存",
    )

    product_data = product_selected_result["data"]
    self.assertIn("unit_price_usd", product_data)
    self.assertIn("stock_square_meters", product_data)
    self.assertNotIn("size_mm", product_data)
    self.assertNotIn("min_order_square_meters", product_data)
    self.assertNotIn("lead_time_days", product_data)
```

- [ ] **Step 2: 运行测试，确认其因字段筛选函数不存在而失败**

Run: `python -m unittest tests.test_langchain_product_agent_service.LangChainProductAgentServiceTest.test_price_and_stock_tool_result_hides_unrequested_fields -v`

Expected: `ImportError`，提示 `select_langchain_product_fields` 尚未定义。

- [ ] **Step 3: 实现 `ChatOpenAI` 工具循环和字段筛选适配器**

复用现有 `select_product_fields_for_answer()`，避免两套字段判断规则：

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from product_agent.product_agent_service import select_product_fields_for_answer

def select_langchain_product_fields(
    product_tool_result: dict[str, object],
    product_user_question: str,
) -> dict[str, object]:
    return select_product_fields_for_answer(
        product_tool_result,
        product_user_question,
    )

def run_langchain_product_agent(
    product_user_question: str,
    product_max_steps: int = 3,
) -> dict[str, object]:
    product_model = ChatOpenAI(
        model=os.getenv("TRADE_AGENT_MODEL", "deepseek-v4-flash"),
        api_key=os.getenv("TRADE_AGENT_API_KEY"),
        base_url=os.getenv("TRADE_AGENT_BASE_URL"),
        temperature=0,
    )
    product_bound_model = product_model.bind_tools(
        TRADE_LANGCHAIN_PRODUCT_TOOLS,
    )
    # 使用 SystemMessage、HumanMessage 和 ToolMessage 完成最多三轮循环。
```

工具事件中的 `result` 必须保存字段筛选前的嵌套业务结果，确保评测器能读取
`result.data.found`；回传给模型的 `ToolMessage` 使用字段筛选后的 JSON。

- [ ] **Step 4: 运行两个专项测试，确认 Tool 与字段范围均通过**

Run: `python -m unittest tests.test_langchain_product_agent_service -v`

Expected: 两项测试通过。

- [ ] **Step 5: 提交 Agent 编排逻辑**

```powershell
git add product_agent/langchain_product_agent_service.py tests/test_langchain_product_agent_service.py
git commit -m "feat: 实现 LangChain 产品业务 Agent"
```

### Task 3: 接入页面、评测器和说明文档

**Files:**
- Modify: `agent_app.py`
- Modify: `product_agent/agent_evaluator.py`
- Modify: `tests/test_agent_app_ui.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `run_langchain_product_agent()`。
- Produces: Streamlit 页面和 `python -m product_agent.agent_evaluator` 均使用 LangChain 正式链路。

- [ ] **Step 1: 写入失败测试，验证页面和评测器导入 LangChain 服务**

```python
def test_agent_page_uses_langchain_service(self) -> None:
    product_agent_app_source = Path("agent_app.py").read_text(encoding="utf-8")
    self.assertIn(
        "from product_agent.langchain_product_agent_service import (",
        product_agent_app_source,
    )
    self.assertIn("run_langchain_product_agent", product_agent_app_source)
```

- [ ] **Step 2: 运行测试，确认页面尚未接入 LangChain 服务而失败**

Run: `python -m unittest tests.test_agent_app_ui.ProductAgentAppUiTest.test_agent_page_uses_langchain_service -v`

Expected: `AssertionError`，因为页面仍导入 `run_product_agent`。

- [ ] **Step 3: 将正式调用入口替换为 LangChain 服务并更新 README**

在 `agent_app.py` 和 `agent_evaluator.py` 中使用：

```python
from product_agent.langchain_product_agent_service import (
    run_langchain_product_agent,
)
```

并将原调用替换为：

```python
agent_result = run_langchain_product_agent(agent_question)
```

在 README 的技术栈与主要能力中明确说明：项目使用 LangChain `ChatOpenAI` 和
`@tool` 封装 CSV 查询工具；保留原生实现只用于学习对照，不作为正式页面链路。

- [ ] **Step 4: 运行页面专项测试和完整自动测试**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_agent_app_ui -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: 页面专项测试和完整测试集全部通过。

- [ ] **Step 5: 提交运行链路与文档更新**

```powershell
git add agent_app.py product_agent/agent_evaluator.py tests/test_agent_app_ui.py README.md
git commit -m "feat: 接入 LangChain Agent 运行链路"
```

### Task 4: 真实评测、浏览器联调与发布

**Files:**
- Modify: `README.md`（仅在验证命令或结果说明需要更正时）
- Verify: `trade_data/evaluation/agent_evaluation_report.json`（忽略文件，不提交）

**Interfaces:**
- Consumes: Task 3 已接入 LangChain 的页面和评测器。
- Produces: 通过验证的 GitHub 提交与可演示本地页面。

- [ ] **Step 1: 执行真实模型评测**

Run: `.\.venv\Scripts\python.exe -m product_agent.agent_evaluator`

Expected: 4 条用例全部 `PASS`，通过率为 `100.0%`。

- [ ] **Step 2: 检查运行期文件未被暂存**

Run:

```powershell
git status --short
git check-ignore -v .env trade_data\database\product_agent.db trade_logs\product_agent.log trade_data\evaluation\agent_evaluation_report.json
```

Expected: 运行期文件由 `.gitignore` 忽略，待提交文件不包含 API Key、SQLite、日志或评测报告。

- [ ] **Step 3: 启动或刷新 Streamlit 页面进行人工联调**

Run: `.\.venv\Scripts\python.exe -m streamlit run agent_app.py --server.port 8501`

Manual checks:

1. 输入“查询 A001 价格和库存”，确认回答只有价格和库存，展开工具记录可见 `query_product` 与 `A001`。
2. 输入“A002 的最小起订量和交期是多少”，确认回答为 800 平方米、20 天。
3. 输入“A999 当前有多少库存”，确认回答明确说明不存在，且工具记录显示 `found: false`。

- [ ] **Step 4: 提交验证后说明并推送**

```powershell
git status --short
git push
```

Expected: 工作区干净，`main` 成功推送至 `origin/main`。

## 自检结果

- 设计中的 LangChain 运行入口、唯一 CSV 数据源、字段范围控制、错误处理、工具步数限制、日志和会话兼容性，均分别由 Task 1 至 Task 4 覆盖。
- 计划没有未完成或模糊的实施占位；每项生产代码变更前均有明确的失败测试与命令。
- 所有跨任务接口均使用 `run_langchain_product_tool()`、`select_langchain_product_fields()`、`run_langchain_product_agent()` 三个固定名称。
