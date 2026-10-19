import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
  type ChartData,
} from "chart.js";
import { useCallback, useEffect, useState } from "react";
import { Line } from "react-chartjs-2";
import { api } from "../api/client";
import type { Forecast, History, Product, Store } from "../api/types";
import { ErrorBanner, WarningBanner } from "../components/banners";
import { ConfirmModal, Toast, useToast } from "../components/Modal";

ChartJS.register(
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
  Legend,
);

/**
 * Прогноз (EX-1): селекторы пары + график «факт + прогноз» + retrain.
 * Честность видна без чтения текста: baseline → прогнозная линия ПУНКТИРОМ
 * (Stage 5.3); соединение серий в последней точке факта — визуальный
 * «продолжай отсюда».
 */

/** Данные графика: чистая функция — тестируется без canvas (jsdom его не умеет). */
export function forecastChartData(
  history: History["history"],
  forecast: Forecast["forecast"],
  dashed: boolean,
): ChartData<"line", (number | null)[]> {
  const labels = [
    ...history.map((d) => d.date.slice(5, 10)),
    ...forecast.map((d) => d.date.slice(5, 10)),
  ];
  return {
    labels,
    datasets: [
      {
        label: "Факт",
        data: [...history.map((d) => d.demand), ...forecast.map(() => null)],
        borderColor: "#412151",
        backgroundColor: "#412151",
        pointRadius: 2,
        tension: 0.25,
      },
      {
        label: "Прогноз",
        // стык: последняя точка факта дублируется в прогнозную серию
        data: [
          ...history.slice(0, -1).map(() => null),
          history.at(-1)?.demand ?? null,
          ...forecast.map((d) => d.demand),
        ],
        borderColor: "#DF7694",
        backgroundColor: "#DF7694",
        borderDash: dashed ? [6, 6] : undefined,
        pointRadius: 3,
        tension: 0.25,
      },
    ],
  };
}

export default function ForecastPage() {
  const [stores, setStores] = useState<Store[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [storeId, setStoreId] = useState("");
  const [productId, setProductId] = useState("");
  const [days, setDays] = useState("3");
  const [result, setResult] = useState<Forecast | null>(null);
  const [history, setHistory] = useState<History["history"] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retraining, setRetraining] = useState(false);
  const { toast, show } = useToast();

  const loadLists = useCallback(async () => {
    try {
      const [s, p] = await Promise.all([
        api.get<Store[]>("/stores"),
        api.get<Product[]>("/products"),
      ]);
      setStores(s);
      setProducts(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить списки");
    }
  }, []);

  useEffect(() => {
    void loadLists();
  }, [loadLists]);

  async function build() {
    const n = Number(days);
    if (!Number.isInteger(n) || n < 1 || n > 14) {
      // механическая граница, зеркало InvalidForecastHorizonError (errors.py)
      setError("Горизонт прогноза — целое число от 1 до 14 дней");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const query = `?store_id=${storeId}&product_id=${productId}&days=${n}`;
      const [f, h] = await Promise.all([
        api.get<Forecast>(`/forecast${query}`),
        api.get<History>(`/forecast/history${query}&days=28`),
      ]);
      setResult(f);
      setHistory(h.history);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Ошибка построения прогноза");
    } finally {
      setLoading(false);
    }
  }

  async function confirmRetrain() {
    setRetraining(false);
    setLoading(true);
    try {
      const r = await api.post<{ status: string; trained_at: string }>(
        "/forecast/retrain",
      );
      show(`Модель переобучена (${new Date(r.trained_at).toLocaleTimeString("ru-RU")})`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка переобучения");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <h1>Прогноз спроса</h1>
      <p className="page-sub">График: 28 дней факта + рекурсивный прогноз на 1–14 дней — EX-1</p>
      <ErrorBanner message={error} />

      <div className="card">
        <form
          className="inline"
          onSubmit={(e) => {
            e.preventDefault();
            void build();
          }}
        >
          <label className="field" htmlFor="fc-store">
            Магазин
            <select
              id="fc-store"
              value={storeId}
              onChange={(e) => setStoreId(e.target.value)}
              required
            >
              <option value="" disabled>
                выберите магазин
              </option>
              {stores.map((s) => (
                <option key={s.id} value={String(s.id)}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field" htmlFor="fc-product">
            Товар
            <select
              id="fc-product"
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              required
            >
              <option value="" disabled>
                выберите товар
              </option>
              {products.map((p) => (
                <option key={p.id} value={String(p.id)}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field" htmlFor="fc-days">
            Дней (1–14)
            <input
              id="fc-days"
              type="number"
              min={1}
              max={14}
              step={1}
              value={days}
              onChange={(e) => setDays(e.target.value)}
            />
          </label>
          <button className="primary" type="submit" disabled={loading}>
            {loading ? "Строим…" : "Построить прогноз"}
          </button>
          <button
            className="ghost"
            type="button"
            disabled={loading}
            onClick={() => setRetraining(true)}
          >
            Переобучить модель
          </button>
        </form>
      </div>

      {result !== null && history !== null && (
        <div className="card">
          <p style={{ margin: "0 0 10px" }}>
            <span className="muted">модель:</span> <strong>{result.model}</strong>
          </p>
          <WarningBanner message={result.warning} />
          <Line
            data={forecastChartData(
              history,
              result.forecast,
              result.model !== "lightgbm",
            )}
            options={{
              responsive: true,
              interaction: { mode: "index", intersect: false },
              scales: { y: { beginAtZero: true } },
              plugins: { legend: { labels: { boxWidth: 12 } } },
            }}
          />
        </div>
      )}
      {result === null && history === null && !loading && (
        <p className="muted">
          Выберите магазин и товар — график покажет последние 28 дней факта
          и прогноз вперёд.
        </p>
      )}

      {retraining && (
        <ConfirmModal
          title="Переобучить модель?"
          body="Модель переобучится на всей накопленной истории. Это займёт несколько секунд."
          confirmLabel="Переобучить"
          onConfirm={() => void confirmRetrain()}
          onCancel={() => setRetraining(false)}
        />
      )}
      <Toast message={toast} />
    </section>
  );
}
