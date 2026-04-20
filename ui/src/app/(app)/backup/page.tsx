"use client";

/**
 * Backup / Restore
 *
 * 每用户粒度的 JSON 备份：Mem0 conversations + Memobase profile topics
 * + 可选 Cognee 数据集（原文快照）。
 *
 * 下载 = GET /backup/export/{userId}?datasets=<ids> 直接写文件。
 * 上传 = 读 JSON → POST /backup/import，显示导入计数。
 */

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { UserSelector } from "@/components/user-selector";
import { getApiKey } from "@/lib/store";
import { knowledgeApi, type KnowledgeDataset } from "@/lib/api";
import { Download, Upload, Loader2, CheckCircle2, XCircle, Database } from "lucide-react";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface MemoryBundle {
  version: string;
  exported_at: string;
  user_id: string;
  conversations: { id: string; content: string }[];
  profile_topics: { id: string; topic: string; sub_topic: string; content: string }[];
  datasets?: { name: string; documents: string[] }[];
}

interface ImportResult {
  success: boolean;
  user_id: string;
  conversations_imported: number;
  conversations_skipped: number;
  profiles_imported: number;
  profiles_skipped: number;
  datasets_imported?: number;
  documents_imported?: number;
  datasets_skipped?: number;
  errors: { kind: string; id: string; reason: string }[];
}

function authHeaders(): Record<string, string> {
  const k = getApiKey();
  return k ? { "X-Cozy-API-Key": k } : {};
}

