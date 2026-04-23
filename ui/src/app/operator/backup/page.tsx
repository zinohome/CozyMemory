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
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { UserSelector } from "@/components/user-selector";
import { operatorApi, type KnowledgeDataset } from "@/lib/api";
import { toast } from "sonner";
import { Download, Upload, Loader2, CheckCircle2, Database } from "lucide-react";
import { useT } from "@/lib/i18n";

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

export default function BackupPage() {
  const t = useT();
  const [exportUserId, setExportUserId] = useState("");
  const [targetUserId, setTargetUserId] = useState("");
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [previewBundle, setPreviewBundle] = useState<MemoryBundle | null>(null);
  const [datasets, setDatasets] = useState<KnowledgeDataset[]>([]);
  const [selectedDs, setSelectedDs] = useState<Set<string>>(new Set());

  useEffect(() => {
    operatorApi
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

  const exportMutation = useMutation({
    mutationFn: async () => {
      if (!exportUserId) throw new Error(t("backup.error.pickUser"));
      const dsIds = selectedDs.size > 0 ? [...selectedDs] : undefined;
      return (await operatorApi.exportUser(exportUserId, dsIds)) as MemoryBundle;
    },
    onSuccess: (bundle) => {
      // 浏览器端写文件
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `cozymemory-${bundle.user_id}-${new Date(bundle.exported_at).toISOString().slice(0, 19).replaceAll(":", "")}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success(t("backup.export.countToast", { n: bundle.conversations.length + (bundle.profile_topics?.length ?? 0) }));
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const importMutation = useMutation({
    mutationFn: async (bundle: MemoryBundle) =>
      (await operatorApi.importBackup({
        bundle,
        target_user_id: targetUserId || null,
      })) as ImportResult,
    onSuccess: (result) => {
      setImportResult(result);
      setPreviewBundle(null); // 导入完清预览，防止重复提交
      toast.success(t("backup.import.successToast"));
    },
    onError: (e) => toast.error((e as Error).message),
  });

  async function handleFilePick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // 允许同名文件重选触发 onChange
    if (!file) return;
    setImportResult(null);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as MemoryBundle;
      if (!parsed.version || !parsed.user_id) {
        throw new Error(t("backup.error.invalidBundle"));
      }
      setPreviewBundle(parsed);
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  const exporting = exportMutation.isPending;
  const importing = importMutation.isPending;
  const handleDownload = () => exportMutation.mutate();
  const handleImport = () => {
    if (previewBundle) importMutation.mutate(previewBundle);
  };

  return (
    <div className="space-y-4 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">{t("backup.title")}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          {t("backup.page.subtitle")}
        </p>
      </div>

      {/* Export */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Download className="h-4 w-4" /> {t("backup.export.title")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <UserSelector
            label={t("backup.user.select")}
            onConfirm={setExportUserId}
            buttonLabel={t("backup.user.confirmBtn")}
          />
          {exportUserId && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {t("backup.user.chosen")} <code className="font-mono">{exportUserId}</code>
            </div>
          )}

          {datasets.length > 0 && (
            <div className="space-y-1.5">
              <Label className="text-xs flex items-center gap-1.5">
                <Database className="h-3.5 w-3.5" /> {t("backup.datasets.label")}
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
                {t("backup.datasets.hint", { n: selectedDs.size, total: datasets.length })}
              </p>
            </div>
          )}

          <Button onClick={handleDownload} disabled={!exportUserId || exporting}>
            {exporting ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Download className="h-4 w-4 mr-2" />
            )}
            {t("backup.download")}
          </Button>
        </CardContent>
      </Card>

      {/* Import */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Upload className="h-4 w-4" /> {t("backup.import.title")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="bundle-file">{t("backup.file.label")}</Label>
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
              <p className="font-medium">{t("backup.preview.title")}</p>
              <div className="flex flex-wrap gap-1.5">
                <Badge variant="outline">v{previewBundle.version}</Badge>
                <Badge variant="secondary">
                  {t("backup.preview.from", { id: previewBundle.user_id.slice(0, 12) })}
                </Badge>
                <Badge variant="secondary">
                  {t("backup.preview.memories", { n: previewBundle.conversations.length })}
                </Badge>
                <Badge variant="secondary">
                  {t("backup.preview.profileTopics", { n: previewBundle.profile_topics.length })}
                </Badge>
                {previewBundle.datasets && previewBundle.datasets.length > 0 && (
                  <Badge variant="secondary">
                    {t("backup.preview.datasets", {
                      n: previewBundle.datasets.length,
                      docs: previewBundle.datasets.reduce((n, d) => n + d.documents.length, 0),
                    })}
                  </Badge>
                )}
                <Badge variant="outline">
                  {new Date(previewBundle.exported_at).toLocaleString()}
                </Badge>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="target-id" className="text-xs">
                  {t("backup.target.label", { id: previewBundle.user_id.slice(0, 8) })}
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
                {t("backup.import.target.btn", {
                  id: targetUserId || previewBundle.user_id.slice(0, 8) + "…",
                })}
              </Button>
            </div>
          )}

          {importResult && (
            <div className="rounded-md border border-green-500/30 bg-green-500/5 p-3 space-y-1 text-xs">
              <p className="flex items-center gap-1 text-green-700 dark:text-green-400">
                <CheckCircle2 className="h-3.5 w-3.5" /> {t("backup.result.importedInto")}{" "}
                <code className="font-mono">{importResult.user_id}</code>
              </p>
              <p>
                {t("backup.result.convs", {
                  imp: importResult.conversations_imported,
                  skip: importResult.conversations_skipped,
                })}
              </p>
              <p>
                {t("backup.result.profiles", {
                  imp: importResult.profiles_imported,
                  skip: importResult.profiles_skipped,
                })}
              </p>
              {(importResult.datasets_imported ?? 0) + (importResult.documents_imported ?? 0) > 0 && (
                <p>
                  {t("backup.result.datasets", {
                    ds: importResult.datasets_imported ?? 0,
                    docs: importResult.documents_imported ?? 0,
                  })}
                </p>
              )}
              {importResult.errors.length > 0 && (
                <details>
                  <summary className="cursor-pointer text-destructive">
                    {t("backup.result.errors", { n: importResult.errors.length })}
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
            {t("backup.note")}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
