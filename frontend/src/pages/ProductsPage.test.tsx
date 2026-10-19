/**
 * Тесты экрана «Склад»: поведение тонкого клиента (ADR-0008) — таблица из
 * API, сырой ввод уходит как есть, BR-ошибка показывается баннером,
 * удаление — через подтверждение. Глобальный fetch подменён двойником.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ProductsPage from "./ProductsPage";

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

const SUGAR = { id: 1, name: "Сахар", warehouse_quantity: 5 };

afterEach(() => {
  cleanup(); // vitest без globals:true — авто-cleanup RTL не работает, DOM копится
  vi.unstubAllGlobals();
});

describe("ProductsPage", () => {
  it("renders the warehouse table from the API", async () => {
    mockApi([{ method: "GET", suffix: "/api/products", status: 200, body: [SUGAR] }]);

    render(<ProductsPage />);

    expect(await screen.findByRole("cell", { name: "Сахар" })).toBeTruthy();
    expect(screen.getByRole("cell", { name: "5" })).toBeTruthy();
  });

  it("shows the empty state for an empty warehouse", async () => {
    mockApi([{ method: "GET", suffix: "/api/products", status: 200, body: [] }]);

    render(<ProductsPage />);

    expect(
      await screen.findByText("Склад пуст — добавьте первый товар"),
    ).toBeTruthy();
  });

  it("sends the raw name on submit and refetches the list", async () => {
    const calls = mockApi([
      { method: "GET", suffix: "/api/products", status: 200, body: [SUGAR] },
      { method: "POST", suffix: "/api/products", status: 201, body: SUGAR },
    ]);

    render(<ProductsPage />);
    fireEvent.change(await screen.findByRole("textbox", { name: "Название" }), {
      target: { value: "  Молоко  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Добавить товар" }));

    await waitFor(() => {
      const post = calls.find((c) => c.init?.method === "POST");
      expect(post?.init?.body).toBe(JSON.stringify({ name: "  Молоко  " }));
    });
    // re-fetch после записи (решение 4.1)
    await waitFor(() => {
      const gets = calls.filter((c) => (c.init?.method ?? "GET") === "GET");
      expect(gets.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("relays a BR error into the banner and keeps the form filled", async () => {
    mockApi([
      { method: "GET", suffix: "/api/products", status: 200, body: [SUGAR] },
      {
        method: "POST",
        suffix: "/api/products",
        status: 409,
        body: { detail: "Товар с таким названием уже есть в складском списке (BR-2)" },
      },
    ]);

    render(<ProductsPage />);
    fireEvent.change(await screen.findByRole("textbox", { name: "Название" }), {
      target: { value: "молоко" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Добавить товар" }));

    expect(await screen.findByText(/BR-2/)).toBeTruthy();
    const input = screen.getByRole("textbox", { name: "Название" }) as HTMLInputElement;
    expect(input.value).toBe("молоко");
  });

  it("asks for confirmation before deletion and sends the encoded name", async () => {
    const calls = mockApi([
      { method: "GET", suffix: "/api/products", status: 200, body: [SUGAR] },
      { method: "DELETE", suffix: "/api/products/", status: 204 },
    ]);

    render(<ProductsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Удалить" }));

    expect(screen.getByText("Удалить товар?")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Да, удалить" }));

    await waitFor(() => {
      const del = calls.find((c) => c.init?.method === "DELETE");
      expect(del?.url).toContain(encodeURIComponent("Сахар"));
    });
  });
});
