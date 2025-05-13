document.addEventListener("DOMContentLoaded", async function () {
  console.log("🔄 Инициализация страницы...");
  console.log("📦 Значения из бэкенда:", window.VALUES_MAP);
  
  // Получаем дату из input
  const dateInput = document.getElementById("date-input");
  const dateValue = dateInput ? dateInput.value : "";
  console.log("📅 Выбранная дата:", dateValue);

  // Все блоки параметров
  const parameterBlocks = document.querySelectorAll(".parameter-block");

  parameterBlocks.forEach((block) => {
    const paramKey = block.getAttribute("data-key");
    const buttons = block.querySelectorAll(".value-button");
    
    // Логируем все кнопки и их значения
    console.log(`\n📊 Параметр ${paramKey}:`);
    console.log(`  🔍 Значение из бэкенда:`, window.VALUES_MAP[paramKey]);
    
    buttons.forEach((btn) => {
      const value = btn.getAttribute("data-value");
      const isSelected = btn.classList.contains("selected");
      console.log(`  - Кнопка ${value}: ${isSelected ? '✅ выбрана' : '❌ не выбрана'}`);
    });

    // Инициализация выбранных кнопок
    buttons.forEach((btn) => {
      btn.addEventListener("click", async function () {
        const selectedValue = parseInt(this.getAttribute("data-value"));
        const isAlreadySelected = this.classList.contains("selected");
        // paramKey всегда берём из блока, а не из кнопки!
        const paramKey = block.getAttribute("data-key");

        if (isAlreadySelected) {
          // Повторный клик — удаляем значение
          const payload = {
            parameter: paramKey,
            value: null,
            date: dateValue,
          };
          console.log("🟡 Отправка запроса на удаление:", payload);
          try {
            const response = await fetch("/update_value/", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
              },
              body: JSON.stringify(payload),
            });
            if (response.ok) {
              console.log(`🗑️ Удалено: ${paramKey}`);
              this.classList.remove("selected");
              loadPredictions();
            } else {
              console.error(`❌ Ошибка удаления ${paramKey}`);
            }
          } catch (error) {
            console.error("Ошибка соединения:", error);
          }
          return;
        }

        // 1. Подсветка активной кнопки
        buttons.forEach((b) => b.classList.remove("selected"));
        this.classList.add("selected");

        // 2. Отправка на сервер
        const payload = {
          parameter: paramKey,
          value: selectedValue,
          date: dateValue,
        };
        console.log("🟢 Отправка запроса на обновление:", payload);
        try {
          const response = await fetch("/update_value/", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCookie("csrftoken"),
            },
            body: JSON.stringify(payload),
          });

          if (response.ok) {
            console.log(`✅ Обновлено: ${paramKey} = ${selectedValue}`);
            loadPredictions();
          } else {
            console.error(`❌ Ошибка обновления ${paramKey}`);
          }
        } catch (error) {
          console.error("Ошибка соединения:", error);
        }
      });
    });
  });

  // Инициализируем выбранные значения
  parameterBlocks.forEach(block => {
      const key = block.dataset.key;
      const selectedButton = block.querySelector('.value-button.selected');
      console.log(`📊 Параметр ${key}:`, selectedButton ? `выбрано значение ${selectedButton.dataset.value}` : 'нет выбранного значения');
  });

  // Загружаем прогнозы (старый способ)
  loadPredictions();

  // Новый способ: Автоматическая загрузка прогнозов при открытии страницы
  console.log("[predict] 📦 Старт загрузки прогнозов после DOMContentLoaded");
  // Получаем значение даты из поля ввода или берём сегодняшнюю
  const date = document.getElementById("date-input")?.value || new Date().toISOString().slice(0, 10);
  console.log("[predict] 📅 Выбранная дата:", date);

  try {
      // Отправляем запрос на сервер за прогнозами
      const res = await fetch(`/get_predictions/?date=${date}`);
      console.log("[predict] 📡 Запрос отправлен на /get_predictions/");
      const preds = await res.json();
      console.log("[predict] 📥 Получен ответ:", preds);

      // Обходим все прогнозы, например: toshn_base, mood_flags
      for (const [key, value] of Object.entries(preds)) {
          const [param, strategy] = key.split("_");
          console.log(`[predict] 🔍 Обрабатываем прогноз: ${param}, стратегия: ${strategy}, значение: ${value}`);

          const selector = `[data-param='${param}']`;
          const el = document.querySelector(selector);

          if (el) {
              // Ищем или создаём блок .prediction
              let block = el.querySelector(".prediction");
              if (!block) {
                  block = document.createElement("div");
                  block.className = "prediction";
                  el.appendChild(block);
                  console.log(`[predict] ➕ Создан блок .prediction для параметра ${param}`);
              }

              // Добавляем строку с прогнозом
              block.innerHTML += `<div><small>🔮 ${strategy}: <b>${value ?? "—"}</b></small></div>`;
              console.log(`[predict] ✅ Прогноз добавлен: ${strategy}: ${value}`);
          } else {
              console.warn(`[predict] ⚠️ Элемент с data-param='${param}' не найден`);
          }
      }
  } catch (err) {
      console.error("[predict] ❌ Ошибка при получении или обработке прогнозов:", err);
  }

  const btn = document.getElementById('retrain-models-btn');
  if (btn) {
    btn.addEventListener('click', async function() {
      btn.disabled = true;
      btn.textContent = '⏳ Обновление...';
      try {
        const res = await fetch('/retrain_models_all/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json',
          },
        });
        if (res.ok) {
          alert('Модели успешно переобучены!');
        } else {
          alert('Ошибка при обучении моделей');
        }
      } catch (e) {
        alert('Ошибка соединения');
      }
      btn.disabled = false;
      btn.textContent = '🔁 Обновить прогнозы';
    });
  }
});

