"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { knowledgeApi, type KnowledgeDataset, type KnowledgeSearchResult } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, BookOpen, RefreshCw, Search, Plus, GitBranch } from "lucide-react";

function DatasetRow({
  ds,
  selected,
  onClick,
}: {
  ds: KnowledgeDataset;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-md border px-3 py-2 text-sm transition-colors ${
        selected ? "bg-primary/10 border-primary" : "hover:bg-muted"
      }`}
    >
      <p className="font-medium">{ds.name}</p>
      <p className="text-xs text-muted-foreground font-mono truncate">{ds.id}</p>
    </button>
  );
}

export default function KnowledgePage() {
  const qc = useQueryClient();
  const [selectedDataset, setSelectedDataset] = useState<KnowledgeDataset | null>(null);
  const [addText, setAddText] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchType, setSearchType] = useState("GRAPH_COMPLETION");
  const [cognifyJobId, setCognifyJobId] = useState<string | null>(null);

  const datasetsQuery = useQuery({
    queryKey: ["datasets"],
    queryFn: knowledgeApi.listDatasets,
  });

  const cognifyStatusQuery = useQuery({
    queryKey: ["cognify-status", cognifyJobId],
    queryFn: () => knowledgeApi.getCognifyStatus(cognifyJobId!),
    enabled: !!cognifyJobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "running" || status === "pending" ? 3000 : false;
    },
  });

  const addMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.add(addText, selectedDataset?.name ?? "default"),
    onSuccess: () => setAddText(""),
  });

  const cognifyMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.cognify(selectedDataset ? [selectedDataset.name] : undefined),
    onSuccess: (data) => {
      if (data.pipeline_run_id) setCognifyJobId(data.pipeline_run_id);
    },
  });

  const searchMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.search({
        query: searchQuery,
        dataset: selectedDataset?.id,
        search_type: searchType,
        top_k: 10,
      }),
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Knowledge Base</h1>
        <p className="text-muted-foreground text-sm mt-1">Manage Cognee datasets and knowledge graphs.</p>
      </div>

      <div className="grid lg:grid-cols-[240px_1fr] gap-4">
        {/* Dataset list */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">Datasets</p>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => qc.invalidateQueries({ queryKey: ["datasets"] })}
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </div>
          <ScrollArea className="h-64">
            <div className="space-y-1 pr-2">
              {datasetsQuery.data?.data.map((ds) => (
                <DatasetRow
                  key={ds.id}
                  ds={ds}
                  selected={selectedDataset?.id === ds.id}
                  onClick={() => setSelectedDataset(ds)}
                />
              ))}
              {datasetsQuery.isLoading && <Loader2 className="h-4 w-4 animate-spin mx-auto mt-4" />}
            </div>
          </ScrollArea>
        </div>

        {/* Actions */}
        <Tabs defaultValue="add">
          <TabsList>
            <TabsTrigger value="add">Add Data</TabsTrigger>
            <TabsTrigger value="search">Search</TabsTrigger>
            <TabsTrigger value="cognify">Cognify</TabsTrigger>
          </TabsList>

          <TabsContent value="add" className="space-y-3 mt-3">
            <div className="space-y-1.5">
              <Label>Dataset</Label>
              <p className="text-sm text-muted-foreground">
                {selectedDataset ? selectedDataset.name : "default (no dataset selected)"}
              </p>
            </div>
            <div className="space-y-1.5">
              <Label>Content</Label>
              <Textarea
                rows={5}
                placeholder="Enter text to add to the knowledge base…"
                value={addText}
                onChange={(e) => setAddText(e.target.value)}
              />
            </div>
            <Button
              onClick={() => addMutation.mutate()}
              disabled={!addText || addMutation.isPending}
            >
              {addMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Plus className="h-4 w-4 mr-2" />
              )}
              Add to Knowledge Base
            </Button>
            {addMutation.isSuccess && (
              <p className="text-xs text-green-600">
                Added! data_id: {addMutation.data?.data_id}
              </p>
            )}
          </TabsContent>

          <TabsContent value="search" className="space-y-3 mt-3">
            <div className="flex gap-2">
              <Input
                placeholder="Search the knowledge graph…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && searchMutation.mutate()}
              />
              <Select value={searchType} onValueChange={(v) => setSearchType(v ?? "GRAPH_COMPLETION")}>
                <SelectTrigger className="w-44">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CHUNKS">Chunks</SelectItem>
                  <SelectItem value="SUMMARIES">Summaries</SelectItem>
                  <SelectItem value="RAG_COMPLETION">RAG</SelectItem>
                  <SelectItem value="GRAPH_COMPLETION">Graph</SelectItem>
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
                {searchMutation.data?.data.map((item, i) => (
                  <div key={String(item.id ?? i)} className="rounded-md border p-3 text-sm space-y-1">
                    <p>{item.text ?? JSON.stringify(item)}</p>
                    {item.score != null && (
                      <span className="text-xs text-muted-foreground">
                        score: {(item.score as number).toFixed(3)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="cognify" className="space-y-3 mt-3">
            <p className="text-sm text-muted-foreground">
              Build the knowledge graph for{" "}
              <strong>{selectedDataset ? selectedDataset.name : "all datasets"}</strong>.
              This may take 30–120s.
            </p>
            <Button onClick={() => cognifyMutation.mutate()} disabled={cognifyMutation.isPending}>
              {cognifyMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <GitBranch className="h-4 w-4 mr-2" />
              )}
              Start Cognify
            </Button>

            {cognifyJobId && (
              <Card>
                <CardContent className="pt-3 pb-3 text-sm space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Job ID:</span>
                    <span className="font-mono text-xs">{cognifyJobId}</span>
                  </div>
                  {cognifyStatusQuery.data && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">Status:</span>
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
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
