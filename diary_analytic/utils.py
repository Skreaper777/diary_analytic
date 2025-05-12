# diary_analytic/utils.py

"""
📊 utils.py — утилиты для работы с данными

Основная функция:
    - get_diary_dataframe() — превращает данные из моделей Entry, Parameter, EntryValue
      в широкую таблицу для обучения и прогнозирования моделей.
"""

import pandas as pd
from .models import EntryValue


# --------------------------------------------------------------------
# 📈 Получение данных в формате DataFrame для ML
# --------------------------------------------------------------------

def get_diary_dataframe() -> pd.DataFrame:
    """
    Собирает все записи пользователя в виде «широкой» таблицы:
        - строки: даты (Entry.date)
        - столбцы: параметры (Parameter.key)
        - значения: значения параметров (EntryValue.value)

    Используется:
        - для обучения моделей (`train`)
        - для формирования today_row (`predict_today`)
        - для анализа истории

    📦 Пример выходного DataFrame:

        |     date     | toshn | ustalost | trevozhnost |
        |--------------|-------|----------|-------------|
        | 2025-05-10   | 1.0   | 2.0      | 4.0         |
        | 2025-05-11   | 0.0   | NaN      | 3.0         |
        | 2025-05-12   | NaN   | 1.0      | NaN         |

    :return: pd.DataFrame, индексированный по дате
    """

    # Извлекаем все значения параметров, связанных с Entry и Parameter
    values = EntryValue.objects.select_related("entry", "parameter")

    # Создаём список словарей (удобно для передачи в DataFrame)
    rows = []
    for val in values:
        rows.append({
            "date": val.entry.date,             # Дата (строка = день)
            "parameter": val.parameter.key,     # Название параметра (ключ)
            "value": val.value                  # Значение от 0.0 до 5.0
        })

    # Преобразуем в "узкий" DataFrame
    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame()  # если данных нет — вернуть пустую таблицу

    # Преобразуем из узкого формата в "широкий":
    # было: date | parameter | value
    # станет: date | toshn | ustalost | ...
    df = df.pivot(index="date", columns="parameter", values="value")

    # Убедимся, что даты отсортированы (на всякий случай)
    df.sort_index(inplace=True)

    # Можно заполнить пропуски, если нужно (по ТЗ: только при обучении)
    # df.fillna(0.0, inplace=True)

    return df
