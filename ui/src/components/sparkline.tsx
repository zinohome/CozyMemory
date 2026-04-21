"use client";

/**
 * Sparkline — 零依赖的内联 SVG 迷你折线图，支持 hover tooltip。
 *
 * 传入数值数组（可含 null 表示缺测点）和可选 timestamps。hover 时按 X
 * 坐标找最近点，浮层显示 value + 相对时间。null 会在路径里产生断开，
 * 避免把"未测到"和"零延迟"混淆。
 */

import { useMemo, useRef, useState } from "react";

interface Props {
  values: (number | null)[];
  timestamps?: number[]; // ms epoch，长度需与 values 对齐
  formatValue?: (v: number) => string; // 自定义 tooltip 数值格式
  width?: number;
  height?: number;
  stroke?: string;
  fill?: string;
  className?: string;
}

function relTime(ts: number): string {
  const diff = (Date.now() - ts) / 1000;
  if (diff < 5) return "now";
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return new Date(ts).toLocaleDateString();
}

export function Sparkline({
  values,
  timestamps,
  formatValue = (v) => `${v}`,
  width = 120,
  height = 36,
  stroke = "currentColor",
  fill = "none",
  className,
}: Props) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const { path, min, max } = useMemo(() => {
    if (values.length === 0) return { path: "", min: 0, max: 0 };
    const finite = values.filter((v): v is number => v != null);
    if (finite.length === 0) return { path: "", min: 0, max: 0 };
    const minV = Math.min(...finite);
    const maxV = Math.max(...finite);
    const range = maxV - minV || 1;
    const stepX = values.length > 1 ? width / (values.length - 1) : 0;
    let d = "";
    let lastValid = false;
    values.forEach((v, i) => {
      if (v == null) {
        lastValid = false;
        return;
      }
      const x = i * stepX;
      const y = height - ((v - minV) / range) * height;
      d += `${lastValid ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)} `;
      lastValid = true;
    });
    return { path: d.trim(), min: minV, max: maxV };
  }, [values, width, height]);

  const interactive = timestamps && timestamps.length === values.length;
  const stepX = values.length > 1 ? width / (values.length - 1) : 0;
  const range = max - min || 1;

  function handleMove(e: React.MouseEvent<SVGSVGElement>) {
    if (!interactive || !svgRef.current || stepX === 0) return;
    const rect = svgRef.current.getBoundingClientRect();
    const scale = rect.width / width; // 响应式 width
    const px = (e.clientX - rect.left) / scale;
    const idx = Math.round(px / stepX);
    const clamped = Math.max(0, Math.min(values.length - 1, idx));
    setHoverIdx(values[clamped] == null ? null : clamped);
  }

  function handleLeave() {
    setHoverIdx(null);
  }

  const hoverValue = hoverIdx != null ? values[hoverIdx] : null;
  const hoverTs = hoverIdx != null && interactive ? timestamps![hoverIdx] : null;
  const hoverX = hoverIdx != null ? hoverIdx * stepX : null;
  const hoverY =
    hoverValue != null ? height - ((hoverValue - min) / range) * height : null;

  if (!path) {
    return (
      <svg
        className={className}
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
      >
        <line
          x1={0}
          x2={width}
          y1={height / 2}
          y2={height / 2}
          stroke="currentColor"
          strokeOpacity={0.15}
          strokeDasharray="2 3"
        />
      </svg>
    );
  }

  return (
    <span className="relative inline-block" style={{ lineHeight: 0 }}>
      <svg
        ref={svgRef}
        className={className}
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        onMouseMove={handleMove}
        onMouseLeave={handleLeave}
        style={{ cursor: interactive ? "crosshair" : "default" }}
      >
        <path d={path} fill={fill} stroke={stroke} strokeWidth={1.5} strokeLinecap="round" />
        {hoverX != null && hoverY != null && (
          <g>
            <line
              x1={hoverX}
              x2={hoverX}
              y1={0}
              y2={height}
              stroke="currentColor"
              strokeOpacity={0.25}
              strokeDasharray="1 2"
            />
            <circle cx={hoverX} cy={hoverY} r={3} fill={stroke} />
          </g>
        )}
      </svg>
      {hoverIdx != null && hoverValue != null && (
        <div
          className="absolute z-10 pointer-events-none rounded-md border bg-popover text-popover-foreground px-2 py-1 text-[11px] shadow-md whitespace-nowrap"
          style={{
            left: `${((hoverIdx * stepX) / width) * 100}%`,
            transform: "translate(-50%, calc(-100% - 6px))",
            top: 0,
          }}
        >
          <div className="font-mono font-medium">{formatValue(hoverValue)}</div>
          {hoverTs != null && (
            <div className="text-muted-foreground text-[10px]">{relTime(hoverTs)}</div>
          )}
        </div>
      )}
    </span>
  );
}
