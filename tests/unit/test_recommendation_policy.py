"""Unit tests: инвентаризационная политика (app/recommendations/policy.py).

Чистая математика без БД: z-квантиль, формула SS, округление Q (включая
гвардию плавающего шума) и правила валидации параметров (EL-3).
"""
import math

import pytest

from app.recommendations import policy
from app.shared.errors import (
    InvalidLeadTimeError,
    InvalidPolicyHorizonError,
    InvalidReplenishmentWindowError,
    InvalidServiceLevelError,
)


class TestZScore:
    def test_95_percentile_is_1_645(self):
        assert policy.z_score(0.95) == pytest.approx(1.6449, abs=1e-4)

    def test_99_percentile_is_2_326(self):
        assert policy.z_score(0.99) == pytest.approx(2.3263, abs=1e-4)

    def test_median_is_zero(self):
        assert policy.z_score(0.5) == pytest.approx(0.0, abs=1e-12)


class TestSafetyStock:
    def test_formula_z_sigma_root_of_window(self):
        # σ=10, T=10, SL=0.95 → 1.6449·10·√10 ≈ 52.0 (не 100 — ошибки гасят друг друга)
        assert policy.safety_stock(10.0, 10, 0.95) == pytest.approx(
            1.6448536 * 10 * math.sqrt(10)
        )

    def test_zero_sigma_gives_zero(self):
        assert policy.safety_stock(0.0, 10, 0.95) == 0.0

    def test_grows_with_service_level(self):
        assert (
            policy.safety_stock(5.0, 7, 0.99) > policy.safety_stock(5.0, 7, 0.95)
        )


class TestOrderQuantity:
    def test_exact_integer_need_is_not_overordered(self):
        # потребность ровно 20 → 20, а не 21
        assert policy.order_quantity(30.0, 10, sigma=0.0, window_days=10,
                                     service_level=0.95) == 20

    def test_fractional_need_rounds_up(self):
        assert policy.order_quantity(20.5, 0, sigma=0.0, window_days=10,
                                     service_level=0.95) == 21

    def test_tiny_positive_need_orders_one(self):
        # G5: потребность 0.2 → 1 (ceil честен: недозаказ рискует стокаутом)
        assert policy.order_quantity(0.2, 0, sigma=0.0, window_days=10,
                                     service_level=0.95) == 1

    def test_zero_need_means_sufficient(self):
        assert policy.order_quantity(10.0, 10, sigma=0.0, window_days=10,
                                     service_level=0.95) == 0

    def test_negative_need_is_zero_not_negative(self):
        assert policy.order_quantity(10.0, 100, sigma=0.0, window_days=10,
                                     service_level=0.95) == 0

    def test_float_noise_does_not_create_order(self):
        # 0.1 + 0.2 − 0.3 = 5.5e-17: без гвардии ceil дал бы 1
        assert policy.order_quantity(0.1 + 0.2, 0.3, sigma=0.0, window_days=10,
                                     service_level=0.95) == 0

    def test_safety_stock_participates(self):
        # σ>0 добавляет SS к потребности: 20 + 1.6449·10·√10 ≈ 72.0 → 72
        q = policy.order_quantity(20.0, 0, sigma=10.0, window_days=10,
                                  service_level=0.95)
        assert q == math.ceil(1.6448536 * 10 * math.sqrt(10) + 20)


class TestValidateParams:
    def test_defaults_are_valid(self):
        policy.validate_params(
            policy.DEFAULT_SERVICE_LEVEL,
            policy.DEFAULT_LEAD_TIME_DAYS,
            policy.DEFAULT_HORIZON_DAYS,
        )  # не бросает

    def test_max_window_boundary_is_valid(self):
        policy.validate_params(0.95, 7, 7)  # L+H = 14 — граница допустима

    @pytest.mark.parametrize("bad_level", [0.0, 1.0, -0.5, 1.5])
    def test_service_level_outside_open_interval_rejected(self, bad_level):
        with pytest.raises(InvalidServiceLevelError, match="Уровень сервиса"):
            policy.validate_params(bad_level, 3, 7)

    def test_zero_lead_time_rejected(self):
        with pytest.raises(InvalidLeadTimeError, match="Время поставки"):
            policy.validate_params(0.95, 0, 7)

    def test_zero_horizon_rejected(self):
        with pytest.raises(InvalidPolicyHorizonError, match="Горизонт обзора"):
            policy.validate_params(0.95, 3, 0)

    def test_window_over_model_horizon_rejected(self):
        with pytest.raises(InvalidReplenishmentWindowError, match="14"):
            policy.validate_params(0.95, 8, 7)  # 15 > 14
