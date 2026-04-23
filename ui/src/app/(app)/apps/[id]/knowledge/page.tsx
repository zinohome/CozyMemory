"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { knowledgeApi, type KnowledgeDataset } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, RefreshCw, Search, Plus, GitBranch, Network, Trash2, Upload, FileText, Eye, Download } from "lucide-react";
import { KnowledgeGraph } from "@/components/knowledge-graph";
import { ConfirmDialog } from "@/components/confirm-dialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useT } from "@/lib/i18n";
import type { DatasetDataItem } from "@/lib/api";

// ── Dataset row with inline delete confirm ────────────────────────────────

function DatasetRow({
  ds,
  selected,
  onClick,
  onDelete,
  isDeleting,
}: {
  ds: KnowledgeDataset;
  selected: boolean;
  onClick: () => void;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  const t = useT();
  const [confirming, setConfirming] = useState(false);

  return (
    <div
      className={`group flex items-center gap-1 rounded-md border transition-colors min-w-0 ${
        selected ? "bg-primary/10 border-primary" : "hover:bg-muted"
      }`}
    >
      {/* Clickable name area */}
      <button
        onClick={onClick}
        className="flex-1 text-left px-3 py-2 text-sm min-w-0"
      >
        <p className="font-medium truncate">{ds.name}</p>
        <p className="text-xs text-muted-foreground font-mono truncate">{ds.id}</p>
      </button>

      {/* Delete / confirm */}
      <div className="px-1.5 shrink-0">
        {isDeleting ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
        ) : confirming ? (
          <span className="flex items-center gap-1">
            <Button
              size="sm"
              variant="destructive"
              className="h-6 px-2 text-xs"
              onClick={(e) => { e.stopPropagation(); setConfirming(false); onDelete(); }}
            >
              {t("common.yes")}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-6 px-2 text-xs"
              onClick={(e) => { e.stopPropagation(); setConfirming(false); }}
            >
              {t("common.no")}
            </Button>
          </span>
        ) : (
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 opacity-0 group-hover:opacity-60 hover:!opacity-100 transition-opacity"
            title={t("knowledge.dataset.deleteHint")}
            aria-label={t("knowledge.dataset.deleteAria", { name: ds.name })}
            onClick={(e) => { e.stopPropagation(); setConfirming(true); }}
          >
            <Trash2 className="h-3.5 w-3.5 text-destructive" />
          </Button>
        )}
      </div>
    </div>
  );
}

/**
 * DocumentPreviewDialog — 点"查看"弹出的预览框。
 *   - 文本类文件（content-type 以 text/ 开头）：直接 fetch 内容展示
 *   - 非文本（PDF/图片/doc 等）：提示用户改用下载
 */
