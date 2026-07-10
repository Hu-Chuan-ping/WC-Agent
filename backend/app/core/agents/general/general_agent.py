from app.config.agent_config import AgentConfig
from app.config.settings import settings
from app.core.agents.base_agent import BaseAgent
from app.core.agents.general.prompts import SYSTEM_PROMPT
from app.core.tools.my_predictions import MyPredictionsTool
from app.core.tools.rag_search import RagSearchTool
from app.core.tools.web_search import WebSearchTool

GENERAL_CONFIG = AgentConfig(
    # 追问要做工具 ReAct：换非推理的快模型，更快更省、流式更干净（不需深度推理）。
    model=settings.fast_model,
    temperature=0.7,
    max_tokens=2048,
    max_iterations=4,  # 允许"检索→再答"的工具循环
)


class GeneralAgent(BaseAgent):
    name = "general"
    description = "通用对话与追问：闲聊、开放性问题，以及对已聊过比赛的追问（可检索）"

    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, config=GENERAL_CONFIG)
        # 挂检索类工具：让追问能查到事实，而不是空对空。
        self.register_tool(WebSearchTool())       # search_web：时效新闻/伤病/争议判罚
        self.register_tool(RagSearchTool())        # search_history：历史世界杯交锋
        self.register_tool(MyPredictionsTool())    # get_my_predictions：自己的预测+赛果
