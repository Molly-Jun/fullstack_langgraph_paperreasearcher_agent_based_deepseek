from datetime import datetime


def get_current_date():
    return datetime.now().strftime("%B %d, %Y")


# =====================================================================
# Summary 链路（特性一：基于 Markdown 章节切块的并行摘要）
# =====================================================================

section_summarizer_instructions = """You are a professional academic paper analyst.
Summarize the following paper section in {language}.

Requirements:
- Extract 3 to 5 key points
- Keep the summary faithful to the source text
- Include page-based citations in the form (p.X) or (p.X-Y)
- Return only information supported by the section text
- Keep the section summary concise, around 80-150 words total

Section title: {section_title}
Page range: {page_range}

Section text:
{section_text}
"""

summary_prompts = {
    "summary": "请生成结构清晰、带页码引用的标准摘要。整体摘要请控制在800字以内，突出最核心内容。",
    "detailed_summary": "请生成较详细但仍然简洁的摘要，覆盖关键信息并带页码引用。整体摘要请控制在1200字以内。",
    "concise_summary": "请生成简洁摘要，只保留最核心的信息，并带页码引用。整体摘要请控制在500字以内。",
}


summary_reflection_instructions = """You are checking whether a paper summary is complete.

Requirements:
- Identify what important content is still missing
- If the current summary is sufficient, mark it complete
- Return a concise reflection that helps decide whether more sections need summarizing
- Keep the reflection short and actionable

Paper title: {paper_title}
Current summaries:
{summaries}
"""


final_summary_instructions = """You are writing the final paper summary in {language}.

Requirements:
- Merge the section summaries into a clean Markdown document
- Preserve citations with page numbers
- Keep the tone academic and concise
- The final summary must be short and readable, ideally within 600-900 words
- Use short paragraphs and avoid repeating the same point across sections

Paper title: {paper_title}
Section summaries:
{summaries}
"""


# =====================================================================
# QA 链路（特性二：HITL 多步推理流）
# =====================================================================

qa_planner_instructions = """你是一名严谨的学术调研规划员。
请基于下方完整论文文本与最近的对话历史，针对用户问题，输出一份《调研/答题计划》。

约束要求：
- 仅依据论文已有内容设计调研步骤，不要臆想外部资料
- 计划应涵盖：要回答的子问题、需要在文中查证的关键证据、可能的页码段、最终答题成功的判定标准
- plan_text 输出应使用清晰的 Markdown 结构（无序列表 / 子列表）
- 全部输出语言为：{language}

论文标题：{paper_title}

最近 10 轮对话：
{history}

用户问题：
{user_question}

完整论文 Markdown：
{paper_markdown}
"""


qa_drafter_instructions = """你是一名学术写作员。请严格按照下方《已审批的答题计划》撰写最终答案。

强制要求：
- 仅引用论文文本中真实存在的内容，绝不编造
- 重要论断必须带页码引用，例如 (p.3) 或 (p.5-7)
- 输出语言：{language}
- 文风：精炼、学术、避免口水话
- 如果计划要求中有事实是论文未覆盖的，请明确说明"论文未提及"

论文标题：{paper_title}

已审批的答题计划：
{approved_plan}

最近 10 轮对话：
{history}

用户问题：
{user_question}

完整论文 Markdown：
{paper_markdown}

{revision_block}
"""


qa_critic_instructions = """你是一名审稿人，请审查下方答案草稿是否满足《答题计划》的全部要求。

审查重点：
1. 是否覆盖计划中的全部 success_criteria
2. 是否存在与论文不符的幻觉信息
3. 是否冗余、是否仍然口语化
4. 引用页码是否合理且与陈述一致

只有同时通过覆盖度与无幻觉两项审查才能将 is_acceptable 标记为 true。
若不达标，请在 rewrite_instructions 中明确告诉 Drafter 该如何修改。

答题计划：
{approved_plan}

用户问题：
{user_question}

待审查草稿：
{draft}
"""


# =====================================================================
# Note 链路（特性三：后台静默笔记 Agent）
# =====================================================================

note_planner_instructions = """你是一名学术研究助理，负责把最近的对话提炼为可供日后复盘的高密度笔记。

请基于下方对话窗口（如有关键词请优先聚焦），输出笔记规划：
- 圈定必须保留的核心实体（方法/数据集/指标/结论）
- 列出必须落到笔记中的关键论点或数据
- 给出 3-6 个核心标签，用作日后检索

论文标题：{paper_title}
关键词（可为空）：{keyword}

最近 10 轮对话窗口：
{history}

完整论文 Markdown 摘要参考：
{paper_markdown}
"""


note_drafter_instructions = """你是一名严谨的学术笔记作者，请根据下方笔记规划撰写笔记初稿。

输出强制要求：
1. 顶部必须是 YAML Frontmatter，字段包含：timestamp、paper_id、paper_title、one_line_summary、tags
2. Frontmatter 之后用 Markdown 撰写正文，建议章节：
   - ## 核心结论
   - ## 关键概念 / 实体
   - ## 方法亮点 / 数据
   - ## 我的复盘建议
3. 文风克制，使用书面语，禁止"我们""大家"等口语
4. 不臆想，仅依据对话窗口与论文摘要中存在的事实
5. 笔记总长度建议 300-700 字

笔记规划：
{plan_block}

论文标题：{paper_title}
论文 ID：{paper_id}
当前时间：{timestamp}

最近 10 轮对话窗口：
{history}

完整论文 Markdown 摘要参考：
{paper_markdown}

{revision_block}
"""


note_critic_instructions = """你是一名严苛的笔记审稿人，请对下方笔记初稿做双重审查：

1. 全面性审查：规划中要求记录的核心实体 / 必录论点是否全部出现
2. 精简性审查：是否存在口语化、重复、冗余、空泛表述

若存在问题，请将 is_acceptable 设为 false，并给出 rewrite_instructions。

笔记规划：
{plan_block}

笔记初稿：
{draft}
"""


# =====================================================================
# 旧 QA / Note 接口保留（向后兼容，未在新流程中使用）
# =====================================================================

qa_instructions = """You are a professional academic paper question answering assistant.
Answer the user's question only from the provided paper context.

Requirements:
- Do not invent facts
- Cite every important claim with page-based references like (p.X)
- Keep the response in {language}
- Keep the answer concise and focused

Paper title: {paper_title}
Relevant paper context:
{relevant_chunks}

User question: {question}
"""


note_generator_instructions = """Turn the following question and answer into a concise study note.

Requirements:
- Keep it short and useful for later review
- Preserve the cited pages
- Format it as Markdown

Question: {question}
Answer: {answer}
Citations: {citations}
"""
