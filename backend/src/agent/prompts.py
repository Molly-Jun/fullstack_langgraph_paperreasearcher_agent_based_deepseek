from datetime import datetime


def get_current_date():
    return datetime.now().strftime("%B %d, %Y")


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
