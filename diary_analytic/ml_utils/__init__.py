from . import base_model  # Добавляй сюда другие модели по мере необходимости

def get_model(name: str):
    if name == "base":
        return base_model
    raise ValueError(f"Неизвестная модель: {name}")
