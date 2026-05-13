import ReactMarkdown from "react-markdown";

interface SummaryMarkdownViewProps {
  summaryText: string | null;
}

export function SummaryMarkdownView({ summaryText }: SummaryMarkdownViewProps) {
  if (!summaryText) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-8 text-sm text-slate-500">
        尚未生成摘要。
      </div>
    );
  }

  return (
    <div className="prose prose-slate max-w-none">
      <ReactMarkdown>{summaryText}</ReactMarkdown>
    </div>
  );
}
