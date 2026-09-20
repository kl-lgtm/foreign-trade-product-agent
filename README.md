# 外贸产品业务 Agent

这是一个独立的结构化产品查询项目。大模型根据用户问题决定是否调用本地 CSV 产品数据库工具，再仅返回问题所需要的字段，并显示工具调用记录。

> `trade_data/structured_data/trade_products.csv` 中的产品、价格、库存和交期均为模拟测试数据，只用于个人学习项目，不代表真实企业。

## 主要能力

- 使用 OpenAI 兼容的大模型 API 进行工具调用决策。
- 基于本地 CSV 查询产品价格、库存、规格、起订量和交期。
- Agent 最多执行 3 个步骤，避免无止境的工具循环。
- 按问题字段范围作答；例如仅询问价格和库存时，不附带规格或交期。
- 显示工具调用过程，并用 SQLite 保存当前会话记录。
- 提供自动评测用例，覆盖工具选择、字段范围与异常结果处理。

## 项目结构

```text
foreign-trade-product-agent/
├─ agent_app.py               # Streamlit 网页入口
├─ product_agent/             # Agent、工具、评测与会话模块
├─ trade_data/
│  ├─ structured_data/        # 模拟产品 CSV
│  └─ evaluation/             # Agent 评测用例
├─ tests/                     # 自动化测试
├─ requirements.txt
└─ .env.example
```

运行产生的 SQLite 数据库和日志均位于本项目目录下，且被 `.gitignore` 忽略；本项目不包含上传文档、向量库或 RAG 功能。

## 安装与启动

在本项目目录打开 PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

在 `.env` 中填写自己的 `TRADE_AGENT_API_KEY` 后，运行：

```powershell
streamlit run agent_app.py
```

## LangChain 实现说明

正式运行链路使用 LangChain 的 `ChatOpenAI` 对接 OpenAI 兼容大模型 API，使用 `@tool` 将本地 CSV 产品查询封装为 `query_product` 工具。模型会根据问题决定是否调用工具，工具结果会按用户提问范围筛选后再生成回答，并保留完整工具调用记录供页面展示和评测。

项目保留原生 Function Calling 实现作为学习对照，但 Streamlit 页面与真实评测器默认使用 LangChain 服务。

## 测试与评测

```powershell
python -m unittest discover -s tests -v
python -m product_agent.agent_evaluator
```

本项目只处理结构化产品业务查询；PDF 或 Word 的知识库问答属于另一个独立的 RAG 系统项目。
