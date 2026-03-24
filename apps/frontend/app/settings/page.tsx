import { PageHeader } from "@/components/page-header";
import { PreferencesForm } from "@/components/preferences-form";
import { getPreferences } from "@/lib/api";

export default async function SettingsPage() {
  try {
    const preferences = await getPreferences();
    return (
      <main className="grid gap-6">
        <PageHeader
          description="集中维护本地偏好、Cookie、二维码登录与片库整理动作。这里保存的是你自己的使用习惯，不是一个账号系统。"
          eyebrow="Settings"
          title="本地偏好与系统维护"
        />
        <PreferencesForm initialValue={preferences} />
      </main>
    );
  } catch {
    return (
      <main className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
        本地设置加载失败，请确认 backend 已启动且接口可访问。
      </main>
    );
  }
}
