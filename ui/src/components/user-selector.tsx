"use client";

/**
 * UserSelector — shared component used across Memory Lab, Profiles, and Context Studio.
 *
 * Fetches known user_ids from GET /api/v1/users, renders as a combobox:
 *   - Dropdown: pick an existing user_id
 *   - Freetext fallback: type any new user_id (not yet in Redis)
 *
 * On select/confirm it writes to Zustand currentUserId so all pages stay in sync.
 */

import { useState, useEffect } from "react";
import { useAppUsers } from "@/lib/hooks/use-app-users";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, UserRound, ChevronDown, PenLine } from "lucide-react";
import { useT } from "@/lib/i18n";

interface Props {
  label?: string;
  onConfirm?: (userId: string) => void;
  /** If true, shows a "Load" button; otherwise calls onConfirm immediately on change */
  withButton?: boolean;
  buttonLabel?: string;
  loading?: boolean;
  /** Override the default user list (e.g. for Operator pages that have their own user source) */
  knownUserIds?: string[];
}

const NEW_USER_SENTINEL = "__new__";

export function UserSelector({
  label,
  onConfirm,
  withButton = true,
  buttonLabel,
  loading = false,
  knownUserIds,
}: Props) {
  const t = useT();
  const effectiveLabel = label ?? t("common.userId");
  const effectiveButtonLabel = buttonLabel ?? t("common.load");
  const { currentUserId, setCurrentUserId } = useAppStore();
  const currentAppId = useAppStore((s) => s.currentAppId);
  const [localId, setLocalId] = useState(currentUserId);
  const [mode, setMode] = useState<"select" | "text">("select");

  // 使用当前 App 的 external_users（来自 Step 7 的 dashboard users endpoint）。
  // 没选 App 时 query 自动 disable（useAppUsers 内部 enabled: !!appId）。
  // 如果调用方提供了 knownUserIds（例如 Operator 页面），则跳过 fetch。
  const { data, isFetching } = useAppUsers(
    knownUserIds ? undefined : currentAppId,
    500,
    0,
  );
  const knownUsers = knownUserIds ?? (data?.data ?? []).map((u) => u.external_user_id);

  // 加载完毕后若无已知用户，自动切换到文本输入模式，避免用户困惑
  useEffect(() => {
    if (!isFetching && knownUsers.length === 0 && mode === "select") {
      setMode("text");
    }
  }, [isFetching, knownUsers.length, mode]);

  function handleChange(val: string) {
    if (val === NEW_USER_SENTINEL) {
      setMode("text");
      setLocalId("");
    } else {
      setLocalId(val);
      // Auto-confirm on dropdown selection — manual input still requires explicit confirm
      setCurrentUserId(val);
      onConfirm?.(val);
    }
  }

  function handleConfirm() {
    if (!localId) return;
    setCurrentUserId(localId);
    onConfirm?.(localId);
  }

  return (
    <div className="space-y-1.5">
      <Label>{effectiveLabel}</Label>
      <div className="flex gap-2">
        {mode === "select" ? (
          <div className="flex-1 flex gap-2">
            <Select value={localId || undefined} onValueChange={(v) => handleChange(v ?? "")}>
              <SelectTrigger className="flex-1" aria-label={effectiveLabel}>
                {isFetching ? (
                  <span className="flex items-center gap-1.5 text-muted-foreground text-sm">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" /> {t("common.loadingUsers")}
                  </span>
                ) : (
                  <SelectValue placeholder={t("common.selectUser")} />
                )}
              </SelectTrigger>
              <SelectContent>
                {knownUsers.map((u) => (
                  <SelectItem key={u} value={u}>
                    <span className="flex items-center gap-2">
                      <UserRound className="h-3.5 w-3.5 text-muted-foreground" />
                      {u}
                    </span>
                  </SelectItem>
                ))}
                <SelectItem value={NEW_USER_SENTINEL}>
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <PenLine className="h-3.5 w-3.5" />
                    {t("common.enterNewId")}
                  </span>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        ) : (
          <div className="flex-1 flex gap-2">
            <Input
              autoFocus
              placeholder="user_01"
              value={localId}
              onChange={(e) => setLocalId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleConfirm()}
              onBlur={() => { if (localId && localId !== currentUserId) handleConfirm(); }}
            />
            {knownUsers.length > 0 && (
              <Button variant="ghost" size="icon" onClick={() => setMode("select")} title={t("common.pickFromList")} aria-label={t("common.pickFromList")}>
                <ChevronDown className="h-4 w-4" />
              </Button>
            )}
          </div>
        )}

        {withButton && (
          <Button onClick={handleConfirm} disabled={!localId || loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : effectiveButtonLabel}
          </Button>
        )}
      </div>
    </div>
  );
}
