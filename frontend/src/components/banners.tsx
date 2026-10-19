/** Красный баннер с текстом ошибки API (ADR-0008: ретранслятор, не интерпретатор). */
export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return <div className="banner error">{message}</div>;
}

/** Жёлто-песочный баннер предупреждения (baseline-честность и т.п.). */
export function WarningBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return <div className="banner warning">{message}</div>;
}
