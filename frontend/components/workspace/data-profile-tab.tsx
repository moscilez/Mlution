"use client";
import { useI18n } from "@/lib/i18n";
import {
  Info,
  AlertTriangle,
  OctagonAlert,
  Columns3,
  Rows3,
  CopyX,
  Droplets,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { DatasetProfile, Warning } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ClassBalanceChart } from "@/components/charts/class-balance-chart";

const warningIcon: Record<Warning["level"], typeof Info> = {
  info: Info,
  warning: AlertTriangle,
  critical: OctagonAlert,
};

const warningStyle: Record<Warning["level"], string> = {
  info: "border-cyan-400/20 bg-cyan-400/5 text-blue-700",
  warning: "border-amber-400/20 bg-amber-400/5 text-amber-700",
  critical: "border-red-400/20 bg-red-400/5 text-red-700",
};

const kindVariant = {
  numeric: "info",
  categorical: "default",
  id_like: "secondary",
} as const;

export function DataProfileTab({ profile }: { profile: DatasetProfile }) {
  const { t } = useI18n();
  const totalMissing = profile.columns.reduce((sum, c) => sum + c.n_missing, 0);

  const stats = [
    { icon: Rows3, label: "Rows", value: profile.n_rows.toLocaleString() },
    {
      icon: Rows3,
      label: "Quality score (heuristic)",
      value: `${profile.quality_score ?? "—"}/100`,
    },
    {
      icon: Columns3,
      label: "Columns",
      value: profile.n_columns.toLocaleString(),
    },
    {
      icon: CopyX,
      label: "Duplicates",
      value: `${profile.n_duplicates.toLocaleString()} (${profile.duplicate_pct.toFixed(1)}%)`,
    },
    {
      icon: Droplets,
      label: "Missing cells",
      value: totalMissing.toLocaleString(),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="flex items-center gap-3 p-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-zinc-200 bg-zinc-100 text-accent">
                <stat.icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs text-zinc-500">{t(stat.label)}</p>
                <p className="text-lg font-semibold tabular-nums text-zinc-900">
                  {t(stat.value)}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {profile.warnings.length > 0 ? (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-zinc-800">
            {t("Data warnings")}
          </h3>
          <div className="space-y-2">
            {profile.warnings.map((warning, i) => {
              const Icon = warningIcon[warning.level];
              return (
                <div
                  key={`${warning.code}-${i}`}
                  className={cn(
                    "flex items-start gap-3 rounded-xl border px-4 py-3 text-sm",
                    warningStyle[warning.level],
                  )}
                >
                  <Icon className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    <span className="mr-2 rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-[10px] uppercase">
                      {t(warning.code)}
                    </span>
                    {t(warning.message)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {profile.leakage_candidates.length > 0 ? (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-zinc-800">
            {t("Leakage suspects")}
          </h3>
          <div className="flex flex-wrap gap-2">
            {profile.leakage_candidates.map((candidate) => (
              <Badge
                key={candidate.column}
                variant="warning"
                title={t(candidate.reason)}
              >
                {candidate.column}
                {t("—")}
                {t(candidate.reason)}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}

      {profile.class_balance ? (
        <Card>
          <CardContent className="space-y-3 p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-zinc-800">
                {t("Class balance")}
                {t(profile.target_column ? ` — ${profile.target_column}` : "")}
              </h3>
              {profile.imbalance_warning ? (
                <Badge variant="warning">{t("imbalanced")}</Badge>
              ) : null}
            </div>
            <ClassBalanceChart balance={profile.class_balance} />
          </CardContent>
        </Card>
      ) : null}

      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-zinc-800">{t("Columns")}</h3>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("Name")}</TableHead>
              <TableHead>{t("Kind")}</TableHead>
              <TableHead>{t("Dtype")}</TableHead>
              <TableHead className="text-right">{t("Missing %")}</TableHead>
              <TableHead className="text-right">{t("Unique")}</TableHead>
              <TableHead>{t("Examples")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {profile.columns.map((col) => (
              <TableRow key={col.name}>
                <TableCell className="font-medium text-zinc-900">
                  {col.name}
                  {col.name === profile.target_column ? (
                    <Badge variant="default" className="ml-2">
                      {t("target")}
                    </Badge>
                  ) : null}
                </TableCell>
                <TableCell>
                  <Badge variant={kindVariant[col.kind]}>
                    {t(col.kind.replace("_", "-"))}
                  </Badge>
                </TableCell>
                <TableCell className="font-mono text-xs text-zinc-600">
                  {t(col.dtype)}
                </TableCell>
                <TableCell
                  className={cn(
                    "text-right tabular-nums",
                    col.missing_pct > 20 ? "text-amber-700" : "text-zinc-700",
                  )}
                >
                  {t(col.missing_pct.toFixed(1))}
                  {t("%")}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {t(col.n_unique.toLocaleString())}
                </TableCell>
                <TableCell
                  className="max-w-[220px] truncate text-xs text-zinc-500"
                  title={col.examples.join(", ")}
                >
                  {col.examples.slice(0, 3).join(", ")}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
