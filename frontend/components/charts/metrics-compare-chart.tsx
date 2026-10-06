"use client";
import { useI18n } from "@/lib/i18n";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MetricResult } from "@/lib/types";
import {
  AXIS_TICK,
  AXIS_STROKE,
  CHART_COLORS,
  GRID_STROKE,
  TOOLTIP_STYLE,
  TOOLTIP_LABEL_STYLE,
} from "./chart-theme";

export function MetricsCompareChart({ metrics }: { metrics: MetricResult[] }) {
  const { t } = useI18n();
  const byName = new Map<
    string,
    { name: string; train?: number; validation?: number }
  >();
  for (const m of metrics) {
    const entry = byName.get(m.name) ?? { name: m.name };
    entry[m.split] = m.value;
    byName.set(m.name, entry);
  }
  const data = Array.from(byName.values());

  if (data.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-zinc-500">
        {t("No metrics recorded.")}
      </p>
    );
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 8, right: 8, bottom: 4, left: -12 }}
        >
          <CartesianGrid stroke={GRID_STROKE} vertical={false} />
          <XAxis dataKey="name" tick={AXIS_TICK} stroke={AXIS_STROKE} />
          <YAxis
            tick={AXIS_TICK}
            stroke={AXIS_STROKE}
            tickFormatter={(v: number) => v.toFixed(2)}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            labelStyle={TOOLTIP_LABEL_STYLE}
            formatter={(value) => Number(value).toFixed(3)}
            cursor={{ fill: "rgba(29,29,31,0.03)" }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: "#6e6e73" }} />
          <Bar
            dataKey="train"
            name={t("Train")}
            fill={CHART_COLORS.zinc}
            radius={[6, 6, 0, 0]}
            maxBarSize={40}
          />
          <Bar
            dataKey="validation"
            name={t("Validation")}
            fill={CHART_COLORS.brand}
            radius={[6, 6, 0, 0]}
            maxBarSize={40}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
