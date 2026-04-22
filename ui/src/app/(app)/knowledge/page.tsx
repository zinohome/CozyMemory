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
import { Loader2, RefreshCw, Search, Plus, GitBranch, Network, Trash2 } from "lucide-react";
import { KnowledgeGraph } from "@/components/knowledge-graph";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { useT } from "@/lib/i18n";

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
    </div>
  );
}
