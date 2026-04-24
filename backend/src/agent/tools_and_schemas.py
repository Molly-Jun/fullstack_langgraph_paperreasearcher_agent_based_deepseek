from typing import List

from pydantic import BaseModel, Field


class SectionSummary(BaseModel):
    # 单个章节的摘要结果
    section_title: str = Field(description="The section title.")
    key_points: List[str] = Field(description="Key points extracted from the section.")
    summary_text: str = Field(description="A concise paragraph summary of the section.")
    citations: List[str] = Field(description="Page-based citations like (p.3) or (p.5-7).")


class ReflectionResult(BaseModel):
    # 反思节点的结构化输出
    is_complete: bool = Field(description="Whether the summary covers the important content.")
    missing_aspects: str = Field(description="What is still missing or under-covered.")
    follow_up_sections: List[str] = Field(description="Sections that should be summarized next.")


class QAResponse(BaseModel):
    # 问答节点的结构化输出
    answer: str = Field(description="The answer to the user's question.")
    citations: List[str] = Field(description="Page-based citations used in the answer.")
    confidence: str = Field(description="Answer confidence level.")
