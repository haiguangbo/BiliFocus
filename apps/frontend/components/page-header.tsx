type PageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  aside?: React.ReactNode;
};

export function PageHeader({ eyebrow, title, description, aside }: PageHeaderProps) {
  return (
    <section className="overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
      <div className="grid gap-4 px-6 py-6 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
        <div className="max-w-3xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-blue-600/80">{eyebrow}</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{title}</h1>
          <p className="mt-3 text-sm leading-7 text-slate-600">{description}</p>
        </div>
        {aside ? <div className="lg:justify-self-end">{aside}</div> : null}
      </div>
    </section>
  );
}
