"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Experiment } from "@/lib/types";
import { AXIS_STROKE, AXIS_TICK, TOOLTIP_LABEL_STYLE, TOOLTIP_STYLE } from "./chart-theme";

export function LeaderboardChart({
  experiments,
  height = 260,
}: {
  experiments: Experiment[];
  height?: number;
}) {
  const data = experiments
    .filter((e) => e.status === "completed" && e.primary_metric_value != null)
    .map((e) => ({
      name: e.name.replace(" (improved)", " ⭐"),
      value: Number(e.primary_metric_value?.toFixed(4)),
      stage: e.stage,
    }));

  if (data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
        <XAxis dataKey="name" tick={{ ...AXIS_TICK, fontSize: 11 }} stroke={AXIS_STROKE} interval={0} angle={-12} textAnchor="end" height={56} />
        <YAxis tick={AXIS_TICK} stroke={AXIS_STROKE} domain={["auto", "auto"]} width={56} />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          labelStyle={TOOLTIP_LABEL_STYLE}
          formatter={(value: number) => [value.toFixed(4), data[0] ? "primary metric" : ""]}
        />
        <Bar dataKey="value" radius={[8, 8, 0, 0]} maxBarSize={56}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.stage === "improvement" ? "#22D3EE" : "#8B5CF6"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
