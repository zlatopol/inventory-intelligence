/**
 * Тесты API-клиента: маппинг ошибок (detail → ApiError), сеть,
 * кодирование имён в пути. Глобальный fetch подменяется двойником —
 * аналогия Fake-сервисов в CLI-тестах.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, namePath } from "./client";

function mockFetch(status: number, body?: unknown): ReturnType<typeof vi.fn> {
  const fn = vi.fn().mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("returns parsed JSON on success", async () => {
    const fn = mockFetch(200, { name: "Сахар", id: 1 });
    await api.get("/products");

    expect(fn).toHaveBeenCalledWith(
      "/api/products",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("throws ApiError with the domain detail text", async () => {
    mockFetch(409, { detail: "Товар с таким названием уже есть (BR-2)" });

    const err = (await api.post("/products", { name: "Сахар" }).catch(
      (e) => e,
    )) as ApiError;

    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toContain("BR-2");
    expect(err.status).toBe(409);
  });

  it("prefers the first message of 422 validation lists", async () => {
    mockFetch(422, {
      detail: [
        { type: "int_parsing", msg: "Input should be a valid integer" },
      ],
    });

    const err = (await api.get("/forecast?days=abc").catch(
      (e) => e,
    )) as ApiError;

    expect(err.message).toContain("valid integer");
  });

  it("maps network failure to a human message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("fetch failed")),
    );

    const err = (await api.get("/products").catch(
      (e) => e,
    )) as ApiError;

    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(0);
    expect(err.message).toContain("недоступен");
  });

  it("encodes cyrillic names with spaces for URL paths", () => {
    expect(namePath("Сахар 2")).toBe("%D0%A1%D0%B0%D1%85%D0%B0%D1%80%202");
  });

  it("does not send a body on GET", async () => {
    const fn = mockFetch(200, []);
    await api.get("/stores");

    const [, init] = fn.mock.calls[0] as [string, RequestInit | undefined];
    expect(init?.body).toBeUndefined();
  });
});
