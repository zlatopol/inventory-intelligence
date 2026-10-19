/** Загрузка: состояния экрана «загрузка → данные | пусто | ошибка» (Стадия 4). */
export function Spinner() {
  return <div className="spinner" role="status" aria-label="Загрузка" />;
}

/** Пустое состояние — не пустая тишина, а внятная фраза (по образцу CLI). */
export function EmptyState({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}
