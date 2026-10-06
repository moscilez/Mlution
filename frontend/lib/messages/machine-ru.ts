// Translate known server presentation messages. Arbitrary narrative is preserved.
export function machineRu(text: string): string | null {
  let m: RegExpMatchArray | null;
  const tasks: Record<string, string> = {
    binary_classification: "бинарная классификация",
    multiclass_classification: "многоклассовая классификация",
    regression: "регрессия",
  };
  const stages: Record<string, string> = {
    analyze: "анализ",
    plan: "планирование",
    build_baseline: "базовая модель",
    evaluate: "оценка",
    critique: "проверка",
    improve: "улучшение",
    finalize: "результат",
  };
  if ((m = text.match(/^Starting (\w+)\.$/)) && stages[m[1]])
    return `Начинаем этап: ${stages[m[1]]}.`;
  if ((m = text.match(/^Task plan: (\w+) on '(.+)', primary metric: (.+)\.$/)))
    return `План: ${tasks[m[1]] ?? m[1]}, цель «${m[2]}», основная метрика ${m[3]}.`;
  if (
    (m = text.match(
      /^Potential target column detected: '(.+)' \(hint: (\w+)\)\.$/,
    ))
  )
    return `Возможный целевой столбец: «${m[1]}». Предполагаемая задача: ${tasks[m[2]] ?? m[2]}.`;
  if (
    (m = text.match(
      /^Possible overfitting in (.+): train (.+)=(.+) vs validation (.+)\.$/,
    ))
  )
    return `Возможное переобучение ${m[1]}: ${m[2]} на обучении ${m[3]}, на валидации ${m[4]}.`;
  if ((m = text.match(/^(.+): validation (\w+) = ([\d.]+)(.*)$/)))
    return `${m[1]}: ${m[2]} на валидации = ${m[3]}${m[4]}`;
  if ((m = text.match(/^Improvement accepted: (\w+) ([\d.]+) → ([\d.]+)\.$/)))
    return `Улучшение принято: ${m[1]} ${m[2]} → ${m[3]}.`;
  if ((m = text.match(/^Done\. Best model: (.+) \((.+) = (.+)\)\.$/)))
    return `Готово. Лучшая модель: ${m[1]} (${m[2]} = ${m[3]}).`;
  if (
    (m = text.match(
      /^Mlution trained (\d+) model\(s\) for (\w+) on (\d+) rows × (\d+) columns\. Best model: (.+) with validation (.+) = (.+)\.$/,
    ))
  )
    return `Mlution обучил ${m[1]} моделей. Задача: ${tasks[m[2]] ?? m[2]}. Данные: ${m[3]} строк × ${m[4]} столбцов. Лучшая модель: ${m[5]}, ${m[6]} на валидации = ${m[7]}.`;
  if (
    (m = text.match(
      /^Class imbalance detected: minority class is (.+) of rows\. Accuracy-like metrics will be misleading; f1\/recall recommended\.$/,
    ))
  )
    return `Дисбаланс классов: меньший класс составляет ${m[1]} строк. Доля верных ответов может вводить в заблуждение; рекомендуются F1 и полнота.`;
  if (
    (m = text.match(
      /^Column '(.+)' looks like an identifier and will be excluded from training\.$/,
    ))
  )
    return `Столбец «${m[1]}» похож на идентификатор и будет исключён из обучения.`;
  if ((m = text.match(/^Column '(.+)' has (.+)% missing values\.$/)))
    return `В столбце «${m[1]}» пропущено ${m[2]}% значений.`;
  if (
    (m = text.match(
      /^Categorical column '(.+)' has (\d+) unique values; encoding may be noisy\.$/,
    ))
  )
    return `В столбце «${m[1]}» ${m[2]} уникальных значений; кодирование может быть нестабильным.`;
  if ((m = text.match(/^(\d+) exact duplicate rows \((.+)\)\.$/)))
    return `Полных дубликатов строк: ${m[1]} (${m[2]}).`;
  if ((m = text.match(/^Column name contains the target name '(.+)'$/)))
    return `Название столбца содержит название цели «${m[1]}»`;
  if ((m = text.match(/^Suspiciously high correlation with target \((.+)\)$/)))
    return `Подозрительно высокая корреляция с целью (${m[1]})`;
  if (text === "Column name suggests post-outcome information")
    return "Название столбца указывает на информацию после наступления результата";
  if (
    (m = text.match(
      /^Potential data leakage in '(.+)': (.+)\. It will be excluded from training\.$/,
    ))
  )
    return `Возможная утечка целевой информации в «${m[1]}»: ${machineRu(m[2]) ?? m[2]}. Столбец будет исключён из обучения.`;
  if (
    (m = text.match(
      /^Small dataset \((\d+) rows\) — metrics may be unstable\.$/,
    ))
  )
    return `Маленький набор данных (${m[1]} строк): метрики могут быть нестабильны.`;
  if ((m = text.match(/^Training (.+)…$/))) return `Обучаем ${m[1]}…`;
  if (
    (m = text.match(
      /^Profile ready: (\d+) rows × (\d+) columns — (\d+) numeric, (\d+) categorical, (\d+) id-like\. Duplicates: (\d+)\.$/,
    ))
  )
    return `Профиль готов: ${m[1]} строк × ${m[2]} столбцов. Числовых: ${m[3]}, категориальных: ${m[4]}, идентификаторов: ${m[5]}. Дубликатов: ${m[6]}.`;
  return null;
}
