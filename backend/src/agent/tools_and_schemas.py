from typing import List

from pydantic import BaseModel, Field


class SectionSummary(BaseModel):
    """单个章节摘要：含关键概念/实体，引用使用'章节名 - 段落前两词'格式。"""

    section_title: str = Field(description="The section title.")
    key_points: List[str] = Field(description="Key points extracted from the section.")
    key_entities: List[str] = Field(
        description="该章节涉及的关键概念 / 术语 / 方法名 / 数据集 / 指标等核心实体，3-6 个。"
    )
    summary_text: str = Field(description="A concise paragraph summary of the section.")
    citations: List[str] = Field(
        description=(
            "本段陈述所对应的引用锚点。每条引用使用格式：'<章节名> - <段落前两个个英文/中文 token>'，"
            "例如 'Method - We propose' 或 '方法 - 本文'。"
            "若无法定位到具体段落，仅写章节名亦可。"
        )
    )


class ReflectionResult(BaseModel):
    is_complete: bool = Field(description="Whether the summary covers the important content.")
    missing_aspects: str = Field(description="What is still missing or under-covered.")
    follow_up_sections: List[str] = Field(description="Sections that should be summarized next.")


class QAPlan(BaseModel):
    """《调研/答题计划》：QA Planner 的结构化输出。需要兼顾用户可读性与专业性。"""

    plan_text: str = Field(
        description=(
            "面向用户阅读的简明计划，使用 Markdown 列表呈现，控制在 4-6 条要点之内，"
            "每条不超过 30 字，避免过度冗长。可包含：拆解的子问题、要在论文中查证的关键点。"
        )
    )
    research_steps: List[str] = Field(
        description="为了回答问题需要执行的调研步骤，简短关键词式陈述，3-5 条即可。"
    )


class QADraft(BaseModel):
    """QA Drafter 的结构化输出，包含答案与证据。"""

    answer: str = Field(description="问题的最终回答，使用 Markdown 排版。")
    citations: List[str] = Field(
        description=(
            "所引用的章节锚点，格式：'<章节名> - <段落前两词>'。"
            "若无法精确到段落，可仅写章节名。"
        )
    )
    confidence: str = Field(description="信心等级，取值 high / medium / low。")


class QACriticResult(BaseModel):
    """QA Critic 的结构化输出。"""

    is_acceptable: bool = Field(description="草稿是否已达标，可直接交付用户。")
    critique: str = Field(description="对草稿质量的总体评价。")
    issues: List[str] = Field(description="待解决的问题清单（幻觉、冗余、未覆盖计划项等）。")
    rewrite_instructions: str = Field(description="若需重写，给 Drafter 的具体修改指令。")


class NotePlan(BaseModel):
    """笔记规划：聚焦最近问答对话，论文仅作背景。"""

    plan_text: str = Field(
        description="围绕本次问答对话的笔记组织思路，简短陈述要保留哪些问题与结论，若有关键词，则更侧重于关键词相关的问答内容。"
    )
    must_record_qa: List[str] = Field(
        description="必须落到笔记的问答要点,（'问题: ... → 结论: ...' 形式），若有关键词，则更侧重于关键词相关的问答内容。"
    )
    one_line_summary: str = Field(
        description="对论文内容的一句话总结，不超过 30 字，用于 frontmatter。"
    )


class NoteCriticResult(BaseModel):
    """笔记评审结果。"""

    is_acceptable: bool = Field(description="笔记是否达到全面性 + 精简性双重标准。")
    coverage_issues: List[str] = Field(description="问答要点遗漏。")
    style_issues: List[str] = Field(description="冗长 / 口语化 / 跑题（写论文而非写问答）等问题。")
    rewrite_instructions: str = Field(description="若不达标，给 Drafter 的修改指令。")
