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

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { usersApi } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, UserRound, ChevronDown, PenLine } from "lucide-react";

interface Props {
  label?: string;
  onConfirm?: (userId: string) => void;
  /** If true, shows a "Load" button; otherwise calls onConfirm immediately on change */
  withButton?: boolean;
  buttonLabel?: string;
  loading?: boolean;
}

const NEW_USER_SENTINEL = "__new__";

export function UserSelector({
  label = "User ID",
  onConfirm,
  withButton = true,
  buttonLabel = "Load",
  loading = false,
}: Props) {
  const { currentUserId, setCurrentUserId } = useAppStore();
  const [localId, setLocalId] = useState(currentUserId);
  const [mode, setMode] = useState<"select" | "text">("select");

  const { data, isFetching } = useQuery({
    queryKey: ["users"],
    queryFn: usersApi.list,
    staleTime: 30_000,
  });

  const knownUsers = data?.data ?? [];

  function handleChange(val: string) {
    if (val === NEW_USER_SENTINEL) {
      setMode("text");
      setLocalId("");
    } else {
      setLocalId(val);
      if (!withButton) {
        setCurrentUserId(val);
        onConfirm?.(val);
      }
    }
  }

  function handleConfirm() {
    if (!localId) return;
    setCurrentUserId(localId);
    onConfirm?.(localId);
  }

  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <div className="flex gap-2">
        {mode === "select" ? (
          <div className="flex-1 flex gap-2">
            <Select value={localId || undefined} onValueChange={(v) => handleChange(v ?? "")}>
              <SelectTrigger className="flex-1">
                {isFetching ? (
                  <span className="flex items-center gap-1.5 text-muted-foreground text-sm">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading users…
                  </span>
                ) : (
                  <SelectValue placeholder="Select a user…" />
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
                    Enter new ID…
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
            />
            {knownUsers.length > 0 && (
              <Button variant="ghost" size="icon" onClick={() => setMode("select")} title="Pick from list">
                <ChevronDown className="h-4 w-4" />
              </Button>
            )}
          </div>
        )}

        {withButton && (
          <Button onClick={handleConfirm} disabled={!localId || loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : buttonLabel}
          </Button>
        )}
      </div>
    </div>
  );
}
