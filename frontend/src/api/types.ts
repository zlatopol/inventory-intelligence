/**
 * TS-типы — рукописные зеркала Pydantic-схем (ADR-0009: кодогенерация для
 * ~10 интерфейсов избыточна). Рассинхрон ловится глазами на ревью и
 * рантаймом на стыке; при росте API — перейти на openapi-generator.
 */

export interface Product {
  id: number;
  name: string;
  warehouse_quantity: number;
}

export interface Store {
  id: number;
  name: string;
}

export interface ProductStock {
  name: string;
  quantity: number;
}

export interface StoreStock {
  name: string;
  products: ProductStock[];
}

export type RequestStatus = "подана" | "обработана";

export interface Sale {
  id: number; store_id: number; store_name: string; product_id: number; product_name: string;
  quantity: number; sold_at: string; created_at: string;
  status: "active" | "cancelled"; reversal_event_id: number | null;
}
export interface SaleReversal { sale_id: number; reversal_event_id: number; store_stock: number; }

export interface StoreRequest {
  number: number;
  status: RequestStatus;
  store_name: string;
  product_name: string;
  requested_quantity: number;
  submitted_at: string;
  processed_at: string | null;
}

export interface ForecastDay {
  date: string;
  demand: number;
}

export interface Forecast {
  store_id: number;
  product_id: number;
  generated_at: string;
  model: string;
  warning: string | null;
  forecast: ForecastDay[];
}

export interface HistoryDay {
  date: string;
  demand: number;
}

export interface History {
  store_id: number;
  product_id: number;
  days: number;
  history: HistoryDay[];
}

export type RecommendationStatus = "order" | "sufficient" | "cold_start";

export interface Recommendation {
  product_id: number;
  product_name: string;
  status: RecommendationStatus;
  warehouse_quantity: number;
  forecast_demand: number | null;
  safety_stock: number | null;
  order_quantity: number | null;
  model: string | null;
}

export interface RecommendationList {
  generated_at: string;
  service_level: number;
  lead_time_days: number;
  horizon_days: number;
  warning: string | null;
  recommendations: Recommendation[];
}

export interface RetrainResult {
  status: string;
  trained_at: string;
}

export interface SaleProductOption {
  product_id: number;
  product_name: string;
  quantity: number;
}
