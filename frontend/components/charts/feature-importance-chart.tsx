"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { FeatureImportance } from "@/lib/types";
import {
  AXIS_TICK,
  AXIS_STROKE,
  CHART_COLORS,
  TOOLTIP_STYLE,
  TOOLTIP_LABEL_STYLE,
} from "./chart-theme";

export function FeatureImportanceChart({
  data,
  limit = 10,
  height,
}: {
  data: FeatureImportance[];
  limit?: number;
  height?: number;
}) {
  const top = [...data]
    .sort((a, b) => b.importance - a.importance)
    .slice(0, limit)
    .reverse();
  const chartHeight = height ?? Math.max(200, top.length * 34 + 20);

  if (top.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-zinc-500">
        Feature importance is not available for this model.
      </p>
    );
  }

  return (
    <div style={{ height: chartHeight }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={top} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
          <XAxis
            type="number"
            tick={AXIS_TICK}
            stroke={AXIS_STROKE}
            tickFormatter={(v: number) => v.toFixed(2)}
          />
          <YAxis
            type="category"
            dataKey="feature"
            width={130}
            tick={{ ...AXIS_TICK, fontSize: 11 }}
            stroke={AXIS_STROKE}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            labelStyle={TOOLTIP_LABEL_STYLE}
            formatter={(value) => [Number(value).toFixed(4), "Importance"]}
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
          />
          <Bar dataKey="importance" radius={[0, 6, 6, 0]} maxBarSize={18}>
            {top.map((entry, index) => (
              <Cell
                key={entry.feature}
                fill={index === top.length - 1 ? CHART_COLORS.accent : CHART_COLORS.brand}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
