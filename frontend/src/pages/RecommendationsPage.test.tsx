/**
 * Тесты экрана «Рекомендации»: статусы → правильные бейджи, строка «заказать»
 * подсвечена, параметры уходят в запрос, кросс-ошибка L+H — баннером.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import RecommendationsPage from "./RecommendationsPage";

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

const LIST = {
  generated_at: "2026-10-19T12:00:00",
  service_level: 0.95,
  lead_time_days: 3,
  horizon_days: 7,
  warning: null,
  recommendations: [
    {
      product_id: 1,
      product_name: "Сахар",
      status: "order",
      warehouse_quantity: 10,
      forecast_demand: 40.0,
      safety_stock: 12.3,
      order_quantity: 43,
      model: "lightgbm",
    },
    {
      product_id: 2,
      product_name: "Соль",
      status: "sufficient",
      warehouse_quantity: 100,
      forecast_demand: 40.0,
      safety_stock: 12.3,
      order_quantity: 0,
      model: "lightgbm",
    },
    {
      product_id: 3,
      product_name: "Кофе",
      status: "cold_start",
      warehouse_quantity: 5,
      forecast_demand: null,
      safety_stock: null,
      order_quantity: null,
      model: null,
    },
  ],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("RecommendationsPage", () => {
  it("renders status badges and highlights order rows", async () => {
    mockApi([{ method: "GET", suffix: "/api/recommendations", status: 200, body: LIST }]);

    render(<RecommendationsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Рассчитать" }));

    expect(await screen.findByText("заказать")).toBeTruthy();
    expect(screen.getByText("достаточно")).toBeTruthy();
    expect(screen.getByText("холодный старт")).toBeTruthy();
    expect(screen.getByText("43")).toBeTruthy();
    const row = screen.getByText("Сахар").closest("tr") as HTMLElement;
    expect(row.className).toContain("row-order");
    const coldRow = screen.getByText("Кофе").closest("tr") as HTMLElement;
    expect(coldRow.className).not.toContain("row-order");
  });

  it("passes custom policy params into the query string", async () => {
    const calls = mockApi([
      { method: "GET", suffix: "/api/recommendations", status: 200, body: LIST },
    ]);

    render(<RecommendationsPage />);
    fireEvent.change(screen.getByLabelText("Уровень сервиса"), {
      target: { value: "0.99" },
    });
    fireEvent.change(screen.getByLabelText("Поставка, дней"), {
      target: { value: "5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Рассчитать" }));

    await screen.findByText("заказать");
    const get = calls.find((c) => (c.init?.method ?? "GET") === "GET");
    expect(get?.url).toContain("service_level=0.99");
    expect(get?.url).toContain("lead_time_days=5");
  });

  it("relays the cross-rule L+H error into the banner", async () => {
    mockApi([
      {
        method: "GET",
        suffix: "/api/recommendations",
        status: 422,
        body: {
          detail:
            "Сумма времени поставки и горизонта обзора не должна превышать 14 дней — доказанный горизонт модели (получено: 8 + 7)",
        },
      },
    ]);

    render(<RecommendationsPage />);
    fireEvent.change(screen.getByLabelText("Поставка, дней"), {
      target: { value: "8" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Рассчитать" }));

    expect(await screen.findByText(/не должна превышать 14/)).toBeTruthy();
    expect(screen.queryByText("заказать")).toBeNull();
  });
});