// 🔐 Получение CSRF-токена из cookie
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
// 📡 Функция загрузки прогнозов с сервера
async function loadPredictions() {
  // 🕓 1. Получаем дату, выбранную в поле <input type="date">
  const date = document.getElementById("date-input")?.value;
  if (!date) return; // если даты нет — прекращаем

  try {
    // 🌐 2. Отправляем GET-запрос на /predict/?date=...
    const res = await fetch(`/predict/?date=${encodeURIComponent(date)}`);

    // 🧾 3. Разбираем JSON-ответ с прогнозами
    const data = await res.json();

    // Пример: data = { "ustalost_base": 3.4, "toshn_base": 1.2 }

    // 🔁 4. Перебираем каждый параметр и его предсказанное значение
    Object.entries(data).forEach(([key, value]) => {
      // Убираем суффикс "_base" → получаем чистый параметр (например: "ustalost")
      const paramKey = key.replace("_base", "");

      // 🎯 Ищем блоки для вставки значений
      const target = document.getElementById(`predicted-${paramKey}`);          // основной прогноз
      const deltaTarget = document.getElementById(`predicted-delta-${paramKey}`); // дельта

      if (target) {
        // 📌 5. Проверяем — есть ли уже сохранённое значение у пользователя
        const selectedButton = document
          .querySelector(`.parameter-block[data-key="${paramKey}"] .value-button.selected`);

        // Преобразуем значение в число (или NaN, если ничего не выбрано)
        const current = parseFloat(selectedButton?.getAttribute("data-value") || "NaN");

        // 🔁 6. Считаем дельту, если возможно
        const delta = isNaN(current) ? null : value - current;
        const absDelta = delta !== null ? Math.abs(delta) : null;

        // 📥 7. Вставляем текст прогноза и дельты
        target.textContent = `Прогноз: ${value.toFixed(1)}`;
        deltaTarget.textContent = delta !== null ? `Δ ${delta.toFixed(1)}` : "";

        // 🎨 8. Вычисляем цвет подсказки
        let color = "gray";
        if (absDelta !== null) {
          if (absDelta < 1) color = "green";
          else if (absDelta <= 2) color = "yellow";
          else color = "red";
        }

        // 🟢 9. Вставляем цвет как data-атрибут (для CSS-стилизации)
        target.dataset.color = color;
      }
    });

    // ✅ Лог в консоль: успех
    console.log("✅ Прогнозы успешно загружены:", data);

  } catch (err) {
    // ❌ Если ошибка — логируем в консоль
    console.error("❌ Ошибка загрузки прогнозов", err);
  }
}
