/**
 * Бейджи статусов: цвет несёт смысл, текст — доменный (как в CLI).
 * Тон выбирает СТРАНИЦА: UI не выводит статус из данных сам — иначе
 * знание о домене расползается по компонентам.
 */
export type BadgeTone = "pending" | "done" | "order" | "sufficient" | "cold";

export function Badge({ tone, children }: { tone: BadgeTone; children: string }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

/** Русский текст статуса заявки (зеркало _STATUS_RU на краю API). */
export function requestBadge(status: string): { tone: BadgeTone; label: string } {
  return status === "обработана"
    ? { tone: "done", label: "обработана" }
    : { tone: "pending", label: "подана" };
}

/** Бейдж статуса рекомендации EX-2. */
export function recommendationBadge(
  status: string,
): { tone: BadgeTone; label: string } {
  switch (status) {
    case "order":
      return { tone: "order", label: "заказать" };
    case "sufficient":
      return { tone: "sufficient", label: "достаточно" };
    default:
      return { tone: "cold", label: "холодный старт" };
  }
}
