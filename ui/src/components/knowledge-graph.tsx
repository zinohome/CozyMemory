"use client";

/**
 * KnowledgeGraph — 2D force-directed graph visualizer for Cognee dataset graphs.
 *
 * 配套 GET /knowledge/datasets/{id}/graph 返回的 { nodes, edges }：
 * Cognee 的节点类型固定为 Entity / EntityType / TextDocument / DocumentChunk /
 * TextSummary / EdgeType，颜色和节点大小都按此调。
 */

import dynamic from "next/dynamic";
import { useMemo, useRef, useCallback, useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false }) as any;

interface RawNode {
  id?: string | number;
  label?: string;
  name?: string;
  type?: string;
  properties?: Record<string, unknown>;
  [key: string]: unknown;
}

interface RawEdge {
  id?: string;
  source?: string | number;
  target?: string | number;
  from?: string | number;
  to?: string | number;
  relation?: string;
  label?: string;
  type?: string;
  [key: string]: unknown;
}

interface GraphNode {
  id: string;
  label: string;
  displayLabel: string;
  type: string;
  color: string;
  val: number;
  properties: Record<string, unknown>;
}

interface GraphLink {
  source: string;
  target: string;
  label: string;
}

// Cognee node types → distinct colors (plus a few common knowledge-graph concepts)
const TYPE_COLORS: Record<string, string> = {
  Entity: "#60a5fa", // blue
  EntityType: "#a78bfa", // purple
  TextDocument: "#fb923c", // orange
  DocumentChunk: "#f59e0b", // amber
  TextSummary: "#34d399", // emerald
  EdgeType: "#f472b6", // pink
  // Generic fallbacks for non-Cognee payloads
  Concept: "#60a5fa",
  Person: "#34d399",
  Organization: "#fb923c",
  Location: "#f472b6",
  Event: "#facc15",
};

// 按类型控制节点半径（核心信息节点更大）
const TYPE_SIZE: Record<string, number> = {
  Entity: 6,
  EntityType: 5,
  TextDocument: 7,
  DocumentChunk: 3,
  TextSummary: 4,
  EdgeType: 3,
};

function colorForType(type: string): string {
  return TYPE_COLORS[type] ?? "#8892a4";
}

function sizeForType(type: string): number {
  return TYPE_SIZE[type] ?? 4;
}

// Cognee 的 DocumentChunk/TextSummary 的 label 是 "Chunk_<uuid>" / "TextSummary_<uuid>"，
// 几乎无法阅读。折叠成短形式 + 保留原 label 在 hover tooltip。
function shortenLabel(label: string): string {
  const m = label.match(/^(Chunk|TextSummary|DocumentChunk)_([0-9a-f]{8})/i);
  if (m) return `${m[1]}_${m[2]}…`;
  if (label.length > 28) return label.slice(0, 26) + "…";
  return label;
}

function normalizeGraph(raw: unknown): { nodes: GraphNode[]; links: GraphLink[] } {
  if (!raw || typeof raw !== "object") return { nodes: [], links: [] };

  const obj = raw as Record<string, unknown>;
  const rawNodes: RawNode[] = Array.isArray(obj.nodes) ? (obj.nodes as RawNode[]) : [];
  const rawEdges: RawEdge[] = Array.isArray(obj.edges)
    ? (obj.edges as RawEdge[])
    : Array.isArray(obj.relationships)
      ? (obj.relationships as RawEdge[])
      : [];

  const nodes: GraphNode[] = rawNodes.map((n, i) => {
    const id = String(n.id ?? i);
    const type = String(n.type ?? "Entity");
    const label = String(n.label ?? n.name ?? id);
    return {
      id,
      label,
      displayLabel: shortenLabel(label),
      type,
      color: colorForType(type),
      val: sizeForType(type),
      properties: (n.properties as Record<string, unknown>) ?? {},
    };
  });

  const nodeIds = new Set(nodes.map((n) => n.id));
  const links: GraphLink[] = rawEdges
    .map((e) => ({
      source: String(e.source ?? e.from ?? ""),
      target: String(e.target ?? e.to ?? ""),
      label: String(e.label ?? e.relation ?? e.type ?? ""),
    }))
    // 过滤掉引用不存在节点的 edge（Cognee 偶发返回悬空边会让 force-graph 抛错）
    .filter((l) => l.source && l.target && nodeIds.has(l.source) && nodeIds.has(l.target));

  return { nodes, links };
}

interface Props {
  data: unknown;
  height?: number;
}

