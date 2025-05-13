# diary_analytic/views.py

from datetime import datetime
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, JsonResponse 
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from .models import Entry, Parameter, EntryValue
from .forms import EntryForm
from .utils import get_diary_dataframe, get_today_row
from .predictor_manager import PredictorManager
from .loggers import web_logger, db_logger, predict_logger
import json
import os
import traceback
from django.conf import settings
from diary_analytic.ml_utils import base_model, flags_model


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
    web_logger.debug(f"[add_entry] 🔍 SQL запрос: {entry_values.query}")
    
    values_map = {
        v.parameter.key: v.value
        for v in entry_values
    }
    web_logger.debug(f"[add_entry] 📊 Загружено параметров для Entry: {len(values_map)}")
    for key, value in values_map.items():
        web_logger.debug(f"[add_entry] 📌 Параметр {key}: значение {value} (тип: {type(value)})")
    
    # Проверяем все активные параметры
    for param in parameters:
        if param.key not in values_map:
            web_logger.debug(f"[add_entry] ⚠️ Параметр {param.key} не имеет значения в базе")

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
        db_logger.info(f"[update_value] RAW BODY: {request.body}")
        data = json.loads(request.body)
        param_key = data.get("parameter")    # ключ параметра, например: "ustalost"
        value = data.get("value")            # значение от 0 до 5
        date_str = data.get("date")          # дата в строке, например: "2025-05-12"
        db_logger.info(f"[update_value] PARSED: param_key={param_key!r}, value={value!r}, date_str={date_str!r}")

        if not param_key or not date_str:
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
        if value is None:
            db_logger.info(f"[update_value] 🟡 value=None: запрос на удаление значения. param_key={param_key}, date={date_str}")
            # Удаление значения
            try:
                deleted_count, deleted_details = EntryValue.objects.filter(entry=entry, parameter=parameter).delete()
                db_logger.info(f"[update_value] 🗑️ Удалён EntryValue: {param_key} ({entry_date}), удалено записей: {deleted_count}")
                return JsonResponse({"success": True, "deleted": True, "deleted_count": deleted_count})
            except Exception as del_exc:
                db_logger.exception(f"[update_value] ❌ Ошибка при удалении EntryValue: {param_key} ({entry_date}): {del_exc}")
                return JsonResponse({"error": "delete error"}, status=500)
        else:
            db_logger.info(f"[update_value] 🟢 value={value}: обновление/создание значения. param_key={param_key}, date={date_str}")
            ev, created = EntryValue.objects.update_or_create(
                entry=entry,
                parameter=parameter,
                defaults={"value": float(value)}
            )
            action = "Создан" if created else "Обновлён"
            db_logger.info(f"[update_value] ✅ {action} EntryValue: {param_key} = {value} ({entry_date})")
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


