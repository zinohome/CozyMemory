import { I18nProvider } from "@/lib/i18n";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <I18nProvider>
      <div className="min-h-screen flex items-center justify-center bg-muted p-4">
        <div className="w-full max-w-md">{children}</div>
      </div>
    </I18nProvider>
  );
}
