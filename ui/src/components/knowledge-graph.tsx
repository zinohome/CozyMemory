"use client";

/**
 * KnowledgeGraph — 2D force-directed graph visualizer for Cognee dataset graphs.
 *
 * Dynamically imported (ssr: false) because react-force-graph-2d uses
 * canvas/WebGL APIs that don't exist in Node.
 *
 * Props:
 *   graphData — raw response from GET /knowledge/datasets/{id}/graph
 *                Expected shape: { nodes: [...], edges: [...] } or { nodes, relationships }
 *                Unknown shapes are gracefully handled.
 */

import dynamic from "next/dynamic";
import { useMemo, useRef, useCallback } from "react";

// Dynamically import to avoid SSR issues with canvas/WebGL
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false }) as any;

interface RawNode {
  id?: string | number;
  label?: string;
  name?: string;
  type?: string;
  [key: string]: unknown;
}

interface RawEdge {
  id?: string;
  source?: string | number;
  target?: string | number;
  from?: string | number;
  to?: string | number;
  relation?: string;
  type?: string;
  [key: string]: unknown;
}

interface GraphNode {
  id: string;
  label: string;
  type: string;
  color: string;
  val: number;
}

interface GraphLink {
  source: string;
  target: string;
  label: string;
}

// Deterministic color by node type
const TYPE_COLORS: Record<string, string> = {
  Entity: "#6c63ff",
  Concept: "#60a5fa",
  Person: "#34d399",
  Organization: "#fb923c",
  Location: "#f472b6",
  Event: "#facc15",
};

function colorForType(type: string): string {
  return TYPE_COLORS[type] ?? "#8892a4";
}

function normalizeGraph(raw: unknown): { nodes: GraphNode[]; links: GraphLink[] } {
  if (!raw || typeof raw !== "object") return { nodes: [], links: [] };

  const obj = raw as Record<string, unknown>;

  // Handle nodes
  const rawNodes: RawNode[] = Array.isArray(obj.nodes)
    ? (obj.nodes as RawNode[])
    : [];

  const nodes: GraphNode[] = rawNodes.map((n, i) => ({
    id: String(n.id ?? i),
    label: String(n.label ?? n.name ?? n.id ?? `node_${i}`),
    type: String(n.type ?? "Entity"),
    color: colorForType(String(n.type ?? "")),
    val: 4,
  }));

  // Handle edges (Cognee may use "edges" or "relationships")
  const rawEdges: RawEdge[] = Array.isArray(obj.edges)
    ? (obj.edges as RawEdge[])
    : Array.isArray(obj.relationships)
      ? (obj.relationships as RawEdge[])
      : [];

  const links: GraphLink[] = rawEdges
    .filter((e) => (e.source ?? e.from) != null && (e.target ?? e.to) != null)
    .map((e) => ({
      source: String(e.source ?? e.from),
      target: String(e.target ?? e.to),
      label: String(e.relation ?? e.type ?? ""),
    }));

  return { nodes, links };
}

interface Props {
  data: unknown;
  width?: number;
  height?: number;
}

export function KnowledgeGraph({ data, width = 700, height = 480 }: Props) {
  const graphData = useMemo(() => normalizeGraph(data), [data]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);

  const handleEngineStop = useCallback(() => {
    fgRef.current?.zoomToFit(400);
  }, []);

  if (graphData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-muted-foreground border-2 border-dashed rounded-lg">
        No graph data — run cognify first, then fetch the graph.
      </div>
    );
  }

  return (
    <div className="rounded-lg overflow-hidden border bg-[#0f1117]">
      <ForceGraph2D
        ref={fgRef as React.MutableRefObject<unknown>}
        graphData={graphData}
        width={width}
        height={height}
        backgroundColor="#0f1117"
        nodeLabel="label"
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        nodeColor={(n: any) => (n as GraphNode).color}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        nodeVal={(n: any) => (n as GraphNode).val}
        linkLabel="label"
        linkColor={() => "#3a3d56"}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const gn = node as GraphNode;
          const label = gn.label;
          const fontSize = Math.max(10 / globalScale, 2);
          const r = Math.sqrt(gn.val) * 2.5;

          // Circle
          ctx.beginPath();
          ctx.arc(node.x as number, node.y as number, r, 0, 2 * Math.PI);
          ctx.fillStyle = gn.color;
          ctx.fill();

          // Label (only when zoomed in enough)
          if (globalScale >= 0.6) {
            ctx.font = `${fontSize}px sans-serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillStyle = "#e2e8f0";
            ctx.fillText(label.length > 20 ? label.slice(0, 18) + "…" : label, node.x as number, (node.y as number) + r + fontSize);
          }
        }}
        onEngineStop={handleEngineStop}
        cooldownTicks={100}
      />
    </div>
  );
}
