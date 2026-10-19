/**
 * Тесты экрана «Прогноз»: логика данных графика (чистая функция — без
 * canvas) + поведение страницы (Line замокан; проверяем baseline-честность:
 * пунктир решается в НАШЕМ коде, а не внутри Chart.js).
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { forecastChartData } from "./ForecastPage";

vi.mock("react-chartjs-2", () => ({
  Line: () => <div data-testid="chart" />,
}));

import ForecastPage from "./ForecastPage";

interface Route {
  method: string;
  suffix: string;
  status: number;
  body?: unknown;
}

function mockApi(routes: Route[]) {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      calls.push({ url, init });
      const method = init?.method ?? "GET";
      const route = routes.find(
        (r) => r.method === method && url.includes(r.suffix),
      );
      return Promise.resolve(
        new Response(route ? JSON.stringify(route.body ?? {}) : "{}", {
          status: route ? route.status : 404,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }),
  );
  return calls;
}

const STORES = [{ id: 7, name: "Магазин А" }];
const PRODUCTS = [{ id: 42, name: "Сахар", warehouse_quantity: 0 }];
const FORECAST = {
  store_id: 7,
  product_id: 42,
  generated_at: "2026-10-19T12:00:00",
  model: "baseline_moving_average_7",
  warning: "история 5 дн. < 30: прогноз даёт baseline",
  forecast: [
    { date: "2026-10-20T00:00:00", demand: 12.0 },
    { date: "2026-10-21T00:00:00", demand: 12.5 },
  ],
};
const HISTORY = {
  store_id: 7,
  product_id: 42,
  days: 2,
  history: [
    { date: "2026-10-18T00:00:00", demand: 10 },
    { date: "2026-10-19T00:00:00", demand: 14 },
  ],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("forecastChartData (pure)", () => {
  it("joins labels and pads each series with nulls to a common axis", () => {
    const data = forecastChartData(HISTORY.history, FORECAST.forecast, false);

    expect(data.labels).toEqual(["10-18", "10-19", "10-20", "10-21"]);
    expect(data.datasets[0].data).toEqual([10, 14, null, null]);
    // стык: прогнозная серия стартует с последней точки факта
    expect(data.datasets[1].data).toEqual([null, 14, 12.0, 12.5]);
  });

  it("dashes the forecast line exactly for baseline (honesty, Stage 5.3)", () => {
    const dashed = forecastChartData(HISTORY.history, FORECAST.forecast, true);
    const solid = forecastChartData(HISTORY.history, FORECAST.forecast, false);

    expect(dashed.datasets[1].borderDash).toEqual([6, 6]);
    expect(solid.datasets[1].borderDash).toBeUndefined();
  });
});

describe("ForecastPage", () => {
  it("builds forecast and shows baseline warning with the model tag", async () => {
    mockApi([
      { method: "GET", suffix: "/api/stores", status: 200, body: STORES },
      { method: "GET", suffix: "/api/products", status: 200, body: PRODUCTS },
      { method: "GET", suffix: "/api/forecast/history", status: 200, body: HISTORY },
      { method: "GET", suffix: "/api/forecast?", status: 200, body: FORECAST },
    ]);

    render(<ForecastPage />);
    fireEvent.change(await screen.findByRole("combobox", { name: "Магазин" }), {
      target: { value: "7" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "Товар" }), {
      target: { value: "42" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Построить прогноз" }));

    expect(await screen.findByText("baseline_moving_average_7")).toBeTruthy();
    expect(screen.getByText(/история 5 дн/)).toBeTruthy();
    expect(screen.getByTestId("chart")).toBeTruthy();
  });

  it("relays the unknown-pair 404 into the banner", async () => {
    mockApi([
      { method: "GET", suffix: "/api/stores", status: 200, body: STORES },
      { method: "GET", suffix: "/api/products", status: 200, body: PRODUCTS },
      {
        method: "GET",
        suffix: "/api/forecast?",
        status: 404,
        body: { detail: "В истории событий нет пары store=7, product=42" },
      },
    ]);

    render(<ForecastPage />);
    fireEvent.change(await screen.findByRole("combobox", { name: "Магазин" }), {
      target: { value: "7" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "Товар" }), {
      target: { value: "42" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Построить прогноз" }));

    expect(await screen.findByText(/нет пары/)).toBeTruthy();
    await waitFor(() => {
      expect(screen.queryByTestId("chart")).toBeNull();
    });
  });
});
