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
import os
import pandas as pd
from pprint import pformat


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

    def save_model_coefs(self, model, features, strategy, target):
        """
        Сохраняет коэффициенты и признаки модели в CSV-файл для последующего анализа.
        """
        predict_logger.info(f"[save_model_coefs] Попытка сохранить коэффициенты. Модель: {type(model)}, features: {features}")
        if model and hasattr(model, "coef_"):
            try:
                coef_df = pd.DataFrame({
                    "feature": features,
                    "coef": model.coef_
                })
                coef_df["intercept"] = model.intercept_
                export_dir = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "diary_analytic", "trained_models", strategy, "csv"
                )
                os.makedirs(export_dir, exist_ok=True)
                export_path = os.path.join(export_dir, f"{target}_{strategy}_coefs.csv")
                predict_logger.info(f"[save_model_coefs] Сохраняю CSV по пути: {export_path}")
                coef_df.to_csv(export_path, index=False)
                predict_logger.info(f"[save_model_coefs] CSV успешно сохранён: {export_path}")
            except Exception as e:
                predict_logger.error(f"[save_model_coefs] Ошибка при сохранении CSV: {e}")
        else:
            predict_logger.warning(f"[save_model_coefs] Модель не имеет coef_ или model=None. model: {type(model)}, features: {features}")

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
        print("1111111111111")
        predict_logger.info(f"[train] Запущен train для стратегии {strategy}, target={target}, exclude={exclude}")

        if strategy == "base":
            model = get_model("base").train_model(df, target, exclude=exclude)
            predict_logger.info(f"[train] Модель обучена. Ключи model: {list(model.keys()) if isinstance(model, dict) else type(model)}")
        else:
            predict_logger.error(f"[train] Неизвестная стратегия обучения: {strategy}")
            raise ValueError(f"❌ Неизвестная стратегия обучения: {strategy}")

        try:
            predict_logger.info("[train] Пробую сохранить коэффициенты модели в CSV")
            self.save_model_coefs(model["model"], model["features"], strategy, target)
        except Exception as e:
            predict_logger.error(f"[train] Ошибка при сохранении CSV: {e}")

        return model

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
        print("1111111111111")
        try:
            if strategy == "base":
                return get_model("base").predict(model["model"], model["features"], today_row)

            else:
                raise ValueError(f"❌ Неизвестная стратегия предсказания: {strategy}")

        except Exception as e:
            predict_logger.error(f"🔥 Ошибка в predict_today (стратегия: {strategy}) — {str(e)}")
            return None
