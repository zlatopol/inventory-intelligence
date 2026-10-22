import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, namePath } from "../api/client";
import type { Product } from "../api/types";
import { ErrorBanner } from "../components/banners";
import { ConfirmModal, Toast, useToast } from "../components/Modal";
import { EmptyState, Spinner } from "../components/states";

/**
 * Склад: FR-1 (добавить), FR-2 (удалить), FR-5 (поступление), FR-6 (список).
 *
 * Тонкий клиент (ADR-0008): формы шлют СЫРОЙ ввод — D-1/BR-1/BR-2 решает
 * сервис, его сообщение показывается баннером как есть. После каждой
 * записи — re-fetch списка (решение 4.1): на экране всегда правда сервера.
 */
export default function ProductsPage() {
  const [products, setProducts] = useState<Product[] | null>(null);
  const [visibleCount, setVisibleCount] = useState(10);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [receiptName, setReceiptName] = useState("");
  const [receiptQty, setReceiptQty] = useState("");
  const [deleting, setDeleting] = useState<Product | null>(null);
  const { toast, show } = useToast();

  const load = useCallback(async () => {
    try {
      setProducts(await api.get<Product[]>("/products"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить склад");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function submitAdd(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/products", { name }); // сырой ввод: правила решает сервис
      setVisibleCount(10);
      setName("");
      show("Товар добавлен в складской список");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка операции");
    } finally {
      setBusy(false);
    }
  }

  async function submitReceipt(e: FormEvent) {
    e.preventDefault();
    const quantity = Number(receiptQty);
    if (!Number.isInteger(quantity)) {
      // механический парсинг, аналог ask_int в CLI; BR-5 остаётся сервису
      setError("Количество должно быть целым числом");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.post(`/products/${namePath(receiptName)}/receipts`, { quantity });
      setReceiptQty("");
      show(`Поступление учтено: +${quantity}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка операции");
    } finally {
      setBusy(false);
    }
  }

  async function confirmDelete() {
    if (!deleting) return;
    const target = deleting;
    setDeleting(null);
    setBusy(true);
    setError(null);
    try {
      await api.del(`/products/${namePath(target.name)}`);
      show(`«${target.name}» удалён из складского списка`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка операции");
    } finally {
      setBusy(false);
    }
  }

  const visibleProducts = (products ?? []).slice(0, visibleCount);
  return (
    <section>
      <h1>Склад</h1>
      <p className="page-sub">
        Складской список, поступления и удаление товаров — FR-1, FR-2, FR-5, FR-6
      </p>
      <ErrorBanner message={error} />

      {products === null ? (
        <Spinner />
      ) : (
        <>
          <div className="card">
            <h2 style={{ marginTop: 0 }}>Новый товар</h2>
            <form className="inline" onSubmit={submitAdd}>
              <label className="field" htmlFor="product-name">
                Название
                <input
                  id="product-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Например: Сахар"
                  required
                />
              </label>
              <button className="primary" type="submit" disabled={busy}>
                Добавить товар
              </button>
            </form>
          </div>

          <div className="card">
            <h2 style={{ marginTop: 0 }}>Поступление товара</h2>
            {products.length === 0 ? (
              <p className="muted" style={{ margin: 0 }}>
                Сначала добавьте товар в складской список.
              </p>
            ) : (
              <form className="inline" onSubmit={submitReceipt}>
                <label className="field" htmlFor="receipt-product">
                  Товар
                  <select
                    id="receipt-product"
                    value={receiptName}
                    onChange={(e) => setReceiptName(e.target.value)}
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
                <label className="field" htmlFor="receipt-qty">
                  Количество
                  <input
                    id="receipt-qty"
                    type="number"
                    min={1}
                    step={1}
                    value={receiptQty}
                    onChange={(e) => setReceiptQty(e.target.value)}
                    required
                  />
                </label>
                <button className="primary" type="submit" disabled={busy}>
                  Учесть поступление
                </button>
              </form>
            )}
          </div>


          <div className="card">
            {products.length === 0 ? (
              <EmptyState text="Склад пуст — добавьте первый товар" />
            ) : (
              <>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Название</th>
                      <th className="num">Количество, шт.</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {visibleProducts.map((p) => (
                      <tr key={p.id}>
                        <td>{p.name}</td>
                        <td className="num">{p.warehouse_quantity}</td>
                        <td style={{ textAlign: "right" }}>
                          <button
                            className="danger"
                            disabled={busy}
                            onClick={() => setDeleting(p)}
                          >
                            Удалить
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {visibleCount < products.length && (
                  <button
                    className="ghost"
                    style={{ marginTop: 12 }}
                    onClick={() => setVisibleCount((count) => count + 10)}
                  >
                    Показать ещё 10
                  </button>
                )}
              </>
            )}
          </div>

        </>
      )}

      {deleting !== null && (
        <ConfirmModal
          title="Удалить товар?"
          body={`«${deleting.name}» будет удалён из складского списка. Удаление возможно только при нулевом остатке на складе (BR-3).`}
          confirmLabel="Да, удалить"
          onConfirm={() => void confirmDelete()}
          onCancel={() => setDeleting(null)}
        />
      )}
      <Toast message={toast} />
    </section>
  );
}
