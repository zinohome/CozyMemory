"use client";

import { Brain, Database, MessageSquare, Users } from "lucide-react";
import { I18nProvider, useT } from "@/lib/i18n";

function AuthContent({ children }: { children: React.ReactNode }) {
  const t = useT();
  return (
    <div className="auth-layout">
      {/* 左侧：表单 */}
      <div className="auth-left bg-background">
        <div className="w-full max-w-sm space-y-6">
          <div className="space-y-1">
            <h1 className="text-2xl font-bold tracking-tight">CozyMemory</h1>
            <p className="text-sm text-muted-foreground">
              统一 AI 记忆平台
            </p>
          </div>
          {children}
        </div>
      </div>

      {/* 右侧：品牌故事 */}
      <div className="auth-right">
        <div className="relative z-10 max-w-md space-y-8">
          <div className="space-y-3">
            <h2 className="text-3xl font-bold tracking-tight">
              让 AI 拥有记忆
            </h2>
            <p className="text-white/70 text-sm leading-relaxed">
              CozyMemory 整合三大记忆引擎，为你的 AI 应用提供对话记忆、用户画像和知识图谱能力。
            </p>
          </div>

          <div className="space-y-3">
            <div className="auth-feature">
              <MessageSquare className="size-5 text-white/80 shrink-0 mt-0.5" />
              <div>
                <div className="font-medium text-sm">对话记忆</div>
                <div className="text-xs text-white/50 mt-0.5">Mem0 引擎自动提取对话中的事实，语义搜索召回</div>
              </div>
            </div>
            <div className="auth-feature">
              <Users className="size-5 text-white/80 shrink-0 mt-0.5" />
              <div>
                <div className="font-medium text-sm">用户画像</div>
                <div className="text-xs text-white/50 mt-0.5">Memobase 引擎结构化管理用户兴趣、偏好和属性</div>
              </div>
            </div>
            <div className="auth-feature">
              <Brain className="size-5 text-white/80 shrink-0 mt-0.5" />
              <div>
                <div className="font-medium text-sm">知识图谱</div>
                <div className="text-xs text-white/50 mt-0.5">Cognee 引擎构建领域知识图谱，实现推理搜索</div>
              </div>
            </div>
            <div className="auth-feature">
              <Database className="size-5 text-white/80 shrink-0 mt-0.5" />
              <div>
                <div className="font-medium text-sm">多租户隔离</div>
                <div className="text-xs text-white/50 mt-0.5">UUID v5 命名空间确保 App 间数据完全隔离</div>
              </div>
            </div>
          </div>

          <div className="text-xs text-white/30 pt-4">
            REST API · gRPC · 全栈本地化部署
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <I18nProvider>
      <AuthContent>{children}</AuthContent>
    </I18nProvider>
  );
}
