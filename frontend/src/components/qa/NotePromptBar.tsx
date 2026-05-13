import { NoteActionButton } from "./NoteActionButton";

interface NotePromptBarProps {
  onNoteClick: () => void;
  isActive?: boolean;
}

export function NotePromptBar({ onNoteClick, isActive }: NotePromptBarProps) {
  return (
    <div className="border-t border-slate-800/80 bg-[#0e1420] p-4">
      <div className="mb-2 text-xs uppercase tracking-[0.24em] text-slate-500">
        灵感整理
      </div>
      <div className="flex items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3">
        <div>
          <div className="text-sm font-medium text-slate-100">将当前灵感整理为笔记</div>
          <div className="mt-1 text-xs text-slate-500">
            这里先提供 UI 骨架，后续再接入真实后端整理流程。
          </div>
        </div>
        <NoteActionButton onClick={onNoteClick} isActive={isActive} />
      </div>
    </div>
  );
}
