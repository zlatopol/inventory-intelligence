import { FormEvent, useState } from "react";
import { api } from "../api/client";
import type { RecommendationList } from "../api/types";
import { Badge, recommendationBadge } from "../components/Badge";
import { ErrorBanner, WarningBanner } from "../components/banners";
import { EmptyState, Spinner } from "../components/states";

/**
 * Рекомендации (EX-2): параметры политики с дефолтами (пустое поле = дефолт,
 * как в CLI пункте 13), таблица со статусами. Строки «заказать» подсвечены
 * акцентом — главный вывод экрана виден до чтения чисел.
 */
const DEFAULTS = { serviceLevel: "0.95", lead: "3", horizon: "7" };

export default function RecommendationsPage() {
  const [serviceLevel, setServiceLevel] = useState(DEFAULTS.serviceLevel);
  const [lead, setLead] = useState(DEFAULTS.lead);
  const [horizon, setHorizon] = useState(DEFAULTS.horizon);
  const [result, setResult] = useState<RecommendationList | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function calculate(e: FormEvent) {
    e.preventDefault();
    // пустое поле = дефолт (зеркало CLI); кросс-правило L+H≤14 решает сервис
    const sl = serviceLevel.trim() === "" ? DEFAULTS.serviceLevel : serviceLevel;
    const l = lead.trim() === "" ? DEFAULTS.lead : lead;
    const h = horizon.trim() === "" ? DEFAULTS.horizon : horizon;
    const slNum = Number(sl);
    const lNum = Number(l);
    const hNum = Number(h);
    if ([slNum, lNum, hNum].some((n) => Number.isNaN(n))) {
      setError("Параметры должны быть числами");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResult(
        await api.get<RecommendationList>(
          `/recommendations?service_level=${slNum}&lead_time_days=${lNum}&horizon_days=${hNum}`,
        ),
      );
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Ошибка расчёта");
    } finally {
      setLoading(false);
    }
  }

  const window = result ? result.lead_time_days + result.horizon_days : null;

  return (
    <section>
      <h1>Рекомендации по закупке</h1>
      <p className="page-sub">
        Политика order-up-to: спрос на окно L+H + страховой запас − остаток — EX-2
      </p>
      <ErrorBanner message={error} />

      <div className="card">
        <form className="inline" onSubmit={calculate}>
          <label className="field" htmlFor="rec-sl">
            Уровень сервиса
            <input
              id="rec-sl"
              type="number"
              step="0.01"
              min="0.01"
              max="0.99"
              value={serviceLevel}
              onChange={(e) => setServiceLevel(e.target.value)}
            />
          </label>
          <label className="field" htmlFor="rec-lead">
            Поставка, дней
            <input
              id="rec-lead"
              type="number"
              min={1}
              step={1}
              value={lead}
              onChange={(e) => setLead(e.target.value)}
            />
          </label>
          <label className="field" htmlFor="rec-horizon">
            Горизонт обзора, дней
            <input
              id="rec-horizon"
              type="number"
              min={1}
              step={1}
              value={horizon}
              onChange={(e) => setHorizon(e.target.value)}
            />
          </label>
          <button className="primary" type="submit" disabled={loading}>
            {loading ? "Считаем…" : "Рассчитать"}
          </button>
        </form>
      </div>

      {loading && <Spinner />}

      {result !== null && (
        <>
          <WarningBanner message={result.warning} />
          <p className="muted">
            Окно {window} дн. (поставка {result.lead_time_days} + обзор{" "}
            {result.horizon_days}), уровень сервиса {result.service_level}
          </p>
          <div className="card">
            {result.recommendations.length === 0 ? (
              <EmptyState text="Нет товаров в складском списке" />
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Товар</th>
                    <th className="num">Остаток</th>
                    <th className="num">Прогноз спроса</th>
                    <th className="num">Страховой запас</th>
                    <th className="num">Заказать</th>
                    <th>Статус</th>
                  </tr>
                </thead>
                <tbody>
                  {result.recommendations.map((r) => {
                    const badge = recommendationBadge(r.status);
                    return (
                      <tr
                        key={r.product_id}
                        className={r.status === "order" ? "row-order" : undefined}
                      >
                        <td>{r.product_name}</td>
                        <td className="num">{r.warehouse_quantity}</td>
                        <td className="num">{r.forecast_demand ?? "—"}</td>
                        <td className="num">{r.safety_stock ?? "—"}</td>
                        <td className="num">
                          {r.order_quantity !== null ? (
                            <strong>{r.order_quantity}</strong>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td>
                          <Badge tone={badge.tone}>{badge.label}</Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
      {result === null && !loading && (
        <p className="muted">
          Нажмите «Рассчитать» — система просуммирует прогнозы по парам и
          предложит заказ для каждого товара.
        </p>
      )}
    </section>
  );
}
