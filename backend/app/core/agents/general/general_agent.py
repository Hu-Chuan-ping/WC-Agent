from app.config.agent_config import AgentConfig
from app.core.agents.base_agent import BaseAgent
from app.core.agents.general.prompts import SYSTEM_PROMPT

GENERAL_CONFIG = AgentConfig(
    temperature=0.7,   # 闲聊允许更自然、灵活
    # 推理模型的思考也吃 max_tokens，1024 太小可能把正文挤空，给 2048 更稳
    max_tokens=2048,
    max_iterations=1,  # 无工具，单轮即出结果，无需 ReAct 循环
)


class GeneralAgent(BaseAgent):
    name = "general"
    description = "通用闲聊与兜底对话，处理打招呼、开放性问题及意图不明确的请求"

    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, config=GENERAL_CONFIG)
        # 不注册任何工具：纯对话
