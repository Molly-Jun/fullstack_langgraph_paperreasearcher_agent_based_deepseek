import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Upload, Send, StopCircle, Brain, Cpu, ListFilter, Zap } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const SUMMARY_PROMPTS = [
  { value: "summary", label: "标准摘要", prompt: "请生成结构清晰、带页码引用的标准摘要。" },
  { value: "detailed_summary", label: "详细摘要", prompt: "请生成更详细的摘要，覆盖尽可能多的关键信息，并带页码引用。" },
  { value: "concise_summary", label: "精简摘要", prompt: "请生成简洁摘要，只保留最核心的信息，并带页码引用。" },
];

interface InputFormProps {
  onSubmit: (
    inputValue: string,
    summaryPrompts: string,
    effort: string,
    model: string,
    mode: "summary" | "qa"
  ) => void;
  onCancel: () => void;
  isLoading: boolean;
  hasHistory: boolean;
  onUploadPdf: (file: File) => void;
}

export const InputForm: React.FC<InputFormProps> = ({
  onSubmit,
  onCancel,
  isLoading,
  hasHistory,
  onUploadPdf,
}) => {
  const [internalInputValue, setInternalInputValue] = useState("");
  const [summaryPrompts, setSummaryPrompts] = useState("summary");
  const [effort, setEffort] = useState("medium");
  const [model, setModel] = useState("deepseek-chat");
  const selectedPrompt = SUMMARY_PROMPTS.find((item) => item.value === summaryPrompts);

  const handleQuestionSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!internalInputValue.trim()) return;
    onSubmit(internalInputValue, selectedPrompt?.prompt ?? summaryPrompts, effort, model, "qa");
    setInternalInputValue("");
  };

  const handleSummarySubmit = () => {
    onSubmit("", selectedPrompt?.prompt ?? summaryPrompts, effort, model, "summary");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleQuestionSubmit();
    }
  };

  return (
    <form onSubmit={handleQuestionSubmit} className="flex flex-col gap-2 p-3 pb-4">
      <div
        className={`flex flex-col gap-3 text-white rounded-3xl rounded-bl-sm ${
          hasHistory ? "rounded-br-sm" : ""
        } break-words min-h-7 bg-neutral-700 px-4 pt-4`}
      >
        <div className="flex flex-wrap gap-2 items-center">
          <div className="flex flex-row gap-2 bg-neutral-800/70 border-neutral-600 text-neutral-300 rounded-xl rounded-t-sm pl-2">
            <div className="flex flex-row items-center text-sm ml-1">
              <ListFilter className="h-4 w-4 mr-2" />
              摘要模式
            </div>
            <Select value={summaryPrompts} onValueChange={setSummaryPrompts}>
              <SelectTrigger className="w-[150px] bg-transparent border-none cursor-pointer">
                <SelectValue placeholder="选择摘要模式" />
              </SelectTrigger>
              <SelectContent className="bg-neutral-700 border-neutral-600 text-neutral-300 cursor-pointer">
                {SUMMARY_PROMPTS.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-row gap-2 bg-neutral-800/70 border-neutral-600 text-neutral-300 rounded-xl rounded-t-sm pl-2">
            <div className="flex flex-row items-center text-sm">
              <Brain className="h-4 w-4 mr-2" />
              Effort
            </div>
            <Select value={effort} onValueChange={setEffort}>
              <SelectTrigger className="w-[120px] bg-transparent border-none cursor-pointer">
                <SelectValue placeholder="Effort" />
              </SelectTrigger>
              <SelectContent className="bg-neutral-700 border-neutral-600 text-neutral-300 cursor-pointer">
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="high">High</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-row gap-2 bg-neutral-800/70 border-neutral-600 text-neutral-300 rounded-xl rounded-t-sm pl-2">
            <div className="flex flex-row items-center text-sm ml-2">
              <Cpu className="h-4 w-4 mr-2" />
              Model
            </div>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger className="w-[160px] bg-transparent border-none cursor-pointer">
                <SelectValue placeholder="Model" />
              </SelectTrigger>
              <SelectContent className="bg-neutral-700 border-neutral-600 text-neutral-300 cursor-pointer">
                <SelectItem value="deepseek-chat">
                  <div className="flex items-center">
                    <Zap className="h-4 w-4 mr-2 text-yellow-400" /> DeepSeek Chat
                  </div>
                </SelectItem>
                <SelectItem value="deepseek-reasoner">
                  <div className="flex items-center">
                    <Cpu className="h-4 w-4 mr-2 text-purple-400" /> DeepSeek Reasoner
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <Textarea
            value={internalInputValue}
            onChange={(e) => setInternalInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你关于这篇论文的问题"
            className="w-full text-neutral-100 placeholder-neutral-500 resize-none border-0 focus:outline-none focus:ring-0 outline-none focus-visible:ring-0 shadow-none md:text-base min-h-[56px] max-h-[200px] bg-transparent"
            rows={1}
          />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="default"
                disabled={isLoading}
                onClick={handleSummarySubmit}
                className="bg-blue-600 hover:bg-blue-500 text-white cursor-pointer rounded-xl"
              >
                生成摘要
              </Button>
              <Button
                type="submit"
                variant="ghost"
                disabled={!internalInputValue.trim() || isLoading}
                className="text-blue-500 hover:text-blue-400 hover:bg-blue-500/10 p-2 cursor-pointer rounded-full transition-all duration-200 text-base"
              >
                提交提问
                <Send className="h-5 w-5" />
              </Button>
            </div>
            {isLoading ? (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="text-red-500 hover:text-red-400 hover:bg-red-500/10 p-2 cursor-pointer rounded-full transition-all duration-200"
                onClick={onCancel}
              >
                <StopCircle className="h-5 w-5" />
              </Button>
            ) : null}
          </div>
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label className="flex flex-row items-center gap-2 bg-neutral-700 border-neutral-600 text-neutral-300 rounded-xl rounded-t-sm px-3 py-2 cursor-pointer">
          <Upload className="h-4 w-4" />
          上传 PDF
          <input
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onUploadPdf(file);
            }}
          />
        </label>
        {hasHistory && (
          <Button
            className="bg-neutral-700 border-neutral-600 text-neutral-300 cursor-pointer rounded-xl rounded-t-sm pl-2"
            variant="default"
            onClick={() => window.location.reload()}
          >
            <Upload size={16} />
            New Paper
          </Button>
        )}
      </div>
    </form>
  );
};