from datetime import datetime


def get_current_date():
    return datetime.now().strftime("%B %d, %Y")


# =====================================================================
# Summary 链路（特性一：基于 Markdown 章节切块的并行摘要）
# =====================================================================

section_summarizer_instructions = """你是一名严谨的学术分析员，请用 {language} 总结下方论文章节。

要求：
- 提炼 3-5 条 key_points（要点）
- 同时列出该章节出现的 3-6 个核心实体（key_entities）：方法名 / 数据集 / 指标 / 关键概念 / 模型名等
- summary_text 控制在 80-150 字，忠实于原文
- 引用（citations）使用以下格式：'<章节名> - <段落前两个 token>'
  · 例如：'Method - We propose' 或 '方法 - 本文提出'
  · 段落前两词使用原文出现的连续词串，便于读者在 PDF 中检索定位
  · 若实在无法对应到段落，可仅写章节名

章节标题：{section_title}

章节正文：
{section_text}
"""


summary_prompts = {
    "summary": "请生成结构清晰、带章节锚点引用的标准摘要。整体摘要请控制在 800 字以内，突出最核心内容。",
    "detailed_summary": "请生成较详细但仍然简洁的摘要，覆盖关键信息并带章节锚点引用。整体摘要请控制在 1200 字以内。",
    "concise_summary": "请生成简洁摘要，只保留最核心的信息，并带章节锚点引用。整体摘要请控制在 500 字以内。",
}


summary_reflection_instructions = """请审查下方论文摘要是否覆盖了重要内容。

要求：
- 指出仍然缺失的重要信息
- 若已经足够，请将 is_complete 标为 true
- 反思应简短、可执行

论文标题：{paper_title}
当前摘要：
{summaries}
"""

# - 保留章节锚点引用（'<章节名> - <段落前两词>' 格式），不要替换或删除
final_summary_instructions = """请用 {language} 撰写最终的论文摘要 Markdown 文档。

要求：
- 把章节摘要合并为整洁的 Markdown
-不需要保留原来的章节引用锚点，仅用'<章节名>'格式即可。
- 在文末新增一节 `## 关键概念 / 实体`，写最重要的五个实体，并在后面用几句话概述解释
- 文风学术、克制、避免重复
- 全文控制在 600-900 字之内，使用短段落

论文标题：{paper_title}

章节摘要（含 key_entities）：
{summaries}
"""


# =====================================================================
# QA 链路（特性二：HITL 多步推理流）
# =====================================================================

qa_planner_instructions = """你是一名严谨但表达简洁的学术调研规划员。
请基于完整论文与最近的对话，针对用户问题，输出一份《调研/答题计划》。

输出约束：
- plan_text：使用 Markdown 无序列表，4-6 条要点，每条不超过 30 字
  · 兼顾用户可读性与专业性，避免冗长说教
  · 内容覆盖：拆解的子问题、要在论文中查证的关键点
- research_steps：3-5 条简短关键词式动作（如「定位 §3.2 训练设置」「核对表 2 的指标」）
- 仅依据论文文本设计计划,但如果用户问题相对论文更加发散，可以结合自身知识，但一定要保证严谨性，不要臆造外部资料
- 全部输出语言为：{language}

论文标题：{paper_title}

最近对话：
{history}

用户问题：
{user_question}

完整论文 Markdown：
{paper_markdown}
"""


qa_drafter_instructions = """你是一名学术写作员。请严格按照下方《已审批的答题计划》撰写最终答案。

强制要求：
- 仅引用论文文本中真实存在的内容，绝不编造
- 引用使用「章节锚点」格式：'<章节名> - <段落前两个 token>'
  · 例如 'Method - We propose'、'实验 - 本文在'
  · 优先精确到段落；实在无法定位则仅写章节名
  · 注意不要滥用大量引用，关键点后面添加引用一次即可
- 输出语言：{language}
- 文风：精炼、学术、避免口水话
- 若计划要求中有事实是论文未覆盖的，请明确说明"论文未提及"
- 如果用户问题相对论文更加发散，可以结合自身知识，但一定要保证严谨性，不要臆造外部资料

论文标题：{paper_title}

已审批的答题计划：
{approved_plan}

最近对话：
{history}

用户问题：
{user_question}

完整论文 Markdown：
{paper_markdown}

{revision_block}
"""


