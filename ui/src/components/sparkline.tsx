"use client";

/**
 * Sparkline — 零依赖的内联 SVG 迷你折线图。
 *
 * 传入数值数组（可含 null 表示缺测点）和可视参数，返回 viewBox 归一化的 svg。
 * null 会在路径里产生断开，避免把"未测到"和"零延迟"混淆。
 */

import { useMemo } from "react";

interface Props {
  values: (number | null)[];
  width?: number;
  height?: number;
  stroke?: string;
  fill?: string;
  className?: string;
}

export function Sparkline({
  values,
  width = 120,
  height = 36,
  stroke = "currentColor",
  fill = "none",
  className,
}: Props) {
  const path = useMemo(() => {
    if (values.length === 0) return "";
    const finite = values.filter((v): v is number => v != null);
    if (finite.length === 0) return "";
    const min = Math.min(...finite);
    const max = Math.max(...finite);
    const range = max - min || 1;
    const stepX = values.length > 1 ? width / (values.length - 1) : 0;
    let d = "";
    let lastValid = false;
    values.forEach((v, i) => {
      if (v == null) {
        lastValid = false;
        return;
      }
      const x = i * stepX;
      const y = height - ((v - min) / range) * height;
      d += `${lastValid ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)} `;
      lastValid = true;
    });
    return d.trim();
  }, [values, width, height]);

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
    <svg
      className={className}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
    >
      <path d={path} fill={fill} stroke={stroke} strokeWidth={1.5} strokeLinecap="round" />
    </svg>
  );
}
