import { Sparkles } from "lucide-react";

interface NoteActionButtonProps {
  onClick: () => void;
  isActive?: boolean;
}

export function NoteActionButton({ onClick, isActive }: NoteActionButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition ${
        isActive
          ? "bg-emerald-400 text-slate-950"
          : "bg-gradient-to-r from-cyan-400 to-blue-500 text-white hover:from-cyan-300 hover:to-blue-400"
      }`}
    >
      <Sparkles className="h-4 w-4" />
      记笔记
    </button>
  );
}
