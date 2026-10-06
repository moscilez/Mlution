"use client";
import { useI18n } from "@/lib/i18n";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AXIS_TICK,
  AXIS_STROKE,
  CHART_COLORS,
  GRID_STROKE,
  TOOLTIP_STYLE,
  TOOLTIP_LABEL_STYLE,
} from "./chart-theme";

const PALETTE = [
  CHART_COLORS.brand,
  CHART_COLORS.accent,
  CHART_COLORS.emerald,
  CHART_COLORS.amber,
  CHART_COLORS.red,
];

export function ClassBalanceChart({
  balance,
}: {
  balance: Record<string, number>;
}) {
  const { t } = useI18n();
  const data = Object.entries(balance).map(([label, count]) => ({
    label,
    count,
  }));
  if (data.length === 0) return null;

  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 8, right: 8, bottom: 4, left: -12 }}
        >
          <CartesianGrid stroke={GRID_STROKE} vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ ...AXIS_TICK, fontSize: 11 }}
            stroke={AXIS_STROKE}
          />
          <YAxis tick={AXIS_TICK} stroke={AXIS_STROKE} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            labelStyle={TOOLTIP_LABEL_STYLE}
            cursor={{ fill: "rgba(29,29,31,0.03)" }}
          />
          <Bar
            dataKey="count"
            name={t("Rows")}
            radius={[6, 6, 0, 0]}
            maxBarSize={48}
          >
            {data.map((entry, index) => (
              <Cell key={entry.label} fill={PALETTE[index % PALETTE.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
