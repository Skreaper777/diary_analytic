# diary_analytic/views.py

from datetime import datetime
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from .models import Entry, Parameter, EntryValue
from .forms import EntryForm
from .utils import get_diary_dataframe
from .loggers import web_logger


# --------------------------------------------------------------------
# 📅 Главная вьюшка: дневник состояния на дату
# --------------------------------------------------------------------

def add_entry(request: HttpRequest) -> HttpResponse:
    """
    Обрабатывает отображение дневника по дате.

    Поведение:
    - ⏱️ Получает дату из параметра `?date=...`, либо берёт сегодняшнюю.
    - 🔄 Создаёт или загружает объект Entry за этот день.
    - 📌 Загружает список активных параметров из модели Parameter.
    - 📈 Загружает значения параметров (EntryValue), если они уже были сохранены.
    - 📝 Загружает форму комментария и связывает с Entry.
    - 💬 Обрабатывает POST-запрос: обновляет комментарий.
    - 🖼️ Передаёт всё в шаблон `add_entry.html`.

    Возвращает отрисованную HTML-страницу.
    """

    # ----------------------------------------------------------------
    # 🕓 1. Получаем дату из GET-параметра
    # ----------------------------------------------------------------
    today_str = datetime.now().date().isoformat()  # Строка сегодняшней даты (например, "2025-05-12")
    selected_str = request.GET.get("date", today_str)  # Если нет ?date=, то подставляем сегодня

    try:
        selected_date = datetime.strptime(selected_str, "%Y-%m-%d").date()
        web_logger.debug(f"[add_entry] ✅ Получена дата из запроса: {selected_date}")
    except ValueError:
        selected_date = datetime.now().date()
        web_logger.warning(f"[add_entry] ⚠️ Некорректная дата '{selected_str}' — используем текущую: {selected_date}")

    # ----------------------------------------------------------------
    # 🧾 2. Загружаем или создаём Entry на эту дату
    # ----------------------------------------------------------------
    entry, created = Entry.objects.get_or_create(date=selected_date)

    if created:
        web_logger.debug(f"[add_entry] 🆕 Создана новая запись Entry на дату: {selected_date}")
    else:
        web_logger.debug(f"[add_entry] 📄 Найдена запись Entry на дату: {selected_date}")

    # ----------------------------------------------------------------
    # 📝 3. Инициализируем форму комментария
    # ----------------------------------------------------------------
    form = EntryForm(instance=entry)
    web_logger.debug(f"[add_entry] 🧾 Инициализирована форма комментария для Entry ({selected_date})")

    # ----------------------------------------------------------------
    # 📌 4. Получаем все активные параметры из базы
    # ----------------------------------------------------------------
    parameters = Parameter.objects.filter(is_active=True).order_by("name")
    web_logger.debug(f"[add_entry] 📌 Загружено активных параметров: {parameters.count()}")

    # ----------------------------------------------------------------
    # 📈 5. Загружаем текущие значения параметров за день (если есть)
    # ----------------------------------------------------------------
    entry_values = EntryValue.objects.filter(entry=entry).select_related("parameter")
    values_map = {
        v.parameter.key: v.value
        for v in entry_values
    }
    web_logger.debug(f"[add_entry] 📊 Загружено параметров для Entry: {len(values_map)} — {values_map}")

    # ----------------------------------------------------------------
    # 💬 6. Обработка POST-запроса (обновление комментария)
    # ----------------------------------------------------------------
    if request.method == "POST":
        web_logger.debug(f"[add_entry] 📥 Обработка POST-запроса")

        form = EntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            web_logger.info(f"[add_entry] 💾 Комментарий обновлён для {selected_date}: «{entry.comment[:50]}...»")
        else:
            web_logger.warning(f"[add_entry] ❌ Форма комментария не прошла валидацию: {form.errors}")

        # В будущем здесь будет блок обработки train=1 (обучения модели)

    # ----------------------------------------------------------------
    # 🖼️ 7. Рендерим HTML-страницу через шаблон
    # ----------------------------------------------------------------
    web_logger.debug(f"[add_entry] 📤 Передаём данные в шаблон add_entry.html")

    return render(request, "diary_analytic/add_entry.html", {
        "form": form,                         # Форма комментария
        "parameters": parameters,             # Активные параметры
        "values_map": values_map,             # Словарь: { "toshn": 2.0, "ustalost": 1.0 }
        "selected_date": selected_date,       # Дата, для которой загружается дневник
        "today_str": today_str,               # Строка сегодняшней даты (для сравнения в шаблоне)
    })
