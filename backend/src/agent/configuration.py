import os
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field


class Configuration(BaseModel):
    summary_model: str = Field(default="deepseek-chat")
    qa_model: str = Field(default="deepseek-chat")
    summary_language: str = Field(default="zh")
    max_sections: int = Field(default=10)
    summary_dir: str = Field(default="./data/summary")
    note_dir: str = Field(default="./data/note")

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        # 兼容 LangGraph 的运行时配置和环境变量
        configurable = config["configurable"] if config and "configurable" in config else {}
        raw_values: dict[str, Any] = {
            name: os.environ.get(name.upper(), configurable.get(name))
            for name in cls.model_fields.keys()
        }
        values = {k: v for k, v in raw_values.items() if v is not None}
        return cls(**values)
