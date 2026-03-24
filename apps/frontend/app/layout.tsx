import "./globals.css";
import Link from "next/link";
import type { Metadata } from "next";

import { AppNavigation } from "@/components/app-navigation";

export const metadata: Metadata = {
  title: "BiliFocus",
  description: "本地优先的 Bilibili 内容工作台，用更克制的方式完成搜索、整理、同步与回看。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>
        <div className="mx-auto min-h-screen max-w-[1440px] px-5 py-6 lg:px-8">
          <header className="mb-8 overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
            <div className="flex flex-col gap-6 px-6 py-6 lg:flex-row lg:items-end lg:justify-between">
              <div className="flex flex-col gap-3">
                <div className="inline-flex w-fit items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.28em] text-blue-700">
                  <span className="h-2 w-2 rounded-full bg-blue-600" />
                  BiliFocus
                </div>
                <div>
                  <Link className="text-3xl font-semibold tracking-tight text-slate-950" href="/">
                    Bilibili 内容工作台
                  </Link>
                  <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600">
                    从发现、筛选到沉淀和回看，把分散的视频线索整理成一个真正属于你的本地内容库。
                  </p>
                </div>
              </div>
              <AppNavigation />
            </div>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
