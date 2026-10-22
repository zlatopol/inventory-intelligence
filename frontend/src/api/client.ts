/**
 * API-клиент: единственное место, где фронт знает, КАК говорить с бэкендом.
 *
 * ADR-0008 (тонкий клиент): все ошибки API приходят текстом в `detail`
 * (DomainError → JSON). Клиент достаёт их и заворачивает в ApiError —
 * страницы показывают `err.message` как есть, без своих интерпретаций.
 *
 * Базовый путь /api зашит: в dev его проксирует Vite, в прод FastAPI
 * сам отдаёт и API, и статику — CORS не возникает (ADR-0009).
 */

const BASE = "/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(method: string, path: string, body?: unknown, extraHeaders?: Record<string, string>): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers: { ...(body !== undefined ? { "Content-Type": "application/json" } : {}), ...extraHeaders },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    // сеть недоступна / сервер упал — fetch бросает TypeError, не Response
    throw new ApiError(0, "Сервер недоступен. Проверьте, что API запущен.");
  }

  if (!response.ok) {
    let message = `Ошибка запроса (${response.status})`;
    try {
      const data = (await response.json()) as { detail?: unknown };
      if (typeof data.detail === "string") {
        message = data.detail; // DomainError-тексты уже человекочитаемые (EL-3)
      } else if (Array.isArray(data.detail)) {
        // 422 FastAPI-валидации: список полей — берём первое, читаемо для человека
        const first = data.detail[0] as { msg?: string } | undefined;
        if (first?.msg) message = first.msg;
      }
    } catch {
      // тело не JSON — останется дефолтное сообщение
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** Имя в путь URL: кириллица/пробелы обязаны быть закодированы. */
export function namePath(name: string): string {
  return encodeURIComponent(name);
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  postWithHeaders: <T>(path: string, body: unknown, headers: Record<string, string>) => request<T>("POST", path, body, headers),
  del: (path: string) => request<void>("DELETE", path),
};
