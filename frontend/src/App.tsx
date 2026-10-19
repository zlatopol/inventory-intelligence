import { NavLink, Route, Routes } from "react-router-dom";
import AnalyticsPage from "./pages/AnalyticsPage";
import ForecastPage from "./pages/ForecastPage";
import ProductsPage from "./pages/ProductsPage";
import RecommendationsPage from "./pages/RecommendationsPage";
import RequestsPage from "./pages/RequestsPage";
import StoresPage from "./pages/StoresPage";

/**
 * Каркас приложения: тёмный сайдбар (палитра №4745) + контентная область.
 * Шесть разделов согласованы на Стадии 4: склад, магазины (+FR-7 секцией),
 * заявки, прогноз, рекомендации, аналитика.
 */
export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">СНАБЖЕНИЕ</div>
        <nav>
          <NavLink to="/">Склад</NavLink>
          <NavLink to="/stores">Магазины</NavLink>
          <NavLink to="/requests">Заявки</NavLink>
          <NavLink to="/forecast">Прогноз</NavLink>
          <NavLink to="/recommendations">Рекомендации</NavLink>
          <NavLink to="/analytics">Аналитика</NavLink>
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<ProductsPage />} />
          <Route path="/stores" element={<StoresPage />} />
          <Route path="/requests" element={<RequestsPage />} />
          <Route path="/forecast" element={<ForecastPage />} />
          <Route path="/recommendations" element={<RecommendationsPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
        </Routes>
      </main>
    </div>
  );
}
