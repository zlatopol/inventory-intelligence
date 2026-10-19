import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, namePath } from "../api/client";
import type { Store, StoreStock } from "../api/types";
import { ErrorBanner } from "../components/banners";
import { ConfirmModal, Toast, useToast } from "../components/Modal";
import { EmptyState, Spinner } from "../components/states";

/**
 * Магазины: FR-3 (добавить), FR-4 (удалить, BR-8 баннером), FR-11 (список)
 * + секция FR-7 «Товары по магазинам» (EL-21: пустой магазин показывается).
 */
export default function StoresPage() {
  const [stores, setStores] = useState<Store[] | null>(null);
  const [stock, setStock] = useState<StoreStock[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [deleting, setDeleting] = useState<Store | null>(null);
  const { toast, show } = useToast();

  const load = useCallback(async () => {
    try {
      const [storeList, stockList] = await Promise.all([
        api.get<Store[]>("/stores"),
        api.get<StoreStock[]>("/stores/stock"),
      ]);
      setStores(storeList);
      setStock(stockList);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить магазины");
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
      await api.post("/stores", { name }); // BR-1/BR-4 решает сервис
      setName("");
      show("Магазин добавлен в список");
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
      await api.del(`/stores/${namePath(target.name)}`);
      show(`«${target.name}» удалён из списка`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка операции");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h1>Магазины</h1>
      <p className="page-sub">
        Список магазинов и товары по магазинам — FR-3, FR-4, FR-7, FR-11
      </p>
      <ErrorBanner message={error} />

      {stores === null ? (
        <Spinner />
      ) : (
        <>
          <div className="card">
            {stores.length === 0 ? (
              <EmptyState text="Список магазинов пуст — добавьте первый магазин" />
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Название</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {stores.map((s) => (
                    <tr key={s.id}>
                      <td>{s.name}</td>
                      <td style={{ textAlign: "right" }}>
                        <button
                          className="danger"
                          disabled={busy}
                          onClick={() => setDeleting(s)}
                        >
                          Удалить
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="card">
            <h2 style={{ marginTop: 0 }}>Новый магазин</h2>
            <form className="inline" onSubmit={submitAdd}>
              <label className="field" htmlFor="store-name">
                Название
                <input
                  id="store-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Например: Магнит"
                  required
                />
              </label>
              <button className="primary" type="submit" disabled={busy}>
                Добавить магазин
              </button>
            </form>
          </div>

          <h2>Товары по магазинам (FR-7)</h2>
          {stock.length === 0 ? (
            <EmptyState text="Магазинов пока нет" />
          ) : (
            stock.map((s) => (
              <div className="card" key={s.name}>
                <h2 style={{ margin: "0 0 8px" }}>{s.name}</h2>
                {s.products.length === 0 ? (
                  <p className="muted" style={{ margin: 0 }}>
                    (нет товаров)
                  </p>
                ) : (
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Товар</th>
                        <th className="num">Количество, шт.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {s.products.map((p) => (
                        <tr key={p.name}>
                          <td>{p.name}</td>
                          <td className="num">{p.quantity}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            ))
          )}
        </>
      )}

      {deleting !== null && (
        <ConfirmModal
          title="Удалить магазин?"
          body={`«${deleting.name}» будет удалён из списка. Удаление невозможно, пока есть заявки со статусом «подана» (BR-8).`}
          confirmLabel="Да, удалить"
          onConfirm={() => void confirmDelete()}
          onCancel={() => setDeleting(null)}
        />
      )}
      <Toast message={toast} />
    </section>
  );
}
