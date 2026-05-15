from typing import List

from pydantic import BaseModel, Field


class SectionSummary(BaseModel):
    section_title: str = Field(description="The section title.")
    key_points: List[str] = Field(description="Key points extracted from the section.")
    summary_text: str = Field(description="A concise paragraph summary of the section.")
    citations: List[str] = Field(description="Page-based citations like (p.3) or (p.5-7).")


class ReflectionResult(BaseModel):
    is_complete: bool = Field(description="Whether the summary covers the important content.")
    missing_aspects: str = Field(description="What is still missing or under-covered.")
    follow_up_sections: List[str] = Field(description="Sections that should be summarized next.")


class QAPlan(BaseModel):
    """《调研/答题计划》：QA Planner 的结构化输出。"""

    plan_text: str = Field(description="对完整答题计划的自然语言陈述，使用 Markdown 列表形式。")
    research_steps: List[str] = Field(description="为了回答问题需要在文档中查证的关键调研步骤。")
    expected_evidence: List[str] = Field(description="预计需要引用的页码段或证据描述。")
    success_criteria: List[str] = Field(description="判定答案达标的具体标准（覆盖度、准确度等）。")


class QADraft(BaseModel):
    """QA Drafter 的结构化输出，包含答案与证据。"""

    answer: str = Field(description="问题的最终回答，使用 Markdown 排版。")
    citations: List[str] = Field(description="所引用的页码标记，如 p.3 或 p.5-7。")
    confidence: str = Field(description="信心等级，取值 high / medium / low。")


class QACriticResult(BaseModel):
    """QA Critic 的结构化输出。"""

    is_acceptable: bool = Field(description="草稿是否已达标，可直接交付用户。")
    critique: str = Field(description="对草稿质量的总体评价。")
    issues: List[str] = Field(description="待解决的问题清单（幻觉、冗余、未覆盖计划项等）。")
    rewrite_instructions: str = Field(description="若需重写，给 Drafter 的具体修改指令。")


class NotePlan(BaseModel):
    """笔记规划：圈定需要记录的核心要素。"""

    plan_text: str = Field(description="笔记的整体规划与组织思路。")
    core_entities: List[str] = Field(description="必须记录的核心实体、术语或方法名。")
    must_record: List[str] = Field(description="必须保留的结论、数据或论点。")
    suggested_tags: List[str] = Field(description="建议的核心标签，用于检索归档。")


class NoteCriticResult(BaseModel):
    """笔记评审结果。"""

    is_acceptable: bool = Field(description="笔记是否已达到全面性 + 精简性双重标准。")
    coverage_issues: List[str] = Field(description="全面性方面的缺漏。")
    style_issues: List[str] = Field(description="精简性 / 去口语化方面的问题。")
    rewrite_instructions: str = Field(description="若不达标，给 Drafter 的修改指令。")
