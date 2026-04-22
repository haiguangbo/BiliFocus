type StatusPanelProps = {
  title: string;
  description: string;
};

export function StatusPanel({ title, description }: StatusPanelProps) {
  return (
    <div className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
      <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-blue-600/75">{title}</p>
      <p className="mt-4 text-sm leading-7 text-slate-600">{description}</p>
    </div>
  );
}
