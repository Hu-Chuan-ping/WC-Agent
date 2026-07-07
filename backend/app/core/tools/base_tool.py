from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    所有工具的抽象基类。

    子类必须定义类属性 name、description，
    并实现 run() 和 _input_schema()。
    """

    name: str
    description: str

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """执行工具逻辑，返回可转为字符串的结果。

        统一声明为协程：纯内存工具直接同步计算即可（async 不会带来开销），
        网络/IO 类工具（如 Wikipedia 查询）则可在内部 await，二者接口一致。
        """
        ...

    @abstractmethod
    def _input_schema(self) -> dict:
        """返回符合 JSON Schema 的输入参数定义。"""
        ...

    def to_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self._input_schema(),
        }
