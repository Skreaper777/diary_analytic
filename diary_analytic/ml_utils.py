"""
🧠 ml_utils.py — базовые функции для ML-прогнозирования

Содержит:
    - base_model: простая линейная модель для базовых прогнозов
    - flags_model: модель с флагами (будет добавлена позже)
"""

import numpy as np
from sklearn.linear_model import LinearRegression
from .loggers import predict_logger


# --------------------------------------------------------------------
# 📊 base_model — простая линейная модель
# --------------------------------------------------------------------

class base_model:
    @staticmethod
    def train_model(df, target: str, exclude: list):
        """
        Обучает простую линейную модель для прогнозирования target.

        :param df: DataFrame с данными
        :param target: название целевого параметра
        :param exclude: список параметров для исключения
        :return: обученная модель
        """
        # Убираем исключённые параметры
        features = [col for col in df.columns if col not in exclude]
        
        # Заполняем пропуски нулями для обучения
        X = df[features].fillna(0).values
        y = df[target].fillna(0).values
        
        # Обучаем модель
        model = LinearRegression()
        model.fit(X, y)
        
        predict_logger.debug(f"✅ Обучена base_model для {target}")
        return model

    @staticmethod
    def predict(model, today_row: dict) -> float:
        """
        Делает прогноз на основе обученной модели.

        :param model: обученная модель
        :param today_row: словарь с текущими значениями параметров
        :return: прогноз (float)
        """
        # Преобразуем словарь в массив признаков
        X = np.array([list(today_row.values())]).reshape(1, -1)
        
        # Делаем прогноз
        prediction = model.predict(X)[0]
        
        # Ограничиваем прогноз диапазоном [0, 5]
        return max(0.0, min(5.0, prediction))


# --------------------------------------------------------------------
# 🚩 flags_model — модель с флагами (заглушка)
# --------------------------------------------------------------------

class flags_model:
    @staticmethod
    def train_model(df, target: str, exclude: list):
        """Заглушка для будущей реализации"""
        raise NotImplementedError("🚧 flags_model пока не реализована")

    @staticmethod
    def predict(model, today_row: dict) -> float:
        """Заглушка для будущей реализации"""
        raise NotImplementedError("🚧 flags_model пока не реализована")


# Явно экспортируем классы
__all__ = ['base_model', 'flags_model'] 