function DocumentPreviewDialog({
  doc,
  datasetId,
  onClose,
}: {
  doc: DatasetDataItem | null;
  datasetId: string | undefined;
  onClose: () => void;
}) {
  const t = useT();
  const isText = (doc?.mime_type ?? "").startsWith("text/") ||
    ["txt", "md", "markdown", "log", "csv", "json", "yaml", "yml"].includes(
      (doc?.extension ?? "").toLowerCase()
    );

  const preview = useQuery({
    queryKey: ["doc-raw", datasetId, doc?.id],
    queryFn: () => knowledgeApi.fetchRawText(datasetId!, doc!.id),
    enabled: !!doc && !!datasetId && isText,
    staleTime: Infinity,
  });

  return (
    <Dialog open={!!doc} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-auto">
        <DialogHeader>
          <DialogTitle>
            {t("knowledge.docs.previewTitle", { name: doc?.name ?? "" })}
          </DialogTitle>
        </DialogHeader>
        {!isText && doc && (
          <div className="py-6 text-sm text-muted-foreground text-center space-y-3">
            <p>{t("knowledge.docs.previewBinary")}</p>
            {datasetId && (
              <a
                href={knowledgeApi.rawDataUrl(datasetId, doc.id)}
                download={doc.name || doc.id}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-primary hover:underline"
              >
                <Download className="h-4 w-4" />
                {t("knowledge.docs.download")}
              </a>
            )}
          </div>
        )}
        {isText && preview.isLoading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
            <Loader2 className="h-4 w-4 animate-spin" />
            {t("knowledge.docs.previewLoading")}
          </div>
        )}
        {isText && preview.isError && (
          <p className="text-sm text-destructive py-4">
            {t("knowledge.docs.previewError", {
              msg: (preview.error as Error)?.message ?? "",
            })}
          </p>
        )}
        {isText && preview.data !== undefined && (
          <pre className="whitespace-pre-wrap font-mono text-xs bg-muted rounded p-3 overflow-auto">
            {preview.data}
          </pre>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function KnowledgePage() {
  const t = useT();
  const qc = useQueryClient();
  const [selectedDataset, setSelectedDataset] = useState<KnowledgeDataset | null>(null);
  const [addText, setAddText] = useState("");
  const [newDatasetName, setNewDatasetName] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  type SearchType = "CHUNKS" | "SUMMARIES" | "RAG_COMPLETION" | "GRAPH_COMPLETION";
  const [searchType, setSearchType] = useState<SearchType>("GRAPH_COMPLETION");
  const [cognifyJobId, setCognifyJobId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("add");
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: string; name: string } | null>(null);
  const [datasetFilter, setDatasetFilter] = useState("");
  const [addMode, setAddMode] = useState<"text" | "file">("text");
  const [pickedFiles, setPickedFiles] = useState<File[]>([]);
  const [previewDoc, setPreviewDoc] = useState<DatasetDataItem | null>(null);
  const [docDeleteConfirm, setDocDeleteConfirm] = useState<DatasetDataItem | null>(null);

  const datasetsQuery = useQuery({
    queryKey: ["datasets"],
    queryFn: knowledgeApi.listDatasets,
  });

  const graphQuery = useQuery({
    queryKey: ["graph", selectedDataset?.id],
    queryFn: () => knowledgeApi.getGraph(selectedDataset!.id),
    enabled: !!selectedDataset && activeTab === "graph",
    staleTime: 60_000,
  });

  const cognifyStatusQuery = useQuery({
    queryKey: ["cognify-status", cognifyJobId],
    queryFn: () => knowledgeApi.getCognifyStatus(cognifyJobId!),
    enabled: !!cognifyJobId,
    refetchInterval: (query) => {
      // Stop polling on network/server error so we don't loop indefinitely
      if (query.state.status === "error") return false;
      const status = query.state.data?.status;
      return status === "running" || status === "pending" ? 3000 : false;
    },
  });

  const filteredDatasets = useMemo(() => {
    const all = datasetsQuery.data?.data ?? [];
    const q = datasetFilter.trim().toLowerCase();
    if (!q) return all;
    return all.filter((d) => d.name.toLowerCase().includes(q));
  }, [datasetsQuery.data, datasetFilter]);

  const deleteDatasetMutation = useMutation({
    mutationFn: (datasetId: string) => knowledgeApi.deleteDataset(datasetId),
    // Optimistic delete: 立即从列表移除 + 清除依赖查询 + 失败回滚
    onMutate: async (datasetId) => {
      await qc.cancelQueries({ queryKey: ["datasets"] });
      const previous = qc.getQueryData<typeof datasetsQuery.data>(["datasets"]);
      qc.setQueryData<typeof datasetsQuery.data>(["datasets"], (old) => {
        if (!old) return old;
        return { ...old, data: (old.data ?? []).filter((d) => d.id !== datasetId) };
      });
      if (selectedDataset?.id === datasetId) {
        setSelectedDataset(null);
        setActiveTab("add");
      }
      return { previous };
    },
    onError: (e, _id, ctx) => {
      if (ctx?.previous) qc.setQueryData(["datasets"], ctx.previous);
      toast.error((e as Error).message);
    },
    onSuccess: (_, datasetId) => {
      qc.removeQueries({ queryKey: ["graph", datasetId] });
      toast.success(t("knowledge.toast.datasetDeleted"));
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["datasets"] }),
  });

  const createDatasetMutation = useMutation({
    mutationFn: (name: string) => knowledgeApi.createDataset(name),
    onSuccess: (_, name) => {
      qc.invalidateQueries({ queryKey: ["datasets"] });
      setNewDatasetName("");
      toast.success(`Dataset "${name}" created`);
    },
    onError: (e) => toast.error((e as Error).message),
  });

  function handleCreateDataset() {
    const name = newDatasetName.trim();
    if (name) createDatasetMutation.mutate(name);
  }

  const addMutation = useMutation({
    mutationFn: () => knowledgeApi.add(addText, selectedDataset?.name ?? "default"),
    onSuccess: () => {
      setAddText("");
      toast.success(t("knowledge.toast.added"));
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const uploadMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.addFiles(selectedDataset?.name ?? "default", pickedFiles),
    onSuccess: (_, __) => {
      toast.success(
        t("knowledge.add.uploadSuccess", { n: pickedFiles.length })
      );
      setPickedFiles([]);
      qc.invalidateQueries({ queryKey: ["dataset-data", selectedDataset?.id] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const dataListQuery = useQuery({
    queryKey: ["dataset-data", selectedDataset?.id],
    queryFn: () => knowledgeApi.listData(selectedDataset!.id),
    enabled: !!selectedDataset && activeTab === "docs",
    staleTime: 30_000,
  });

  const deleteDocMutation = useMutation({
    mutationFn: (doc: DatasetDataItem) =>
      knowledgeApi.deleteData(selectedDataset!.id, doc.id),
    onMutate: async (doc) => {
      await qc.cancelQueries({ queryKey: ["dataset-data", selectedDataset?.id] });
      const previous = qc.getQueryData<typeof dataListQuery.data>([
        "dataset-data",
        selectedDataset?.id,
      ]);
      qc.setQueryData<typeof dataListQuery.data>(
        ["dataset-data", selectedDataset?.id],
        (old) => {
          if (!old) return old;
          return {
            ...old,
            data: (old.data ?? []).filter((d) => d.id !== doc.id),
            total: Math.max(0, (old.total ?? 0) - 1),
          };
        }
      );
      return { previous };
    },
    onError: (e, _doc, ctx) => {
      if (ctx?.previous) {
        qc.setQueryData(["dataset-data", selectedDataset?.id], ctx.previous);
      }
      toast.error((e as Error).message);
    },
    onSuccess: () => toast.success(t("knowledge.docs.deletedToast")),
    onSettled: () =>
      qc.invalidateQueries({ queryKey: ["dataset-data", selectedDataset?.id] }),
  });

  const cognifyMutation = useMutation({
    mutationFn: () => knowledgeApi.cognify(selectedDataset ? [selectedDataset.name] : undefined),
    onSuccess: (data) => {
      if (data.pipeline_run_id) setCognifyJobId(data.pipeline_run_id);
      toast.info(t("knowledge.toast.cognifyStarted"));
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const searchMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.search({
        query: searchQuery,
        dataset: selectedDataset?.name, // use name (not id/UUID) — consistent with add/cognify
        search_type: searchType,
        top_k: 10,
      }),
    onError: (e) => toast.error((e as Error).message),
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">{t("knowledge.title")}</h1>
        <p className="text-muted-foreground text-sm mt-1">{t("knowledge.subtitle")}</p>
      </div>

      <div className="grid lg:grid-cols-[240px_1fr] gap-4 min-w-0">
        {/* ── Dataset list ── */}
        <div className="space-y-2 min-w-0">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">{t("knowledge.datasets")}</p>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              aria-label={t("knowledge.dataset.refreshAria")}
              title={t("knowledge.dataset.refreshTitle")}
              onClick={() => qc.invalidateQueries({ queryKey: ["datasets"] })}
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </div>
          <Input
            placeholder={t("knowledge.dataset.filter")}
            value={datasetFilter}
            onChange={(e) => setDatasetFilter(e.target.value)}
            className="h-8 text-xs"
          />
          <ScrollArea className="h-72">
            <div className="space-y-1 pr-2">
              {filteredDatasets.map((ds) => (
                <DatasetRow
                  key={ds.id}
                  ds={ds}
                  selected={selectedDataset?.id === ds.id}
                  onClick={() => setSelectedDataset(ds)}
                  onDelete={() => setDeleteConfirm({ id: ds.id, name: ds.name })}
                  isDeleting={deleteDatasetMutation.isPending && deleteDatasetMutation.variables === ds.id}
                />
              ))}
              {datasetsQuery.isLoading && <Loader2 className="h-4 w-4 animate-spin mx-auto mt-4" />}
              {!datasetsQuery.isLoading && filteredDatasets.length === 0 && (
                <p className="text-xs text-muted-foreground text-center py-4">
                  {datasetFilter
                    ? t("knowledge.dataset.noMatch", { q: datasetFilter })
                    : t("knowledge.dataset.none")}
                </p>
              )}
            </div>
          </ScrollArea>
          <div className="flex gap-1 min-w-0">
            <Input
              placeholder={t("knowledge.dataset.newName")}
              id="new-ds"
              className="text-xs h-8 min-w-0 flex-1"
              value={newDatasetName}
              onChange={(e) => setNewDatasetName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreateDataset()}
              disabled={createDatasetMutation.isPending}
            />
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8 shrink-0"
              aria-label={t("knowledge.dataset.createAria")}
              title={t("knowledge.dataset.createTitle")}
              onClick={handleCreateDataset}
              disabled={!newDatasetName.trim() || createDatasetMutation.isPending}
            >
              {createDatasetMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Plus className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>
          {createDatasetMutation.isError && (
            <p className="text-xs text-destructive">{String(createDatasetMutation.error)}</p>
          )}
        </div>

        {/* ── Main panel ── */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="add">{t("knowledge.add.tab")}</TabsTrigger>
            <TabsTrigger value="docs" disabled={!selectedDataset} className="gap-1.5">
              <FileText className="h-3.5 w-3.5" />
              {t("knowledge.docs.tab")}
            </TabsTrigger>
            <TabsTrigger value="search">{t("knowledge.tab.search")}</TabsTrigger>
            <TabsTrigger value="cognify">{t("knowledge.cognify.tab")}</TabsTrigger>
            <TabsTrigger value="graph" disabled={!selectedDataset} className="gap-1.5">
              <Network className="h-3.5 w-3.5" />
              {t("knowledge.graph.tab")}
            </TabsTrigger>
          </TabsList>

          {/* ─ Add ─ */}
          <TabsContent value="add" className="space-y-3 mt-3">
            <div className="space-y-1.5">
              <Label>{t("knowledge.add.dataset")}</Label>
              <p className="text-sm text-muted-foreground">
                {selectedDataset ? selectedDataset.name : <span className="italic">{t("knowledge.add.noDatasetLabel")}</span>}
              </p>
            </div>

            <div className="inline-flex rounded-md border text-xs overflow-hidden">
              <button
                onClick={() => setAddMode("text")}
                className={
                  (addMode === "text"
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-muted") + " px-3 py-1.5"
                }
              >
                {t("knowledge.add.methodText")}
              </button>
              <button
                onClick={() => setAddMode("file")}
                className={
                  (addMode === "file"
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-muted") + " px-3 py-1.5 border-l"
                }
              >
                {t("knowledge.add.methodFile")}
              </button>
            </div>

            {addMode === "text" ? (
              <>
                <Textarea
                  rows={5}
                  placeholder={t("knowledge.add.placeholderNew")}
                  value={addText}
                  onChange={(e) => setAddText(e.target.value)}
                />
                <Button onClick={() => addMutation.mutate()} disabled={!addText || addMutation.isPending}>
                  {addMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4 mr-2" />
                  )}
                  {t("knowledge.add.button")}
                </Button>
                {addMutation.isSuccess && (
                  <p className="text-xs text-green-600 dark:text-green-400">
                    {t("knowledge.add.success", { id: addMutation.data?.data_id ?? "" })}
                  </p>
                )}
              </>
            ) : (
              <>
                <div className="space-y-1.5">
                  <Input
                    type="file"
                    multiple
                    onChange={(e) => setPickedFiles(Array.from(e.target.files ?? []))}
                    className="cursor-pointer"
                  />
                  <p className="text-[11px] text-muted-foreground">
                    {t("knowledge.add.filePickerHint")}
                  </p>
                  {pickedFiles.length > 0 && (
                    <p className="text-xs">
                      {t("knowledge.add.filesSelected", { n: pickedFiles.length })}
                    </p>
                  )}
                </div>
                <Button
                  onClick={() => uploadMutation.mutate()}
                  disabled={
                    pickedFiles.length === 0 ||
                    uploadMutation.isPending ||
                    !selectedDataset
                  }
                >
                  {uploadMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Upload className="h-4 w-4 mr-2" />
                  )}
                  {t("knowledge.add.uploadBtn")}
                </Button>
                {!selectedDataset && (
                  <p className="text-xs text-amber-700 dark:text-amber-300">
                    {t("knowledge.add.pickDatasetFirst")}
                  </p>
                )}
              </>
            )}
          </TabsContent>

          {/* ─ Documents ─ */}
          <TabsContent value="docs" className="space-y-3 mt-3">
            {!selectedDataset ? (
              <p className="text-sm text-muted-foreground">
                {t("knowledge.docs.pickDataset")}
              </p>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">
                    {t("knowledge.docs.count", {
                      n: dataListQuery.data?.total ?? 0,
                    })}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      qc.invalidateQueries({
                        queryKey: ["dataset-data", selectedDataset.id],
                      })
                    }
                    disabled={dataListQuery.isFetching}
                  >
                    {dataListQuery.isFetching ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <RefreshCw className="h-3.5 w-3.5" />
                    )}
                    <span className="ml-1.5">{t("knowledge.docs.refresh")}</span>
                  </Button>
                </div>

                {dataListQuery.isLoading && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t("knowledge.docs.loading")}
                  </div>
                )}

                {dataListQuery.data && (dataListQuery.data.data ?? []).length === 0 && (
                  <p className="text-sm text-muted-foreground py-4 text-center">
                    {t("knowledge.docs.empty")}
                  </p>
                )}

                {dataListQuery.data && (dataListQuery.data.data ?? []).length > 0 && (
                  <div className="rounded-md border overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="text-left px-3 py-2 font-medium text-xs text-foreground">
                            {t("knowledge.docs.col.name")}
                          </th>
                          <th className="text-left px-3 py-2 font-medium text-xs text-foreground hidden sm:table-cell">
                            {t("knowledge.docs.col.type")}
                          </th>
                          <th className="text-right px-3 py-2 font-medium text-xs text-foreground hidden md:table-cell">
                            {t("knowledge.docs.col.created")}
                          </th>
                          <th className="px-3 py-2 w-28">
                            <span className="sr-only">
                              {t("knowledge.docs.col.actions")}
                            </span>
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {(dataListQuery.data.data ?? []).map((d) => (
                          <tr
                            key={d.id}
                            className="border-t hover:bg-muted/30 transition-colors"
                          >
                            <td className="px-3 py-2">
                              <div className="flex items-center gap-2 min-w-0">
                                <FileText className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                                <span className="truncate" title={d.name || d.id}>
                                  {d.name || d.id.slice(0, 8)}
                                </span>
                              </div>
                            </td>
                            <td className="px-3 py-2 text-xs text-muted-foreground hidden sm:table-cell">
                              {d.extension ?? d.mime_type ?? "—"}
                            </td>
                            <td className="px-3 py-2 text-right text-xs text-muted-foreground hidden md:table-cell">
                              {d.created_at
                                ? new Date(d.created_at).toLocaleString()
                                : "—"}
                            </td>
                            <td className="px-3 py-2 text-right">
                              <div className="flex items-center justify-end gap-0.5">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-7 w-7"
                                  title={t("knowledge.docs.view")}
                                  aria-label={t("knowledge.docs.viewAria", {
                                    name: d.name || d.id,
                                  })}
                                  onClick={() => setPreviewDoc(d)}
                                >
                                  <Eye className="h-3.5 w-3.5" />
                                </Button>
                                <a
                                  href={knowledgeApi.rawDataUrl(
                                    selectedDataset.id,
                                    d.id
                                  )}
                                  download={d.name || d.id}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted"
                                  title={t("knowledge.docs.download")}
                                  aria-label={t("knowledge.docs.downloadAria", {
                                    name: d.name || d.id,
                                  })}
                                >
                                  <Download className="h-3.5 w-3.5" />
                                </a>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-7 w-7"
                                  title={t("knowledge.docs.delete")}
                                  aria-label={t("knowledge.docs.deleteAria", {
                                    name: d.name || d.id,
                                  })}
                                  onClick={() => setDocDeleteConfirm(d)}
                                >
                                  <Trash2 className="h-3.5 w-3.5 text-destructive" />
                                </Button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </TabsContent>

          {/* ─ Search ─ */}
          <TabsContent value="search" className="space-y-3 mt-3">
            <div className="flex gap-2">
              <Input
                placeholder={t("knowledge.search.placeholderNew")}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && searchMutation.mutate()}
              />
              <Select
                value={searchType}
                onValueChange={(v) => setSearchType((v as SearchType) ?? "GRAPH_COMPLETION")}
              >
                <SelectTrigger className="w-44" aria-label={t("knowledge.search.type.aria")}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CHUNKS">{t("knowledge.search.type.CHUNKS")}</SelectItem>
                  <SelectItem value="SUMMARIES">{t("knowledge.search.type.SUMMARIES")}</SelectItem>
                  <SelectItem value="RAG_COMPLETION">{t("knowledge.search.type.RAG_COMPLETION")}</SelectItem>
                  <SelectItem value="GRAPH_COMPLETION">{t("knowledge.search.type.GRAPH_COMPLETION")}</SelectItem>
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                onClick={() => searchMutation.mutate()}
                disabled={!searchQuery || searchMutation.isPending}
              >
                {searchMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
              </Button>
            </div>
            <ScrollArea className="h-72">
              <div className="space-y-2 pr-2">
                {searchMutation.data?.data?.map((item, i) => (
                  <div key={String(item.id ?? i)} className="rounded-md border p-3 text-sm space-y-1">
                    <p>{item.text ?? JSON.stringify(item)}</p>
                    {item.score != null && (
                      <span className="text-xs text-muted-foreground">
                        score: {(item.score as number).toFixed(3)}
                      </span>
                    )}
                  </div>
                ))}
                {searchMutation.isSuccess && searchMutation.data?.data?.length === 0 && (
                  <p className="text-sm text-muted-foreground">{t("knowledge.search.empty")}</p>
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          {/* ─ Cognify ─ */}
          <TabsContent value="cognify" className="space-y-3 mt-3">
            <p className="text-sm text-muted-foreground">
              {t("knowledge.cognify.desc", {
                dataset: selectedDataset?.name ?? t("knowledge.cognify.allDatasets"),
              })}
            </p>
            <Button onClick={() => cognifyMutation.mutate()} disabled={cognifyMutation.isPending}>
              {cognifyMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <GitBranch className="h-4 w-4 mr-2" />
              )}
              {t("knowledge.cognify.start")}
            </Button>

            {cognifyJobId && (
              <Card>
                <CardContent className="pt-3 pb-3 text-sm space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground text-xs">{t("knowledge.cognify.jobId")}</span>
                    <span className="font-mono text-xs">{cognifyJobId}</span>
                  </div>
                  {cognifyStatusQuery.data && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground text-xs">{t("knowledge.cognify.status")}</span>
                      <Badge
                        variant={
                          cognifyStatusQuery.data.status === "completed"
                            ? "default"
                            : cognifyStatusQuery.data.status === "failed"
                              ? "destructive"
                              : "secondary"
                        }
                      >
                        {cognifyStatusQuery.data.status}
                      </Badge>
                      {(cognifyStatusQuery.data.status === "running" ||
                        cognifyStatusQuery.data.status === "pending") && (
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                      )}
                      {cognifyStatusQuery.data.status === "completed" && (
                        <Button
                          variant="link"
                          size="sm"
                          className="h-auto p-0 text-xs"
                          onClick={() => setActiveTab("graph")}
                        >
                          {t("knowledge.cognify.viewGraph")}
                        </Button>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* ─ Graph ─ */}
          <TabsContent value="graph" className="mt-3 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm text-muted-foreground min-w-0 truncate">
                {t("knowledge.graph.dataset")} <strong>{selectedDataset?.name}</strong>
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => qc.invalidateQueries({ queryKey: ["graph", selectedDataset?.id] })}
                disabled={graphQuery.isFetching}
                className="shrink-0"
              >
                {graphQuery.isFetching ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="h-3.5 w-3.5" />
                )}
                <span className="ml-1.5">{t("knowledge.graph.refresh")}</span>
              </Button>
            </div>

            {graphQuery.isFetching && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t("knowledge.graph.loading")}
              </div>
            )}

            {graphQuery.data && (
              <KnowledgeGraph data={graphQuery.data.data} height={520} />
            )}
          </TabsContent>
        </Tabs>
      </div>

      <ConfirmDialog
        open={!!deleteConfirm}
        onOpenChange={(o) => !o && setDeleteConfirm(null)}
        title={t("knowledge.dataset.deleteTitle", { name: deleteConfirm?.name ?? "" })}
        description={t("knowledge.dataset.deleteDesc")}
        confirmLabel={t("common.delete")}
        destructive
        onConfirm={() => {
          if (deleteConfirm) deleteDatasetMutation.mutate(deleteConfirm.id);
        }}
      />

      <ConfirmDialog
        open={!!docDeleteConfirm}
        onOpenChange={(o) => !o && setDocDeleteConfirm(null)}
        title={t("knowledge.docs.deleteConfirmTitle", {
          name: docDeleteConfirm?.name ?? "",
        })}
        description={t("knowledge.docs.deleteConfirmDesc")}
        confirmLabel={t("common.delete")}
        destructive
        onConfirm={() => {
          if (docDeleteConfirm) deleteDocMutation.mutate(docDeleteConfirm);
        }}
      />

      <DocumentPreviewDialog
        doc={previewDoc}
        datasetId={selectedDataset?.id}
        onClose={() => setPreviewDoc(null)}
      />
    </div>
  );
}
