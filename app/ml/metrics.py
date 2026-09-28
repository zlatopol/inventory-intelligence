"""Метрики прогноза спроса (Phase 2, ML track).

Почему MAE и WAPE, а не «привычные» MAPE/RMSE:
- MAPE делит ошибку каждого наблюдения на ФАКТ — при нулевом/малом спросе
  взрывается (а нулевые дни у нас контрактно возможны, Q2). Для intermittent
  demand непригоден;
- RMSE штрафует большие ошибки квадратично — фокусируется на хвостах.
  Для закупок важна средняя ошибка В ШТУКАХ («в среднем ошибаемся на 3 шт.»),
  а не чувствительность к редким выбросам;
- MAE — та же средняя ошибка в штуках, без искажения масштабом;
- WAPE (weighted APE) — суммарная ошибка, взвешенная суммарным фактом:
  устойчив к нулям отдельных дней (деление одно, на общую сумму) и читается
  как «прогноз ошибается на N% от объёма продаж».
"""
import numpy as np
import pandas as pd


def mae(actual: pd.Series, predicted: pd.Series) -> float:
    """Средняя абсолютная ошибка — в штуках товара."""
    return float(np.abs(actual - predicted).mean())


def wape(actual: pd.Series, predicted: pd.Series) -> float:
    """Ошибка в % от суммарного факта; inf, если факта нет совсем."""
    denominator = actual.sum()
    if denominator == 0:
        return float("inf")
    return float(np.abs(actual - predicted).sum() / denominator * 100)
