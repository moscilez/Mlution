"use client";

import { useState } from "react";
import { AlertTriangle, Check, ClipboardCopy, Info, Lightbulb, OctagonAlert } from "lucide-react";
import type { FinalReport, Warning } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ImprovementsList } from "@/components/improvements";

const warningIcon: Record<Warning["level"], typeof Info> = {
  info: Info,
  warning: AlertTriangle,
  critical: OctagonAlert,
};

const warningColor: Record<Warning["level"], string> = {
  info: "text-zinc-400",
  warning: "text-amber-300",
  critical: "text-red-300",
};

function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => {
          void navigator.clipboard.writeText(code);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        }}
        className="absolute right-3 top-3 flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-zinc-300 transition-colors hover:bg-white/10"
      >
        {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <ClipboardCopy className="h-3.5 w-3.5" />}
        {copied ? "Copied" : "Copy"}
      </button>
      <pre className="max-h-96 overflow-auto rounded-xl border border-white/10 bg-black/40 p-4 font-mono text-xs leading-relaxed text-zinc-300">
        {code}
      </pre>
    </div>
  );
}

export function ReportTab({ report }: { report: FinalReport }) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm leading-relaxed text-zinc-200">{report.summary}</p>
          <p className="text-sm leading-relaxed text-zinc-400">{report.explanation}</p>
          <p className="rounded-xl border border-brand/20 bg-brand/5 p-3 text-xs text-zinc-400">
            <span className="font-medium text-brand">Task rationale: </span>
            {report.task.rationale}
          </p>
        </CardContent>
      </Card>

      {report.improvements.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Improvement loop</CardTitle>
          </CardHeader>
          <CardContent>
            <ImprovementsList steps={report.improvements} />
          </CardContent>
        </Card>
      ) : null}

      {report.warnings.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Warnings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {report.warnings.map((w, i) => {
              const Icon = warningIcon[w.level];
              return (
                <div key={i} className="flex items-start gap-2.5 text-sm">
                  <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${warningColor[w.level]}`} />
                  <span className="text-zinc-300">{w.message}</span>
                </div>
              );
            })}
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Limitations</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1.5 pl-4 text-sm text-zinc-400">
              {report.limitations.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Lightbulb className="h-4 w-4 text-accent" /> Next steps
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1.5 pl-4 text-sm text-zinc-400">
              {report.next_steps.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Generated inference code</CardTitle>
        </CardHeader>
        <CardContent>
          <CodeBlock code={report.usage_code} />
        </CardContent>
      </Card>
    </div>
  );
}
