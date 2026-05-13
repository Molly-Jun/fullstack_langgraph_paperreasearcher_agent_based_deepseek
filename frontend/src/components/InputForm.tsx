import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Upload, Send, StopCircle } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";

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

  const handleQuestionSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!internalInputValue.trim()) return;
    onSubmit(internalInputValue, "", "", "", "qa");
    setInternalInputValue("");
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
