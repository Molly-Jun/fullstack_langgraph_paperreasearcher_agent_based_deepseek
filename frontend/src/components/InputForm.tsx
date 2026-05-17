import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Send, StopCircle } from "lucide-react";
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
}

export const InputForm: React.FC<InputFormProps> = ({
  onSubmit,
  onCancel,
  isLoading,
  hasHistory,
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
    </form>
  );
};
