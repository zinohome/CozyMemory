import { I18nProvider } from "@/lib/i18n";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <I18nProvider>
      <div className="login-bg relative min-h-screen flex items-center justify-center p-4">
        <div className="relative z-10 w-full max-w-md space-y-6">
          <div className="text-center">
            <h1 className="text-3xl font-extrabold tracking-tight text-white">
              CozyMemory
            </h1>
            <p className="text-sm text-white/60 mt-1.5">
              Unified AI Memory Platform
            </p>
          </div>
          <div className="login-card rounded-lg p-1">{children}</div>
        </div>
      </div>
    </I18nProvider>
  );
}