export function KnowledgeGraph({ data, height = 520 }: Props) {
  const fullGraph = useMemo(() => normalizeGraph(data), [data]);

  // 类型分布（按 count 倒序）
  const typeStats = useMemo(() => {
    const m = new Map<string, number>();
    for (const n of fullGraph.nodes) m.set(n.type, (m.get(n.type) ?? 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [fullGraph.nodes]);

  // 选中/过滤出的类型 — 初始全选
  const [enabledTypes, setEnabledTypes] = useState<Set<string>>(() => new Set());
  useEffect(() => {
    setEnabledTypes(new Set(typeStats.map(([t]) => t)));
  }, [typeStats]);

  // 应用过滤
  const filteredGraph = useMemo(() => {
    if (enabledTypes.size === 0 || enabledTypes.size === typeStats.length) return fullGraph;
    const nodes = fullGraph.nodes.filter((n) => enabledTypes.has(n.type));
    const keep = new Set(nodes.map((n) => n.id));
    const links = fullGraph.links.filter((l) => keep.has(l.source) && keep.has(l.target));
    return { nodes, links };
  }, [fullGraph, enabledTypes, typeStats.length]);

  const [selected, setSelected] = useState<GraphNode | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);

  // 容器宽度自适应：observer 监听 wrapper 宽度变化驱动 canvas 尺寸
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(700);
  useEffect(() => {
    if (!wrapperRef.current) return;
    const el = wrapperRef.current;
    const obs = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w) setWidth(Math.max(300, Math.floor(w)));
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const handleEngineStop = useCallback(() => {
    fgRef.current?.zoomToFit(400, 40);
  }, []);

  function toggleType(type: string) {
    setEnabledTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  if (fullGraph.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-muted-foreground border-2 border-dashed rounded-lg">
        No graph data — run cognify first, then fetch the graph.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* 统计栏 + 过滤 */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <Badge variant="secondary" className="font-mono">
          {filteredGraph.nodes.length}/{fullGraph.nodes.length} nodes
        </Badge>
        <Badge variant="secondary" className="font-mono">
          {filteredGraph.links.length}/{fullGraph.links.length} edges
        </Badge>
        <span className="text-muted-foreground ml-1">click to toggle:</span>
        {typeStats.map(([type, count]) => {
          const enabled = enabledTypes.has(type);
          return (
            <button
              key={type}
              onClick={() => toggleType(type)}
              className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs transition-opacity ${
                enabled ? "opacity-100" : "opacity-40"
              }`}
              style={{ borderColor: colorForType(type) }}
            >
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: colorForType(type) }}
              />
              {type}
              <span className="text-muted-foreground">{count}</span>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-2">
        <div ref={wrapperRef} className="rounded-lg overflow-hidden border bg-[#0f1117]">
          <ForceGraph2D
            ref={fgRef as React.MutableRefObject<unknown>}
            graphData={filteredGraph}
            width={width}
            height={height}
            backgroundColor="#0f1117"
            nodeLabel={(n: GraphNode) => `${n.type}: ${n.label}`}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            nodeColor={(n: any) => (n as GraphNode).color}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            nodeVal={(n: any) => (n as GraphNode).val}
            linkLabel="label"
            linkColor={() => "#3a3d56"}
            linkDirectionalArrowLength={3}
            linkDirectionalArrowRelPos={1}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            onNodeClick={(n: any) => setSelected(n as GraphNode)}
            onBackgroundClick={() => setSelected(null)}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
              if (node.x == null || node.y == null) return;
              const gn = node as GraphNode;
              const r = Math.sqrt(gn.val) * 2.5;
              const isSelected = selected?.id === gn.id;

              // ring for selected
              if (isSelected) {
                ctx.beginPath();
                ctx.arc(node.x as number, node.y as number, r + 3, 0, 2 * Math.PI);
                ctx.strokeStyle = "#fde68a";
                ctx.lineWidth = 2 / globalScale;
                ctx.stroke();
              }

              ctx.beginPath();
              ctx.arc(node.x as number, node.y as number, r, 0, 2 * Math.PI);
              ctx.fillStyle = gn.color;
              ctx.fill();

              if (globalScale >= 0.7) {
                const fontSize = Math.max(10 / globalScale, 2);
                ctx.font = `${fontSize}px sans-serif`;
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillStyle = "#e2e8f0";
                ctx.fillText(
                  gn.displayLabel,
                  node.x as number,
                  (node.y as number) + r + fontSize
                );
              }
            }}
            onEngineStop={handleEngineStop}
            cooldownTicks={100}
          />
        </div>

        {/* 详情面板 */}
        <div className="rounded-lg border p-3 text-xs space-y-2 bg-card">
          {selected ? (
            <>
              <div className="flex items-center gap-2">
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{ background: selected.color }}
                />
                <Badge variant="outline" className="text-xs">
                  {selected.type}
                </Badge>
              </div>
              <p className="font-mono break-all text-[11px] text-muted-foreground">{selected.id}</p>
              <p className="font-medium break-words">{selected.label}</p>
              {Object.keys(selected.properties).length > 0 && (
                <>
                  <p className="text-muted-foreground uppercase tracking-wide text-[10px] mt-2">
                    properties
                  </p>
                  <ScrollArea className="h-60">
                    <pre className="text-[10px] whitespace-pre-wrap break-words font-mono bg-muted rounded p-2">
                      {JSON.stringify(selected.properties, null, 2)}
                    </pre>
                  </ScrollArea>
                </>
              )}
            </>
          ) : (
            <p className="text-muted-foreground">Click a node to inspect its properties.</p>
          )}
        </div>
      </div>
    </div>
  );
}