# 📡 Обрабатывает GET-запрос на получение прогнозов по всем стратегиям
@require_GET
def get_predictions(request: HttpRequest) -> JsonResponse:
    from .utils import get_today_row
    import joblib
    import traceback

    web_logger.debug("[get_predictions] 🔧 Получен запрос на прогнозы: %s", request.GET)

    date_str = request.GET.get("date")
    if not date_str:
        web_logger.warning("[get_predictions] ⛔ Отсутствует параметр 'date' в запросе")
        return JsonResponse({"error": "missing date"}, status=400)

    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        web_logger.debug("[get_predictions] 📆 Преобразована дата: %s", selected_date)
    except ValueError:
        web_logger.warning("[get_predictions] ❌ Некорректный формат даты: %s", date_str)
        return JsonResponse({"error": "invalid date"}, status=400)

    # Получаем строку данных для указанной даты
    row = get_today_row(selected_date)
    web_logger.debug(f"[get_predictions] 🧩 Строка признаков на дату {selected_date}: {row}")
    if row is None or not row:
        web_logger.warning("[get_predictions] 🚫 Данные на дату %s отсутствуют или пусты", selected_date)
        return JsonResponse({"error": "no data"}, status=404)

    base_dir = os.path.join(settings.BASE_DIR, "diary_analytic", "trained_models")
    strategies = ["base", "flags"]  # Здесь можно добавить другие стратегии при необходимости
    predictions = {}

    web_logger.debug("[get_predictions] 🔍 Стратегии для прогноза: %s", strategies)

    for strategy in strategies:
        model_dir = os.path.join(base_dir, strategy)
        web_logger.debug("[get_predictions] 📂 Проверка папки моделей: %s", model_dir)

        if not os.path.exists(model_dir):
            web_logger.warning("[get_predictions] ⚠️ Папка не найдена: %s", model_dir)
            continue

        for fname in os.listdir(model_dir):
            if not fname.endswith(".pkl"):
                continue

            param_key = fname.replace(".pkl", "")
            full_key = f"{param_key}_{strategy}"
            model_path = os.path.join(model_dir, fname)

            try:
                model = joblib.load(model_path)
                web_logger.debug(f"[get_predictions] 📦 Загружена модель: {model_path}")
                # Логируем shape входа и имена признаков
                if hasattr(model, 'n_features_in_'):
                    web_logger.debug(f"[get_predictions] Модель {full_key} ожидает признаков: {model.n_features_in_}")
                if hasattr(model, 'feature_names_in_'):
                    web_logger.debug(f"[get_predictions] Модель {full_key} ожидает признаки: {model.feature_names_in_}")
                # Преобразуем row в список признаков в том же порядке, что и при обучении
                if hasattr(model, 'feature_names_in_'):
                    X = [row.get(f, 0.0) for f in model.feature_names_in_]
                    web_logger.debug(f"[get_predictions] Вход для модели {full_key}: {X}")
                    value = float(model.predict([X])[0])
                else:
                    # Fallback: просто все значения row
                    X = list(row.values())
                    web_logger.debug(f"[get_predictions] Вход для модели {full_key} (fallback): {X}")
                    value = float(model.predict([X])[0])
                predictions[full_key] = round(value, 2)
                web_logger.debug("[get_predictions] ✅ Прогноз: %s = %.2f", full_key, value)
            except Exception as e:
                tb = traceback.format_exc()
                web_logger.error(f"[get_predictions] ⚠️ Ошибка при прогнозе {full_key}: {e}\n{tb}")
                predictions[full_key] = None

    web_logger.debug("[get_predictions] 📤 Отправка JSON с %d прогнозами", len(predictions))
    return JsonResponse(predictions)

# 📦 Обучает модели по всем стратегиям и сохраняет их в отдельные папки
@csrf_exempt
@require_POST
def retrain_models_all(request: HttpRequest) -> JsonResponse:
    from .utils import get_diary_dataframe
    import joblib

    web_logger.debug("[retrain] 🔁 Запущено переобучение моделей по всем стратегиям...")

    df = get_diary_dataframe()
    today = datetime.now().date()
    # Исправленная фильтрация по дате
    if "date" in df.columns:
        df = df[df["date"] < today]
    else:
        df = df.reset_index()
        if "date" in df.columns:
            df = df[df["date"] < today]
        # если и после этого нет — не фильтруем

    strategies = [
        ("base", base_model.train_model),
        ("flags", flags_model.train_model),
    ]

    results = []

    for strategy_name, strategy_fn in strategies:
        web_logger.debug("[retrain] ▶️ Стратегия: %s", strategy_name)

        model_dir = os.path.join(settings.BASE_DIR, "diary_analytic", "trained_models", strategy_name)
        os.makedirs(model_dir, exist_ok=True)
        web_logger.debug("[retrain] 📁 Каталог моделей: %s", model_dir)

        for target in df.columns:
            if target in ("date", "Дата", "comment"):
                continue

            try:
                result = strategy_fn(df.copy(), target=target, exclude=[])
                model = result.get("model")
                features = result.get("features")

                if model:
                    file_path = os.path.join(model_dir, f"{target}.pkl")
                    joblib.dump({"model": model, "features": features}, file_path)
                    msg = f"[{strategy_name}] ✅ Обучено и сохранено: {target}"
                    web_logger.info("[retrain] " + msg)
                    results.append(msg)
                else:
                    msg = f"[{strategy_name}] ⚠️ Пропущено: {target}"
                    web_logger.warning("[retrain] " + msg)
                    results.append(msg)
            except Exception as e:
                msg = f"[{strategy_name}] ❌ Ошибка при обучении {target}: {e}"
                web_logger.exception("[retrain] " + msg)
                results.append(msg)

    # Новый блок: если есть ошибки, возвращаем status: error
    if any("❌" in msg for msg in results):
        return JsonResponse({"status": "error", "details": results})
    return JsonResponse({"status": "ok", "details": results})