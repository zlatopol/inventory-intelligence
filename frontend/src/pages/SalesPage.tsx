import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { Product, Sale, SaleProductOption, Store } from "../api/types";
import { ErrorBanner } from "../components/banners";
import { ConfirmModal, Toast, useToast } from "../components/Modal";
import { EmptyState, Spinner } from "../components/states";

function localDateTimeValue() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

function fmt(iso: string) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
}

export default function SalesPage() {
  const [sales, setSales] = useState<Sale[] | null>(null);
  const [stores, setStores] = useState<Store[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [saleProducts, setSaleProducts] = useState<SaleProductOption[]>([]);
  const [storeId, setStoreId] = useState("");
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [soldAt, setSoldAt] = useState(localDateTimeValue);
  const [filterStore, setFilterStore] = useState("");
  const [filterProduct, setFilterProduct] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reversing, setReversing] = useState<Sale | null>(null);
  const { toast, show } = useToast();

  const load = useCallback(async () => {
    try {
      const [storeList, productList, saleList] = await Promise.all([
        api.get<Store[]>("/stores"),
        api.get<Product[]>("/products"),
        api.get<Sale[]>("/sales"),
      ]);
      setStores(storeList);
      setProducts(productList);
      setSales(saleList);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить данные продаж");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const selectedProduct = saleProducts.find((p) => p.product_id === Number(productId));
  const availableStock = selectedProduct?.quantity ?? 0;

  const refreshSaleProducts = useCallback(async (targetStoreId: string = storeId) => {
    if (!targetStoreId) {
      setSaleProducts([]);
      return;
    }
    const items = await api.get<SaleProductOption[]>(`/sales/products?store_id=${targetStoreId}`);
    setSaleProducts(items);
  }, [storeId]);

  useEffect(() => {
    setProductId("");
    let cancelled = false;
    if (!storeId) {
      setSaleProducts([]);
      return;
    }
    api.get<SaleProductOption[]>(`/sales/products?store_id=${storeId}`)
      .then((items) => { if (!cancelled) setSaleProducts(items); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : "Не удалось загрузить остатки магазина"); });
    return () => { cancelled = true; };
  }, [storeId]);

  async function submitSale(e: FormEvent) {
    e.preventDefault();
    if (!storeId || !productId || !Number.isInteger(Number(quantity)) || Number(quantity) <= 0) {
      setError("Выберите магазин и товар, укажите положительное целое количество.");
      return;
    }
    if (Number(quantity) > availableStock) {
      setError(`Недостаточный остаток: доступно ${availableStock} шт.`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.postWithHeaders<Sale>("/sales", {
        store_id: Number(storeId),
        product_id: Number(productId),
        quantity: Number(quantity),
        sold_at: new Date(soldAt).toISOString(),
      }, { "Idempotency-Key": crypto.randomUUID() });
      setQuantity("1");
      setProductId("");
      setSoldAt(localDateTimeValue());
      show("Продажа зарегистрирована");
      await Promise.all([load(), refreshSaleProducts()]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось зарегистрировать продажу");
      await Promise.all([load(), refreshSaleProducts()]);
    } finally {
      setBusy(false);
    }
  }

  async function confirmReversal() {
    if (!reversing) return;
    const target = reversing;
    setBusy(true);
    setReversing(null);
    setError(null);
    try {
      await api.post(`/sales/${target.id}/reverse`);
      show("Продажа отменена, товар возвращён в остаток");
      await Promise.all([load(), refreshSaleProducts()]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось отменить продажу");
      await Promise.all([load(), refreshSaleProducts()]);
    } finally {
      setBusy(false);
    }
  }

  async function applyFilters() {
    const params = new URLSearchParams();
    if (filterStore) params.set("store_id", filterStore);
    if (filterProduct) params.set("product_id", filterProduct);
    if (filterStatus !== "all") params.set("status", filterStatus);
    if (from) params.set("sold_from", new Date(from).toISOString());
    if (to) params.set("sold_to", new Date(`${to}T23:59:59.999`).toISOString());
    setError(null);
    try {
      setSales(await api.get<Sale[]>(`/sales${params.size ? `?${params.toString()}` : ""}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось отфильтровать историю");
    }
  }

  return (
    <section>
      <h1>Продажи</h1>
      <p className="page-sub">Ручная регистрация продаж и история списаний</p>
      <ErrorBanner message={error} />
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Новая продажа</h2>
        {stores.length === 0 ? (
          <p className="muted">Для регистрации нужен хотя бы один магазин.</p>
        ) : (
          <form className="inline" onSubmit={submitSale}>
            <label className="field" htmlFor="sale-store">Магазин
              <select id="sale-store" value={storeId} onChange={(e) => { setStoreId(e.target.value); setProductId(""); }} required>
                <option value="" disabled>выберите магазин</option>
                {stores.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </label>
            <label className="field" htmlFor="sale-product">Товар
              <select id="sale-product" value={productId} onChange={(e) => setProductId(e.target.value)} required>
                <option value="" disabled>выберите товар</option>
                {saleProducts.map((p) => <option key={p.product_id} value={p.product_id}>{p.product_name} — остаток {p.quantity} шт.</option>)}
              </select>
            </label>
            {storeId && saleProducts.length === 0 && <p className="muted" style={{ margin: 0 }}>В выбранном магазине нет товаров с положительным остатком.</p>}
            <label className="field" htmlFor="sale-qty">Количество
              <input id="sale-qty" type="number" min={1} step={1} max={availableStock || undefined} value={quantity}
                onChange={(e) => setQuantity(e.target.value)} required />
            </label>
            <label className="field" htmlFor="sale-date">Дата и время продажи
              <input id="sale-date" type="datetime-local" value={soldAt} onChange={(e) => setSoldAt(e.target.value)} required />
            </label>
            {productId && <p className="muted" style={{ margin: 0, alignSelf: "end" }}>Доступно: {availableStock} шт.</p>}
            <button className="primary" type="submit" disabled={busy || !storeId || !productId || availableStock === 0 || Number(quantity) > availableStock}>
              Зарегистрировать продажу
            </button>
          </form>
        )}
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>История продаж</h2>
        <form className="inline" onSubmit={(e) => { e.preventDefault(); void applyFilters(); }}>
          <label className="field" htmlFor="filter-store">Магазин
            <select id="filter-store" value={filterStore} onChange={(e) => setFilterStore(e.target.value)}>
              <option value="">Все магазины</option>{stores.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
          <label className="field" htmlFor="filter-product">Товар
            <select id="filter-product" value={filterProduct} onChange={(e) => setFilterProduct(e.target.value)}>
              <option value="">Все товары</option>{products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </label>
          <label className="field" htmlFor="filter-from">С даты
            <input id="filter-from" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </label>
          <label className="field" htmlFor="filter-to">По дату
            <input id="filter-to" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          </label>
          <label className="field" htmlFor="filter-status">Статус
            <select id="filter-status" value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="all">Все</option><option value="active">Активные</option><option value="cancelled">Отменённые</option>
            </select>
          </label>
          <button className="primary" type="submit">Применить</button>
          <button className="ghost" type="button" onClick={() => { setFilterStore(""); setFilterProduct(""); setFilterStatus("all"); setFrom(""); setTo(""); void api.get<Sale[]>("/sales").then(setSales).catch((e) => setError(e.message)); }}>Сбросить</button>
        </form>
        {sales === null ? <Spinner /> : sales.length === 0 ? <EmptyState text="Продаж по выбранным условиям нет" /> : (
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead><tr><th>Продана</th><th>Зарегистрирована</th><th>Магазин</th><th>Товар</th><th className="num">Кол-во</th><th>Статус</th><th /></tr></thead>
              <tbody>{sales.map((sale) => <tr key={sale.id}>
                <td>{fmt(sale.sold_at)}</td><td>{fmt(sale.created_at)}</td><td>{sale.store_name}</td><td>{sale.product_name}</td>
                <td className="num">{sale.quantity}</td>
                <td>{sale.status === "cancelled" ? "Отменена" : "Активна"}</td>
                <td>{sale.status === "active" && <button className="ghost" disabled={busy} onClick={() => setReversing(sale)}>Отменить</button>}</td>
              </tr>)}</tbody>
            </table>
          </div>
        )}
      </div>
      <Toast message={toast} />
      {reversing && <ConfirmModal
        title="Отменить продажу?"
        body={`Вернуть ${reversing.quantity} шт. товара «${reversing.product_name}» в текущий остаток магазина «${reversing.store_name}»?`}
        confirmLabel="Подтвердить отмену"
        onConfirm={() => void confirmReversal()}
        onCancel={() => setReversing(null)}
      />}
    </section>
  );
}
