import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface SummaryControlPanelProps {
  value: string;
  onChange: (value: string) => void;
  onGenerate: () => void;
  isLoading: boolean;
}

const SUMMARY_PRESETS = [
  { value: "summary", label: "简易模式" },
  { value: "detailed_summary", label: "详细模式" },
  { value: "concise_summary", label: "精简模式" },
];

export function SummaryControlPanel({
  value,
  onChange,
  onGenerate,
  isLoading,
}: SummaryControlPanelProps) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-slate-700">摘要模式</span>
        <Select value={value} onValueChange={onChange}>
          <SelectTrigger className="w-[160px] bg-white">
            <SelectValue placeholder="选择摘要模式" />
          </SelectTrigger>
          <SelectContent>
            {SUMMARY_PRESETS.map((item) => (
              <SelectItem key={item.value} value={item.value}>
                {item.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Button
        type="button"
        className="bg-slate-900 text-white hover:bg-slate-800"
        onClick={onGenerate}
        disabled={isLoading}
      >
        生成摘要
      </Button>
    </div>
  );
}
