# diary_analytic/loggers.py

import logging
import os

# -------------------------------------------------------------------
# 📁 Каталог для логов
# -------------------------------------------------------------------

# Получаем абсолютный путь до директории /logs, находящейся в корне проекта
# (на один уровень выше текущего файла, т.е. выше diary_analytic/)
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

# Если каталог logs ещё не создан — создаём его (иначе FileNotFoundError)
os.makedirs(LOG_DIR, exist_ok=True)

# -------------------------------------------------------------------
# 🧰 Универсальная функция для создания логгера
# -------------------------------------------------------------------

def setup_logger(name: str, logfile: str) -> logging.Logger:
    """
    Унифицированный способ создания логгера для разных подсистем проекта.

    :param name: внутреннее имя логгера (например, 'web', 'predict')
    :param logfile: имя файла, в который будут писаться логи
    :return: объект Logger, настроенный на вывод в отдельный лог-файл

    📌 Преимущества:
    - Логгеры создаются централизованно
    - Каждый файл логирует свою подсистему
    - Формат логов читаемый и стабилен
    """

    # Абсолютный путь до файла логов (например: /logs/web.log)
    path = os.path.join(LOG_DIR, logfile)

    # Очищаем лог при каждом запуске, чтобы не копить старое (mode="w" на старте)
    open(path, 'w').close()

    # Создаём экземпляр логгера
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Отслеживаем всё, включая отладку

    # Создаём обработчик логов, записывающий в файл
    handler = logging.FileHandler(path, mode="a", encoding="utf-8")

    # Настраиваем читаемый формат строки лога
    formatter = logging.Formatter("[%(asctime)s] [%(name)s] [%(funcName)s] — %(message)s")
    handler.setFormatter(formatter)

    # Привязываем обработчик к логгеру
    logger.addHandler(handler)

    # Отключаем буферизацию на уровне логгера
    logger.propagate = False

    # Принудительно сбрасываем буфер после каждой записи
    handler.flush = lambda: handler.stream.flush()

    # Возвращаем готовый логгер
    return logger

# -------------------------------------------------------------------
# 🔧 Готовые логгеры под конкретные подсистемы
# -------------------------------------------------------------------

# 📘 WEB: маршруты, переходы, загрузка страниц, GET/POST параметры
web_logger = setup_logger("web", "web.log")

# 📊 ML: вызов моделей, стратегия прогнозов, объяснения, ошибки моделей
predict_logger = setup_logger("predict", "predict.log")

# 🗃️ БД: сохранение и удаление Entry, EntryValue, Parameter
db_logger = setup_logger("db", "db.log")
