# diary_analytic/views.py

from datetime import datetime
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, JsonResponse 
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Entry, Parameter, EntryValue
from .forms import EntryForm
from .utils import get_diary_dataframe
from .loggers import web_logger, db_logger, predict_logger


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


# --------------------------------------------------------------------
# 🔘 AJAX: обновление значения параметра (клик по кнопке)
# --------------------------------------------------------------------

@csrf_exempt  # отключаем CSRF (используем ручную защиту через заголовок в JS)
@require_POST  # разрешаем только POST-запросы
def update_value(request):
    """
    Обрабатывает запрос на обновление одного значения параметра.

    📥 Вход: JSON-объект, отправленный через JS:
        {
            "parameter": "toshn",
            "value": 2,
            "date": "2025-05-12"
        }

    🧠 Обработка:
    - находит или создаёт Entry на указанную дату
    - находит Parameter по ключу
    - обновляет или создаёт EntryValue
    - логирует результат

    📤 Ответ:
    - {"success": true} — при успехе
    - {"error": "..."} — при ошибке
    """

    try:
        # --------------------------
        # 🔓 1. Распаковываем JSON
        # --------------------------
        data = json.loads(request.body)

        param_key = data.get("parameter")    # ключ параметра, например: "ustalost"
        value = data.get("value")            # значение от 0 до 5
        date_str = data.get("date")          # дата в строке, например: "2025-05-12"

        if not param_key or value is None or not date_str:
            db_logger.warning("⚠️ Не хватает обязательных полей в теле запроса")
            return JsonResponse({"error": "missing fields"}, status=400)

        # --------------------------
        # 🕓 2. Преобразуем дату
        # --------------------------
        try:
            entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            db_logger.warning(f"⚠️ Некорректный формат даты: {date_str}")
            return JsonResponse({"error": "invalid date"}, status=400)

        # --------------------------
        # 📅 3. Получаем или создаём Entry на эту дату
        # --------------------------
        entry, _ = Entry.objects.get_or_create(date=entry_date)

        # --------------------------
        # 📌 4. Находим параметр по ключу
        # --------------------------
        try:
            parameter = Parameter.objects.get(key=param_key)
        except Parameter.DoesNotExist:
            db_logger.error(f"❌ Параметр не найден: '{param_key}'")
            return JsonResponse({"error": "invalid parameter"}, status=400)

        # --------------------------
        # 💾 5. Обновляем или создаём EntryValue
        # --------------------------
        ev, created = EntryValue.objects.update_or_create(
            entry=entry,
            parameter=parameter,
            defaults={"value": float(value)}
        )

        # --------------------------
        # 📜 6. Логируем результат
        # --------------------------
        action = "Создан" if created else "Обновлён"
        db_logger.info(f"✅ {action} EntryValue: {param_key} = {value} ({entry_date})")

        # --------------------------
        # 📤 7. Возвращаем успех
        # --------------------------
        return JsonResponse({"success": True})

    except Exception as e:
        # 🔥 В случае любой ошибки — лог + JSON-ответ 500
        db_logger.exception(f"🔥 Ошибка в update_value: {str(e)}")
        return JsonResponse({"error": "internal error"}, status=500)
    
@require_GET
def predict(request):
    """
    Выполняет прогнозы по всем активным параметрам на указанную дату.

    🔍 GET-параметры:
        ?date=2025-05-12

    📦 Ответ:
        {
            "ustalost_base": 3.4,
            "toshn_base": 1.2,
            ...
        }

    Прогноз строится через стратегию "base" (линейная модель).
    """

    try:
        date_str = request.GET.get("date")
        if not date_str:
            return JsonResponse({"error": "missing date"}, status=400)

        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({"error": "invalid date"}, status=400)

        # Получаем полный DataFrame
        df = get_diary_dataframe()

        if df.empty:
            return JsonResponse({}, status=200)  # нет данных → нет прогнозов

        # Получаем значения за выбранную дату (частично заполненные)
        today_row = get_today_row(selected_date)
        manager = PredictorManager()
        result = {}

        # Перебираем все активные параметры
        for param in Parameter.objects.filter(is_active=True):
            key = param.key

            if key not in df.columns:
                continue  # нет истории для этого параметра

            # Исключаем сам параметр из признаков
            exclude = [key]
            try:
                model = manager.train(strategy="base", df=df, target=key, exclude=exclude)
                prediction = manager.predict_today(strategy="base", model=model, today_row=today_row)

                if prediction is not None:
                    result[f"{key}_base"] = round(prediction, 2)

                    predict_logger.debug(
                        f"[predict] ✅ Прогноз для {key}: {prediction:.2f}"
                    )

            except Exception as e:
                predict_logger.exception(f"[predict] ❌ Ошибка для {key}: {str(e)}")

        return JsonResponse(result)

    except Exception as e:
        predict_logger.exception(f"🔥 Ошибка в общей логике /predict/: {str(e)}")
        return JsonResponse({"error": "internal error"}, status=500)
