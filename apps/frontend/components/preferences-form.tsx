"use client";

import { useEffect, useState } from "react";

import { createBilibiliQRCode, getPreferences, pollBilibiliQRCode, rewriteLibraryMetadata, savePreferences } from "@/lib/api";
import { PreferenceConfig } from "@/types/api";

type PreferencesFormProps = {
  initialValue: PreferenceConfig;
};

export function PreferencesForm({ initialValue }: PreferencesFormProps) {
  const [form, setForm] = useState({ ...initialValue, default_source: "default" });
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [rewriteBusy, setRewriteBusy] = useState(false);
  const [rewriteMessage, setRewriteMessage] = useState("");
  const [qrcodeBusy, setQrcodeBusy] = useState(false);
  const [qrcodeMessage, setQrcodeMessage] = useState("");
  const [qrcodeSession, setQrcodeSession] = useState<{
    qrcodeKey: string;
    loginUrl: string;
    expiresInSeconds: number;
  } | null>(null);

  useEffect(() => {
    if (!qrcodeSession) {
      return;
    }

    let cancelled = false;
    const intervalId = window.setInterval(async () => {
      try {
        const result = await pollBilibiliQRCode(qrcodeSession.qrcodeKey);
        if (cancelled) {
          return;
        }

        setQrcodeMessage(result.message);

        if (result.status === "completed" && result.cookie_configured) {
          const preferences = await getPreferences();
          if (cancelled) {
            return;
          }
          setForm((current) => ({
            ...current,
            bilibili_cookie: preferences.bilibili_cookie,
          }));
          setQrcodeMessage("扫码登录成功，Cookie 已写入当前设置。");
          setQrcodeSession(null);
          setMessage("已同步 Bilibili Cookie 到本地设置");
          return;
        }

        if (result.status === "expired" || result.status === "failed") {
          setQrcodeSession(null);
        }
      } catch (error) {
        if (cancelled) {
          return;
        }
        setQrcodeMessage(error instanceof Error ? error.message : "二维码登录状态轮询失败");
        setQrcodeSession(null);
      }
    }, 2500);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [qrcodeSession]);

  async function handleSubmit() {
    setSaving(true);
    setMessage("");
    try {
      await savePreferences(form);
      setMessage("设置已保存到 backend");
    } catch {
      setMessage("保存失败，请检查 backend 是否可用");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateQRCode() {
    setQrcodeBusy(true);
    setQrcodeMessage("");
    setMessage("");
    try {
      const result = await createBilibiliQRCode();
      setQrcodeSession({
        qrcodeKey: result.qrcode_key,
        loginUrl: result.login_url,
        expiresInSeconds: result.expires_in_seconds,
      });
      setQrcodeMessage("二维码已生成，请使用 Bilibili App 扫码并在手机上确认登录。");
    } catch (error) {
      setQrcodeMessage(error instanceof Error ? error.message : "生成二维码失败");
      setQrcodeSession(null);
    } finally {
      setQrcodeBusy(false);
    }
  }

  const qrcodeImageUrl = qrcodeSession
    ? `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(qrcodeSession.loginUrl)}`
    : null;

  return (
    <section className="grid gap-5">
      <div className="grid gap-5 lg:grid-cols-2">
        <section className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
          <div className="mb-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-600/75">数据源与搜索</p>
            <h3 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">默认获取策略</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">控制视频获取页的默认搜索规模与基础筛选文本。</p>
          </div>
          <div className="grid gap-4">
            <label className="flex flex-col gap-2 text-sm text-slate-700">
              <span>默认搜索源策略</span>
              <select
                className="rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900"
                data-testid="preferences-source-select"
                value={form.default_source}
                onChange={() => setForm((current) => ({ ...current, default_source: "default" }))}
              >
                <option value="default">真实 Bilibili Web</option>
              </select>
            </label>
            <label className="flex flex-col gap-2 text-sm text-slate-700">
              <span>默认搜索条数</span>
              <input
                className="rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900"
                data-testid="preferences-limit-input"
                type="number"
                value={form.default_search_limit}
                onChange={(event) =>
                  setForm((current) => ({ ...current, default_search_limit: Number(event.target.value) }))
                }
              />
            </label>
            <label className="flex flex-col gap-2 text-sm text-slate-700">
              <span>默认筛选文本</span>
              <input
                className="rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900"
                data-testid="preferences-filter-input"
                value={form.default_filter_text}
                onChange={(event) => setForm((current) => ({ ...current, default_filter_text: event.target.value }))}
              />
            </label>
          </div>
        </section>

        <section className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
          <div className="mb-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-600/75">本地缓存</p>
            <h3 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">本地落盘与片库规则</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">控制本地文件缓存目录与片库浏览默认排序方式。</p>
          </div>
          <div className="grid gap-4">
            <label className="flex flex-col gap-2 text-sm text-slate-700">
              <span>下载输出目录</span>
              <input
                className="rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900"
                data-testid="preferences-download-dir-input"
                value={form.download_output_dir}
                onChange={(event) => setForm((current) => ({ ...current, download_output_dir: event.target.value }))}
              />
              <span className="text-xs leading-5 text-slate-500">“缓存到本地文件”会把 mp4 写入这里。</span>
            </label>
            <label className="flex flex-col gap-2 text-sm text-slate-700">
              <span>片库排序</span>
              <select
                className="rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900"
                data-testid="preferences-library-sort-select"
                value={form.library_sort}
                onChange={(event) => setForm((current) => ({ ...current, library_sort: event.target.value }))}
              >
                <option value="recent">最近同步</option>
                <option value="views">播放量</option>
                <option value="published_at">发布时间</option>
              </select>
            </label>
          </div>
        </section>
      </div>

      <section className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-600/75">库维护</p>
            <h3 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">结构化重写</h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              用于补写本地库中最近同步的视频元数据，补充摘要、标签和学习焦点，让后续检索和整理更顺手。
            </p>
          </div>
          <button
            className="rounded-[18px] bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-300"
            disabled={rewriteBusy}
            onClick={async () => {
              setRewriteBusy(true);
              setRewriteMessage("");
              try {
                const result = await rewriteLibraryMetadata({ limit: 20 });
                setRewriteMessage(`已重写 ${result.rewritten_count} 条，跳过 ${result.skipped_count} 条。刷新片库页面可查看更新。`);
              } catch (error) {
                setRewriteMessage(error instanceof Error ? error.message : "重写失败");
              } finally {
                setRewriteBusy(false);
              }
            }}
            type="button"
          >
            {rewriteBusy ? "正在重写..." : "重写本地库元数据"}
          </button>
        </div>
        <div className="rounded-[20px] border border-slate-100 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-600">
          默认处理最近同步的视频，适合作为同步完成后的补全动作。
        </div>
        {rewriteMessage ? <p className="mt-3 text-sm text-slate-600">{rewriteMessage}</p> : null}
      </section>

      <section className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
        <div className="mb-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-600/75">登录态与高清资源</p>
          <h3 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">Bilibili Cookie</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">可选填完整 Cookie 或单独的 `SESSDATA`，用于请求更高画质和更完整的播放信息。</p>
        </div>
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px]">
          <div className="grid gap-3">
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-[20px] border border-slate-100 bg-slate-50 px-4 py-3">
              <div>
                <p className="text-sm font-medium text-slate-900">当前 Cookie</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  {form.bilibili_cookie ? "已存在本地登录态，可直接用于高清视频和更完整的播放信息请求。" : "当前还没有本地登录态，可以手动粘贴，也可以用右侧二维码扫码写入。"}
                </p>
              </div>
              <span
                className={`rounded-full px-3 py-1 text-xs font-medium ${form.bilibili_cookie ? "bg-emerald-50 text-emerald-700" : "bg-slate-200 text-slate-600"}`}
              >
                {form.bilibili_cookie ? "已配置" : "未配置"}
              </span>
            </div>

            <label className="flex flex-col gap-2 text-sm text-slate-700">
              <span>Bilibili Cookie / SESSDATA</span>
              <textarea
                className="min-h-40 rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3 font-mono text-xs leading-6 text-slate-900"
                data-testid="preferences-cookie-input"
                placeholder="可粘贴完整 Cookie，或只粘贴 SESSDATA 值。用于同步时探测更高清晰度。"
                value={form.bilibili_cookie}
                onChange={(event) => setForm((current) => ({ ...current, bilibili_cookie: event.target.value }))}
              />
            </label>
          </div>

          <div className="rounded-[20px] border border-slate-100 bg-slate-50 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-900">二维码登录</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  在这里生成二维码后，可直接用 Bilibili App 扫码，并自动写入当前 Cookie 字段。
                </p>
              </div>
            </div>

            <div className="mt-4 flex min-h-[220px] items-center justify-center rounded-[18px] border border-dashed border-slate-200 bg-white">
              {qrcodeImageUrl ? (
                <img
                  alt="Bilibili 扫码登录二维码"
                  className="h-[220px] w-[220px] rounded-[12px]"
                  data-testid="preferences-cookie-qrcode"
                  src={qrcodeImageUrl}
                />
              ) : (
                <div className="px-6 text-center text-xs leading-6 text-slate-500">
                  {form.bilibili_cookie
                    ? "当前已存在本地 Cookie。如需切换账号，可重新生成二维码覆盖。"
                    : "点击下方按钮生成二维码。"}
                </div>
              )}
            </div>

            <div className="mt-4 flex flex-wrap gap-3">
              <button
                className="rounded-[18px] bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-300"
                data-testid="preferences-cookie-qrcode-button"
                disabled={qrcodeBusy}
                onClick={handleCreateQRCode}
                type="button"
              >
                {qrcodeBusy ? "生成中..." : qrcodeSession ? "重新生成二维码" : "生成二维码"}
              </button>
              {qrcodeSession ? (
                <a
                  className="rounded-[18px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 hover:border-slate-300"
                  href={qrcodeSession.loginUrl}
                  rel="noreferrer"
                  target="_blank"
                >
                  在浏览器中打开
                </a>
              ) : null}
            </div>

            <div className="mt-3 text-xs leading-5 text-slate-500">
              {qrcodeSession ? `二维码会话有效期约 ${qrcodeSession.expiresInSeconds} 秒，前端会自动轮询登录状态。` : "扫码完成后，这里会自动回填最新 Cookie。"}
            </div>
            {qrcodeMessage ? (
              <p className="mt-3 rounded-[16px] bg-white px-3 py-2 text-sm text-slate-600">{qrcodeMessage}</p>
            ) : null}
          </div>
        </div>
      </section>

      <div className="flex flex-wrap items-center gap-3 rounded-[24px] border border-slate-200 bg-white px-5 py-4 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
        <button
          className="rounded-[18px] bg-blue-600 px-5 py-3 font-medium text-white disabled:bg-slate-300 disabled:text-slate-500"
          data-testid="preferences-save-button"
          disabled={saving}
          onClick={handleSubmit}
          type="button"
        >
          {saving ? "保存中..." : "保存设置"}
        </button>
        <span className="text-sm text-slate-500" data-testid="preferences-message">{message}</span>
      </div>
    </section>
  );
}