export default function BackupPage() {
  const [exportUserId, setExportUserId] = useState("");
  const [targetUserId, setTargetUserId] = useState("");
  const [exporting, setExporting] = useState(false);
  const [exportErr, setExportErr] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [importErr, setImportErr] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [previewBundle, setPreviewBundle] = useState<MemoryBundle | null>(null);
  const [datasets, setDatasets] = useState<KnowledgeDataset[]>([]);
  const [selectedDs, setSelectedDs] = useState<Set<string>>(new Set());

  useEffect(() => {
    knowledgeApi
      .listDatasets()
      .then((r) => setDatasets(r.data ?? []))
      .catch(() => setDatasets([]));
  }, []);

  function toggleDs(id: string) {
    setSelectedDs((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleDownload() {
    if (!exportUserId) return;
    setExporting(true);
    setExportErr(null);
    try {
      const dsQuery = selectedDs.size > 0 ? `?datasets=${[...selectedDs].join(",")}` : "";
      const resp = await fetch(
        `${BASE_URL}/api/v1/backup/export/${encodeURIComponent(exportUserId)}${dsQuery}`,
        { headers: authHeaders() }
      );
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.detail?.detail ?? body.detail ?? body.error ?? `HTTP ${resp.status}`);
      }
      const bundle = (await resp.json()) as MemoryBundle;
      // 写文件
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `cozymemory-${bundle.user_id}-${new Date(bundle.exported_at).toISOString().slice(0, 19).replaceAll(":", "")}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setExportErr((e as Error).message);
    } finally {
      setExporting(false);
    }
  }

  async function handleFilePick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // 允许同名文件重选触发 onChange
    if (!file) return;
    setImportErr(null);
    setImportResult(null);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as MemoryBundle;
      if (!parsed.version || !parsed.user_id) {
        throw new Error("Invalid bundle: missing version or user_id");
      }
      setPreviewBundle(parsed);
    } catch (e) {
      setImportErr((e as Error).message);
    }
  }

  async function handleImport() {
    if (!previewBundle) return;
    setImporting(true);
    setImportErr(null);
    try {
      const resp = await fetch(`${BASE_URL}/api/v1/backup/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          bundle: previewBundle,
          target_user_id: targetUserId || null,
        }),
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.detail ?? body.error ?? `HTTP ${resp.status}`);
      }
      const result = (await resp.json()) as ImportResult;
      setImportResult(result);
      setPreviewBundle(null); // 导入完清预览，防止重复提交
    } catch (e) {
      setImportErr((e as Error).message);
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">Backup</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Export a user&apos;s Mem0 memories + Memobase profile as a portable JSON bundle. Use
          import to restore into the same or a different user.
        </p>
      </div>

      {/* Export */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Download className="h-4 w-4" /> Export
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <UserSelector
            label="User to export"
            onConfirm={setExportUserId}
            buttonLabel="Select"
          />
          {exportUserId && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              Selected: <code className="font-mono">{exportUserId}</code>
            </div>
          )}

          {datasets.length > 0 && (
            <div className="space-y-1.5">
              <Label className="text-xs flex items-center gap-1.5">
                <Database className="h-3.5 w-3.5" /> Include Cognee datasets (optional)
              </Label>
              <div className="flex flex-wrap gap-1.5 max-h-40 overflow-auto rounded-md border p-2">
                {datasets.map((d) => (
                  <label
                    key={d.id}
                    className="flex items-center gap-1.5 text-xs cursor-pointer rounded px-1.5 py-0.5 hover:bg-muted"
                  >
                    <input
                      type="checkbox"
                      checked={selectedDs.has(d.id)}
                      onChange={() => toggleDs(d.id)}
                    />
                    <span>{d.name}</span>
                  </label>
                ))}
              </div>
              <p className="text-[11px] text-muted-foreground">
                Selected: {selectedDs.size} / {datasets.length}. Datasets are global, not tied to
                the user — checked ones will be embedded in this bundle.
              </p>
            </div>
          )}

          <Button onClick={handleDownload} disabled={!exportUserId || exporting}>
            {exporting ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Download className="h-4 w-4 mr-2" />
            )}
            Download bundle
          </Button>
          {exportErr && <p className="text-xs text-destructive">{exportErr}</p>}
        </CardContent>
      </Card>

      {/* Import */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Upload className="h-4 w-4" /> Import
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="bundle-file">JSON bundle file</Label>
            <Input
              id="bundle-file"
              type="file"
              accept="application/json,.json"
              onChange={handleFilePick}
              disabled={importing}
            />
          </div>

          {previewBundle && (
            <div className="rounded-md border p-3 space-y-2 text-xs">
              <p className="font-medium">Bundle preview</p>
              <div className="flex flex-wrap gap-1.5">
                <Badge variant="outline">v{previewBundle.version}</Badge>
                <Badge variant="secondary">
                  from {previewBundle.user_id.slice(0, 12)}…
                </Badge>
                <Badge variant="secondary">
                  {previewBundle.conversations.length} memories
                </Badge>
                <Badge variant="secondary">
                  {previewBundle.profile_topics.length} profile topics
                </Badge>
                {previewBundle.datasets && previewBundle.datasets.length > 0 && (
                  <Badge variant="secondary">
                    {previewBundle.datasets.length} datasets · {previewBundle.datasets.reduce((n, d) => n + d.documents.length, 0)} docs
                  </Badge>
                )}
                <Badge variant="outline">
                  {new Date(previewBundle.exported_at).toLocaleString()}
                </Badge>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="target-id" className="text-xs">
                  Target user ID (leave empty to restore into the original {previewBundle.user_id.slice(0, 8)}…)
                </Label>
                <Input
                  id="target-id"
                  placeholder={previewBundle.user_id}
                  value={targetUserId}
                  onChange={(e) => setTargetUserId(e.target.value)}
                />
              </div>

              <Button onClick={handleImport} disabled={importing}>
                {importing ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Upload className="h-4 w-4 mr-2" />
                )}
                Import into {targetUserId || previewBundle.user_id.slice(0, 8) + "…"}
              </Button>
            </div>
          )}

          {importErr && (
            <p className="text-xs text-destructive flex items-center gap-1">
              <XCircle className="h-3.5 w-3.5" /> {importErr}
            </p>
          )}
          {importResult && (
            <div className="rounded-md border border-green-500/30 bg-green-500/5 p-3 space-y-1 text-xs">
              <p className="flex items-center gap-1 text-green-700 dark:text-green-400">
                <CheckCircle2 className="h-3.5 w-3.5" /> Imported into{" "}
                <code className="font-mono">{importResult.user_id}</code>
              </p>
              <p>
                Conversations: {importResult.conversations_imported} imported,{" "}
                {importResult.conversations_skipped} skipped
              </p>
              <p>
                Profiles: {importResult.profiles_imported} imported,{" "}
                {importResult.profiles_skipped} skipped
              </p>
              {(importResult.datasets_imported ?? 0) + (importResult.documents_imported ?? 0) > 0 && (
                <p>
                  Datasets: {importResult.datasets_imported ?? 0} imported ·{" "}
                  {importResult.documents_imported ?? 0} docs · cognify queued
                </p>
              )}
              {importResult.errors.length > 0 && (
                <details>
                  <summary className="cursor-pointer text-destructive">
                    {importResult.errors.length} errors
                  </summary>
                  <ul className="list-disc pl-5 mt-1">
                    {importResult.errors.slice(0, 10).map((e, i) => (
                      <li key={i}>
                        [{e.kind}] {e.id}: {e.reason}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            <strong>Note:</strong> Mem0 doesn&apos;t retain original messages, only extracted
            facts. On import, each fact is replayed as a user message so Mem0 re-extracts —
            results may differ slightly from the source. Memobase profiles restore exactly.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
