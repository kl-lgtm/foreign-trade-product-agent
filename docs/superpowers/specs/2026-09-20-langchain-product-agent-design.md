# LangChain 产品业务 Agent 设计说明

## 目标

在不改变现有产品 CSV、会话持久化、日志、字段范围控制和评测能力的前提下，
让外贸产品业务 Agent 的正式运行链路使用 LangChain。完成后，项目能够真实演示
`ChatOpenAI`、LangChain Tool 和多轮工具调用，而不是仅在文档中声明使用了 LangChain。

## 范围

本次只改造产品业务 Agent 的模型与工具调用编排层，不新增产品数据、用户权限、
多 Agent 协作或网页交互模式。页面仍保持单一聊天入口和工具调用记录展示。

## 架构

新增 `product_agent/langchain_product_agent_service.py` 作为正式 Agent 服务：

- `ChatOpenAI` 读取现有 `.env` 的 API Key、Base URL 和模型名，对接 OpenAI 兼容模型服务。
- 使用 LangChain `@tool` 将产品查询封装为 `query_product` 工具。
- 该工具只调用已有的 `product_tools.query_product()`；产品 CSV 仍是唯一事实来源。
- 服务层沿用已有字段筛选规则，仅将用户明确询问的字段交给模型生成最终回答。
- 每次工具调用输出与现有页面兼容的 `tool_events`，包含步骤、工具名、参数和结果。

保留 `product_agent/product_agent_service.py` 作为原生 Function Calling 的历史实现，
不作为 Streamlit 页面或真实评测的默认运行链路。

## 执行流程

```text
用户问题
  → ChatOpenAI.bind_tools([query_product])
  → 模型决定直接回答或请求工具
  → LangChain Tool 查询本地 CSV
  → 按问题筛选产品字段
  → ToolMessage 回传模型
  → 最终回答和工具调用记录
```

对于价格、库存、规格、起订量和交期等具体产品问题，系统提示词要求模型调用
`query_product`，不得凭记忆编造。普通外贸概念问题可以直接回答。

## 异常处理与安全

- API Key 缺失或 API 连接失败时向页面返回明确错误，但不输出密钥。
- 模型返回无效工具参数或未知工具时，将错误作为工具结果回传，并由最终回答说明。
- CSV 不存在或格式错误时，工具结果保留具体原因，方便排查。
- 查询不存在的产品时，工具必须返回 `found: false`；最终回答明确说明不存在。
- 工具调用次数最多为 3 步，避免无限循环。

## 测试与验收

新增或调整测试以验证：

1. LangChain 工具已注册为 `query_product`，并使用真实项目 CSV 查询 A001。
2. 价格和库存问题的工具结果不会包含未请求的规格、起订量和交期。
3. 工具调用记录包含评测器所需的工具名、`product_id` 参数和嵌套 `found` 结果。
4. Streamlit 页面和真实评测器均调用 LangChain 服务。

验收命令：

```powershell
python -m unittest discover -s tests -v
python -m product_agent.agent_evaluator
streamlit run agent_app.py
```

通过标准：全部自动测试通过、4 条真实 Agent 评测全部通过，且浏览器中可查看
LangChain 工具调用记录。
