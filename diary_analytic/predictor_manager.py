# diary_analytic/predictor_manager.py

"""
🧠 PredictorManager — диспетчер стратегий прогнозирования

Назначение:
    - централизованно управляет обучением и прогнозами;
    - абстрагирует вызов разных моделей: base_model, flags_model и др.;
    - изолирует ML-логику от views и других частей Django-приложения;
    - логирует ключевые шаги: выбор стратегии, исключения признаков, ошибки.

Используется во вьюхах:
    - для предсказаний:    manager.predict_today(strategy=..., ...)
    - для обучения модели: manager.train(strategy=..., ...)
"""

from diary_analytic.ml_utils import get_model
from .loggers import predict_logger


# -------------------------------------------------------------
# 📦 Общая точка входа для всех моделей прогнозирования
# -------------------------------------------------------------

class PredictorManager:
    """
    Класс, управляющий вызовом нужной модели в зависимости от стратегии.
    """

    def __init__(self):
        """
        Инициализация — ничего не требует.
        Стратегия передаётся в момент вызова train() или predict_today().
        """
        pass

    # -----------------------------------------------------------------
    # 🧪 Обучение модели по выбранной стратегии
    # -----------------------------------------------------------------

    def train(self, strategy: str, df, target: str, exclude: list):
        """
        Обучает модель прогнозирования по всей истории.

        :param strategy: название стратегии (например, 'base', 'flags')
        :param df: датафрейм всех записей пользователя (pivot-таблица)
        :param target: параметр, который нужно предсказывать
        :param exclude: список признаков, которые нужно исключить (например, текущий target)

        :return: обученная модель (или объект, пригодный для дальнейшего вызова predict)
        """
        predict_logger.debug(f"🔁 [train] Стратегия: {strategy}, Target: {target}, Исключения: {exclude}")

        if strategy == "base":
            return get_model("base").train_model(df, target, exclude=exclude)

        else:
            raise ValueError(f"❌ Неизвестная стратегия обучения: {strategy}")

    # -----------------------------------------------------------------
    # 🔮 Прогнозирование текущего дня по выбранной стратегии
    # -----------------------------------------------------------------

    def predict_today(self, strategy: str, model, today_row: dict) -> float:
        """
        Выполняет прогноз значения параметра на сегодня.

        :param strategy: название стратегии (например, 'base')
        :param model: обученная модель, возвращённая из train()
        :param today_row: словарь значений параметров за сегодня (может быть неполным)

        :return: float-прогноз (или np.nan/null при невозможности)
        """
        predict_logger.debug(f"📥 [predict_today] Стратегия: {strategy}, Данные: {today_row}")

        try:
            if strategy == "base":
                return get_model("base").predict(model["model"], model["features"], today_row)

            else:
                raise ValueError(f"❌ Неизвестная стратегия предсказания: {strategy}")

        except Exception as e:
            predict_logger.error(f"🔥 Ошибка в predict_today (стратегия: {strategy}) — {str(e)}")
            return None
