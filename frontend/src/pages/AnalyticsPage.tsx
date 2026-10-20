import { WarningBanner } from "../components/banners";

/**
 * Аналитика — статическая витрина ML-трека (Стадия 1: интервьюер/README).
 * Все цифры — зашитые результаты прогонов из docs/project-status.md;
 * картинки — /img/... (FastAPI отдаёт docs/img напрямую, ADR-0009:
 * единый источник правды — график пересоздан скриптом → фронт уже свежий).
 *
 * Числа НЕ считаются на лету: воспроизводимость важнее живости —
 * те же цифры лежат в MLflow и README.
 */

const METRICS: { model: string; mae: string; wape: string; note: string }[] = [
  { model: "naive", mae: "9.72", wape: "20.5%", note: "вчера = сегодня" },
  { model: "seasonal_naive_7", mae: "7.90", wape: "16.7%", note: "неделя назад = сегодня" },
  { model: "moving_average_7", mae: "7.67", wape: "16.2%", note: "скользящее среднее" },
  { model: "lightgbm (500 пар)", mae: "6.01", wape: "11.5%", note: "Phase 2, −21.6% к бейзлайну" },
  { model: "+ праздники", mae: "5.96", wape: "11.4%", note: "календарные фичи" },
];

const BACKTEST = [
  { policy: "naive (без SS)", fill: "99.0%", stock: "×1.00", note: "5.5% дней со стокаутом" },
  { policy: "order_up_to SL 0.95", fill: "100%", stock: "×1.21", note: "страховой запас z·σ·√(L+H)" },
  { policy: "order_up_to SL 0.99", fill: "100%", stock: "×1.31", note: "нелинейная цена z: 1.645 → 2.326" },
];

export default function AnalyticsPage() {
  return (
    <section>
      <h1>Аналитика</h1>
      <p className="page-sub">
        ML-трек проекта: от событий склада до рекомендаций по закупке. Все
        метрики — результаты воспроизводимых прогонов (MLflow, walk-forward).
      </p>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Пайплайн</h2>
        <p>
          события (stock_event / Kaggle) → дневной спрос (бизнес-таймзона,
          ADR-0007) → фичи без утечек → LightGBM → рекурсивный прогноз на
          1–14 дней → инвентаризационная политика → рекомендация заказа
        </p>
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Качество прогноза (walk-forward, 500 пар)</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Модель</th>
              <th className="num">MAE, шт.</th>
              <th className="num">WAPE</th>
              <th>Примечание</th>
            </tr>
          </thead>
          <tbody>
            {METRICS.map((m) => (
              <tr key={m.model}>
                <td>{m.model}</td>
                <td className="num">{m.mae}</td>
                <td className="num">{m.wape}</td>
                <td className="muted">{m.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted" style={{ marginBottom: 0 }}>
          Каждый шаг проверялся против бейзлайна; сложность модели — не
          самоцель (сезонный наив уступает среднему лишь на 4%).
        </p>
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Горизонт 1–14 дней (блочная оценка)</h2>
        <img src="/img/horizon_degradation.png" alt="Деградация MAE по горизонту k" style={{ maxWidth: "100%" }} />
        <p className="muted" style={{ marginBottom: 0 }}>
          Модель плоская до k=14: неделя рекурсии стоит ~0.04 MAE. Гипотезы
          «лаги прогниют» (H6a–c) опровергнуты измерением — горизонт
          обещания «1–14 дней» доказан, а не постулирован.
        </p>
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Праздничный профиль</h2>
        <img src="/img/holidays_profile.png" alt="Профиль спроса вокруг праздников" style={{ maxWidth: "100%" }} />
        <p className="muted" style={{ marginBottom: 0 }}>
          Разведка сняла два конфаунда (день недели, сезонный тренд):
          «предпраздничного роста» нет — единственный сигнал у «полосы
          закрытия» Рождества/НГ. Гипотеза H5 отклонена до обучения.
        </p>
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Рекомендации: цена уровня сервиса</h2>
        <img src="/img/replenishment_policies.png" alt="Fill rate и средний запас трёх политик" style={{ maxWidth: "100%" }} />
        <table className="table" style={{ marginTop: 12 }}>
          <thead>
            <tr>
              <th>Политика</th>
              <th className="num">Fill rate</th>
              <th className="num">Запас</th>
              <th>Примечание</th>
            </tr>
          </thead>
          <tbody>
            {BACKTEST.map((b) => (
              <tr key={b.policy}>
                <td>{b.policy}</td>
                <td className="num">{b.fill}</td>
                <td className="num">{b.stock}</td>
                <td className="muted">{b.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted" style={{ marginBottom: 0 }}>
          Симуляция периодического обзора (500 пар, 52 якоря): страховой
          запас покупает последние ~1 п.п. fill rate за +21% запаса —
          компромисс «сервис ↔ замороженные деньги» измерен.
        </p>
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Как считается заказ</h2>
        <p>
          Q = ⌈ прогнозный спрос (L+H) + z·σ·√(L+H) − остаток склада ⌉
        </p>
        <p className="muted" style={{ marginBottom: 0 }}>
          z — квантиль нормального распределения для уровня сервиса; σ —
          дневная изменчивость агрегированного спроса (28 дней); корень из
          окна — потому что складываются дисперсии независимых дней, а
          ошибки разнонаправленны и гасят друг друга.
        </p>
      </div>

      <WarningBanner message="Данные метрики зафиксированы по прогонам 2026-10-08…13; живое переобучение обновляет модель, но не эту страницу." />
    </section>
  );
}
