import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { Product, Store, StoreRequest } from "../api/types";
import { Badge, requestBadge } from "../components/Badge";
import { ErrorBanner } from "../components/banners";
import { ConfirmModal, Toast, useToast } from "../components/Modal";
import { EmptyState, Spinner } from "../components/states";

/**
 * Заявки: FR-8 (подать), FR-9 (обработать — модалка, BR-7 баннером),
 * FR-10 (список). Селекторы заполнены списками магазинов/товаров;
 * на сервер уходят ИМЕНА (контракт FR-8), не id.
 */
function fmt(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
}

export default function RequestsPage() {
  const [requests, setRequests] = useState<StoreRequest[] | null>(null);
  const [stores, setStores] = useState<Store[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [storeName, setStoreName] = useState("");
  const [productName, setProductName] = useState("");
  const [qty, setQty] = useState("");
  const [processing, setProcessing] = useState<StoreRequest | null>(null);
  const { toast, show } = useToast();

  const load = useCallback(async () => {
    try {
      const [reqList, storeList, productList] = await Promise.all([
        api.get<StoreRequest[]>("/requests"),
        api.get<Store[]>("/stores"),
        api.get<Product[]>("/products"),
      ]);
      setRequests(reqList);
      setStores(storeList);
      setProducts(productList);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить заявки");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function submitRequest(e: FormEvent) {
    e.preventDefault();
    const quantity = Number(qty);
    if (!Number.isInteger(quantity)) {
      setError("Количество должно быть целым числом");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.post("/requests", { store_name: storeName, product_name: productName, quantity });
      setQty("");
      show("Заявка подана");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка операции");
    } finally {
      setBusy(false);
    }
  }

  async function confirmProcess() {
    if (!processing) return;
    const target = processing;
    setProcessing(null);
    setBusy(true);
    setError(null);
    try {
      await api.post(`/requests/${target.number}/process`);
      show(`Заявка №${target.number} обработана`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка операции");
    } finally {
      setBusy(false);
    }
  }

  const formDisabled = stores.length === 0 || products.length === 0;

  return (
    <section>
      <h1>Заявки магазинов</h1>
      <p className="page-sub">Подача, обработка и список заявок — FR-8, FR-9, FR-10</p>
      <ErrorBanner message={error} />

      {requests === null ? (
        <Spinner />
      ) : (
        <div className="card">
          {requests.length === 0 ? (
            <EmptyState text="Заявок пока нет" />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>№</th>
                  <th>Магазин</th>
                  <th>Товар</th>
                  <th className="num">Кол-во</th>
                  <th>Статус</th>
                  <th>Подана</th>
                  <th>Обработана</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {requests.map((r) => {
                  const badge = requestBadge(r.status);
                  return (
                    <tr key={r.number}>
                      <td>№{r.number}</td>
                      <td>{r.store_name}</td>
                      <td>{r.product_name}</td>
                      <td className="num">{r.requested_quantity}</td>
                      <td>
                        <Badge tone={badge.tone}>{badge.label}</Badge>
                      </td>
                      <td>{fmt(r.submitted_at)}</td>
                      <td>{fmt(r.processed_at)}</td>
                      <td style={{ textAlign: "right" }}>
                        {r.status === "подана" && (
                          <button
                            className="ghost"
                            disabled={busy}
                            onClick={() => setProcessing(r)}
                          >
                            Обработать
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Новая заявка</h2>
        {formDisabled ? (
          <p className="muted" style={{ margin: 0 }}>
            Нужны хотя бы один магазин и один товар в списках.
          </p>
        ) : (
          <form className="inline" onSubmit={submitRequest}>
            <label className="field" htmlFor="req-store">
              Магазин
              <select
                id="req-store"
                value={storeName}
                onChange={(e) => setStoreName(e.target.value)}
                required
              >
                <option value="" disabled>
                  выберите магазин
                </option>
                {stores.map((s) => (
                  <option key={s.id} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field" htmlFor="req-product">
              Товар
              <select
                id="req-product"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                required
              >
                <option value="" disabled>
                  выберите товар
                </option>
                {products.map((p) => (
                  <option key={p.id} value={p.name}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field" htmlFor="req-qty">
              Количество
              <input
                id="req-qty"
                type="number"
                min={1}
                step={1}
                value={qty}
                onChange={(e) => setQty(e.target.value)}
                required
              />
            </label>
            <button className="primary" type="submit" disabled={busy}>
              Подать заявку
            </button>
          </form>
        )}
      </div>

      {processing !== null && (
        <ConfirmModal
          title={`Обработать заявку №${processing.number}?`}
          body={`${processing.store_name}: ${processing.product_name} — ${processing.requested_quantity} шт. Товар будет отпущен со склада в магазин; при нехватке остатка операция отклонится (BR-7).`}
          confirmLabel="Обработать"
          onConfirm={() => void confirmProcess()}
          onCancel={() => setProcessing(null)}
        />
      )}
      <Toast message={toast} />
    </section>
  );
}
