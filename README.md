# WC-Agent · 2026 世界杯比赛预测智能体

一个数据驱动的足球比赛预测 AI Agent：给定两支球队，自动并行收集**结构化战绩、最新首发/伤病、历史交锋、市场赔率**四维数据，交由大模型综合分析，给出**比分预测 + 胜平负概率**，并通过**赛后复盘闭环**用 Brier score 客观衡量"预测得比市场赔率准不准"。

> 定位：一个用于学习 Agent 架构与工程实践的完整项目。核心亮点不在"预测多准"（见[待改进](#待改进与已知局限)），而在于一套**可观测、可评估、可迭代**的 agent 系统骨架。

---

## 核心特性

- **确定性 pipeline 预测**：预测是"已知流程"，用代码固定编排（并行抓全维数据 → 单次推理），而非 ReAct 逐轮试探。2 次 LLM 调用完成，快且绝不漏数据。
- **四维数据融合**：球队硬数据（football-data）+ 时效软信息（Tavily）+ 历史交锋（本地 RAG）+ 市场赔率（The Odds API）。
- **RAG 历史知识库**：5 届世界杯（2006–2022）315 场比赛切片入向量库，**元数据过滤**精准召回两队交锋。
- **记忆系统**：短期会话（Redis）+ 长期用户画像（MySQL），支持多轮上下文与追问。
- **快慢模型分工**：轻任务（意图理解/抽取）走便宜快的非思考模型，重任务（预测）才用推理模型。
- **流式输出（SSE）**：状态进度 + 逐 token 回答，缓解推理模型的长延迟。
- **三态防污染**：预测前判定赛前/进行中/已结束——已结束的比赛直接返回真实比分、拒绝"假预测"，保护评估诚实性。
- **评估闭环**：预测入库 → 赛后自动查赛果 → 算 Brier / log-loss，并与**赔率隐含概率 baseline** 对比。
- **工程化**：统一异常体系（错误码）、结构化日志（loguru + request_id）、请求级统计（工具调用次数 + API 额度）。

---

## 技术栈

| 层 | 技术 |
|---|---|
| Web 框架 | FastAPI（异步）+ Uvicorn |
| LLM | DeepSeek（OpenAI 兼容接口，v4-pro 推理 / deepseek-chat 快模型）|
| 向量库 / Embedding | Chroma（嵌入式）+ bge-small-zh-v1.5（本地，512 维）|
| 短期记忆 | Redis（Docker）|
| 长期记忆 + 评估 | MySQL（Docker）|
| 外部数据 | football-data、Tavily、The Odds API |
| 其他 | httpx、Pydantic、loguru |

---

## 系统架构：一次预测请求的完整链路

```
POST /api/v1/dispatch(/stream)  { question, session_id, user_id }
  │
  ▼  [中间件] 生成 request_id、计时、日志
DispatchService.dispatch_stream
  ├─ 加载短期历史(Redis) + 长期画像(MySQL)
  ├─ interpret()  ← 一次「快模型」调用：判定意图(predict/chat) + 抽取两队
  │
  ├─ route = chat  → GeneralAgent（流式闲聊，带历史/画像）
  └─ route = predict →
        │  ① 三态判定 match_state()：已结束→返回真实比分(不预测/不入库)
        │                            进行中→临场分析(不入库)
        │                            赛前  →继续 ↓
        │  ② asyncio.gather 并行抓四维数据
        │       get_team_info · search_web · search_history(RAG) · get_match_odds
        │  ③ 单次「推理模型」调用 → 流式输出预测 + 结构化 JSON
        │  ④ 赛前预测入库(MySQL, pending)，供赛后评估
        ▼
  存回本轮对话(Redis) → 返回 answer + session_id
```

**关键设计**：Agent 不直接碰 OpenAI SDK，只调 `LLMClient`（分层解耦，换供应商只改一处）；工具是无状态的 `BaseTool` 子类，pipeline 里由代码固定调用，ReAct 兜底时由 LLM 自主调用。

---

## 数据存储（四类，各司其职）

| 存储 | 位置 | 存什么 |
|---|---|---|
| **Redis** | Docker | 短期会话历史（`session:*`，LIST + TTL 滑动窗口）|
| **MySQL** | Docker | `predictions`（预测评估）+ `user_profile`（长期画像）|
| **Chroma** | 嵌入式，`backend/data/chroma` | RAG 历史世界杯知识库（315 场向量）|
| 磁盘 | `D:/code/hf_cache` | bge 向量模型缓存 |

---

## 目录结构

```
backend/app/
  api/v1/        HTTP 端点（dispatch / eval）
  core/
    agents/      predictor（预测）/ general（兜底闲聊）/ base_agent
    tools/       team_info · web_search · odds · rag_search
    rag/         parser · splitter · embedder · retriever
    eval/        metrics · repo · resolver · fixtures · pending
    interpreter  意图理解+抽取（快模型）
    router       意图 → agent 派发
    memory/      short_term(Redis) · long_term(MySQL)
  db/            redis_client · mysql_client · vector_store(Chroma)
  utils/         client(LLM) · exceptions · logger · request_stats · teammatch
  config/        settings · agent_config
  scripts/       build_index(建向量库) · check_infra(连通性自检)
doc_rag/         5 届世界杯 .docx 战报（RAG 语料）
docker-compose.yml   Redis + MySQL
```

---

## 快速开始

```bash
# 1. 起依赖（Redis + MySQL）
docker compose up -d

# 2. 配置密钥
cp backend/.env.example backend/.env   # 填入你的各 API key

# 3. 装依赖（torch 装 CPU 版）
cd backend
python -m pip install -r requirements.txt
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu

# 4. 建 RAG 向量库（一次性，把 doc_rag 灌进 Chroma）
python scripts/build_index.py

# 5. 连通性自检（可选）
python scripts/check_infra.py

# 6. 启动服务（注意在 backend 目录下）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# 打开 http://localhost:8000/docs 交互调试
```

---

## 主要 API

| 端点 | 说明 |
|---|---|
| `POST /api/v1/dispatch` | 统一入口（非流式），返回完整回答 |
| `POST /api/v1/dispatch/stream` | 流式入口（SSE），推送 status/token/done |
| `GET /api/v1/eval` | 评估报告：你的平均 Brier vs 赔率 Brier |
| `GET /api/v1/eval/details` | 每场明细：预测/概率/实际/各自 Brier |
| `POST /api/v1/eval/resolve` | 手动触发结算（查赛果、算分）|
| `GET /health` | 健康检查 |

请求体示例：`{ "question": "预测西班牙vs葡萄牙", "user_id": "u1" }`（首次不带 session_id，响应会返回一个供后续追问复用）。

---

## 评估闭环（本项目的灵魂）

1. **预测时**：把你的胜平负概率 + 赔率隐含概率 + 开赛时间一起入库（`pending`）。
2. **赛后**：定时任务（+ 启动补扫）查 football-data 终场比分，对你的概率和赔率概率各算一次 **Brier score**（越低越准）。
3. **对比**：`GET /eval` 看你平均 Brier 有没有打赢赔率 baseline。

> 评估只收录**赛前**预测（已结束/进行中的预测不入库），保证是诚实的"事前预测"，不被上帝视角污染。

---

## 待改进与已知局限

坦诚记录（很多是有意识的取舍，非疏漏）：

- **预测水平 ≈ 复述市场**：实测中 agent 概率基本贴着赔率走，未能稳定打赢市场 baseline。博彩市场高度有效，概率上极难超越——本系统的价值更在"解释/情景分析"这类市场给不了的维度，而非绝对准度。
- **样本太少不足以定论**：Brier 需累积数十场才有统计意义，当前样本 < 5。
- **没有自动"学习"机制**：评估闭环是"测量仪"，不是"进步器"。改进目前靠人工迭代 prompt/数据，尚未做概率校准或经验记忆。
- **零自动化测试**：缺 pytest 测试套件，重构缺安全网（首要工程债）。
- **无缓存 / 限流**：相同请求重复烧 LLM 与 API 额度；无 per-user 限流。
- **一致性小瑕疵**：pipeline 的 `_call_tool` 对 `ConfigError` 也做了降级（与 ReAct 路径不完全一致）。
- **RAG 语料有限**：仅 2006–2022；历史交锋对预测的实际增益有限。"赛后结果自动入库"扩充语料尚未做。
- **延迟**：单次预测约 25–50s（推理模型 + 多源抓取），已用流式缓解，但绝对耗时仍高。

### 路线图
- [ ] 赛后真实结果自动写入 RAG 向量库（持续扩充语料）
- [ ] 概率校准（Platt/isotonic），用累积评估数据自我修正
- [ ] pytest 测试套件 + CI
- [ ] 相同比赛结果缓存（Redis）+ 请求限流
- [ ] 前端界面

---

## 许可

个人学习项目。外部数据 API 各遵循其自身服务条款。
