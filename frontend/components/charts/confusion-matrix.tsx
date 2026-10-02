import { cn } from "@/lib/utils";
import type { ConfusionMatrix } from "@/lib/types";

export function ConfusionMatrixGrid({
  matrix,
  className,
}: {
  matrix: ConfusionMatrix;
  className?: string;
}) {
  const max = Math.max(1, ...matrix.matrix.flat());
  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="border-separate" style={{ borderSpacing: 3 }}>
        <thead>
          <tr>
            <th className="p-1 text-right text-[10px] uppercase tracking-wide text-zinc-500">
              actual \ predicted
            </th>
            {matrix.labels.map((label) => (
              <th
                key={label}
                className="max-w-[90px] truncate p-1 text-center text-[11px] font-medium text-zinc-400"
                title={label}
              >
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.matrix.map((row, i) => (
            <tr key={matrix.labels[i] ?? i}>
              <th
                className="max-w-[90px] truncate p-1 text-right text-[11px] font-medium text-zinc-400"
                title={matrix.labels[i]}
              >
                {matrix.labels[i]}
              </th>
              {row.map((value, j) => {
                const intensity = value / max;
                const diagonal = i === j;
                return (
                  <td
                    key={`${i}-${j}`}
                    className={cn(
                      "h-10 w-14 rounded-md text-center text-sm font-semibold tabular-nums",
                      intensity > 0.5 ? "text-white" : "text-zinc-300"
                    )}
                    style={{
                      backgroundColor: diagonal
                        ? `rgba(139, 92, 246, ${0.12 + intensity * 0.75})`
                        : value > 0
                          ? `rgba(248, 113, 113, ${0.08 + intensity * 0.5})`
                          : "rgba(255,255,255,0.03)",
                    }}
                    title={`${matrix.labels[i]} predicted as ${matrix.labels[j]}: ${value}`}
                  >
                    {value}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