qa_critic_instructions = """你是一名审稿人，请审查下方答案草稿是否满足《答题计划》的全部要求。

审查重点：
1. 是否完整回应了用户问题与计划要点
2. 是否存在与论文不符、或完全臆造的外部知识的幻觉信息
3. 是否冗余、是否仍然口语化
4. 引用是否使用了 '<章节名> - <段落前两词>' 格式且与陈述一致

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

note_planner_instructions = """你是一名学术研究助理，负责把最近的「问答对话」整理为可供日后复盘的笔记。

重要原则：
- 笔记的主体是【用户与助手之间的问答对话】
- 论文内容只是【背景】，不要重新概括论文
- 我们关注的是：用户在阅读论文 / 摘要后产生了哪些问题、得到了哪些结论、引发了什么思考

请基于下方对话窗口（如有关键词请优先聚焦），输出笔记规划：
- plan_text：简短陈述本轮问答的组织思路与重点，若有关键词，则更侧重于关键词相关的问答内容
- must_record_qa：问题: ... → 结论: ...」形式的问答要点，若有关键词，则更侧重于关键词相关的问答内容
- one_line_summary：对文章内容的一句话总结，不超过 30 字，用于概述背景（用于frontmatter）

论文标题（仅作背景）：{paper_title}
关键词（可为空）：{keyword}

最近的问答对话窗口（重点）：
{history}

完整论文 Markdown（仅作背景，请勿照抄）：
{paper_markdown}
"""


note_drafter_instructions = """你是一名严谨的学术笔记作者，请根据下方笔记规划撰写笔记初稿。

【关键定位】
- 这是一份针对【问答对话】的笔记，论文只是背景
- 不要把笔记写成"论文综述"或"论文内容摘要"
- 围绕"用户问了什么问题 + 得到了什么结论 + 有什么启发"展开

【输出强制要求】
1. 顶部必须是 YAML Frontmatter，仅包含三个字段：
   ```
   ---
   timestamp: "{timestamp}"
   paper_title: "{paper_title}"
   one_line_summary: "<论文内容的一句话总结>"
   ---
   ```
2. Frontmatter 之后用 Markdown 撰写正文，建议结构：
   - ## 本轮问答
     - 用「**Q:** ... / **A:** ...」形式逐条记录核心问答（保留关键引用如「Method - …」即可）
   - ## 启发与延伸思考（可选，1-3 条）
3. 文风克制，使用书面语，禁止"我们""大家"等口语
4. 不臆想，仅依据对话窗口与论文背景中存在的事实
5. 笔记总长度建议 200-500 字，应明显短于一份论文摘要

笔记规划：
{plan_block}

论文标题（背景）：{paper_title}
当前时间：{timestamp}

最近问答对话窗口（重点）：
{history}

完整论文 Markdown（仅作背景）：
{paper_markdown}

{revision_block}
"""


note_critic_instructions = """你是一名严苛的笔记审稿人，请对下方笔记初稿做双重审查：

1. 全面性审查：规划中 must_record_qa 的问答要点是否全部出现
2. 精简性审查：是否口语化 / 重复 / 冗余 / 跑题（写论文综述而非写问答）
3. 结构审查：frontmatter 是否仅包含 timestamp / paper_title / one_line_summary 三个字段；正文是否以「问答」为核心

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
- Cite every important claim using '<section title> - <first 5 words of paragraph>' anchors
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
- Preserve the section-anchor citations
- Format it as Markdown

Question: {question}
Answer: {answer}
Citations: {citations}
"""
