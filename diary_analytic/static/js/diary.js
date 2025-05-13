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

  // Инициализация графиков истории
  initAllParameterCharts(dateValue);
  setupChartsToggleBtn();
  // Восстанавливаем видимость графиков
  setChartsVisible(loadChartsVisibleState());

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
        const data = await res.json();
        if (data.status === 'ok') {
          alert('Модели успешно переобучены!');
        } else if (data.status === 'error') {
          // Можно сделать красивое модальное окно, но пока alert
          alert('Есть ошибки при обучении моделей:\n' + (data.details || []).join('\n'));
        } else {
          alert('Неизвестный ответ от сервера');
        }
      } catch (e) {
        alert('Ошибка соединения');
      }
      btn.disabled = false;
      btn.textContent = '🔁 Обновить прогнозы';
    });
  }

  // При смене даты (если переход по календарю)
  if (dateInput) {
    dateInput.addEventListener('change', function() {
      setTimeout(() => {
        // После перехода по ссылке страница перезагрузится, но если SPA — можно раскомментировать:
        // initAllParameterCharts(this.value);
      }, 100);
    });
  }

  setupPredictionsToggleBtn();
  setPredictionsVisible(loadPredictionsVisibleState());
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
  console.log("[loadPredictions] Выбранная дата:", date);
  if (!date) {
    console.warn("[loadPredictions] Нет даты, прогнозы не будут загружены");
    return; // если даты нет — прекращаем
  }

  try {
    // 🌐 2. Отправляем GET-запрос на /get_predictions/?date=...
    console.log(`[loadPredictions] Отправляю запрос: /get_predictions/?date=${encodeURIComponent(date)}`);
    const res = await fetch(`/get_predictions/?date=${encodeURIComponent(date)}`);

    // 🧾 3. Разбираем JSON-ответ с прогнозами
    const data = await res.json();
    console.log("[loadPredictions] Ответ от сервера:", data);

    // Пример: data = { "ustalost_base": 3.4, "toshn_base": 1.2 }

    // 🔁 4. Перебираем каждый параметр и его предсказанное значение
    Object.entries(data).forEach(([key, value]) => {
      console.log(`[loadPredictions] Обрабатываю ключ: ${key}, значение: ${value}`);
      // Убираем суффикс "_base" → получаем чистый параметр (например: "ustalost")
      const paramKey = key.replace("_base", "");
      console.log(`[loadPredictions] paramKey: ${paramKey}`);

      // 🎯 Ищем блоки для вставки значений
      const target = document.getElementById(`predicted-${paramKey}`);          // основной прогноз
      const deltaTarget = document.getElementById(`predicted-delta-${paramKey}`); // дельта

      if (!target) {
        console.warn(`[loadPredictions] Не найден элемент predicted-${paramKey}`);
      }
      if (!deltaTarget) {
        console.warn(`[loadPredictions] Не найден элемент predicted-delta-${paramKey}`);
      }

      if (target) {
        // 📌 5. Проверяем — есть ли уже сохранённое значение у пользователя
        const selectedButton = document
          .querySelector(`.parameter-block[data-key="${paramKey}"] .value-button.selected`);
        if (!selectedButton) {
          console.log(`[loadPredictions] Для ${paramKey} не выбрано значение пользователем`);
        }

        // Преобразуем значение в число (или NaN, если ничего не выбрано)
        const current = parseFloat(selectedButton?.getAttribute("data-value") || "NaN");
        console.log(`[loadPredictions] Текущее значение пользователя для ${paramKey}:`, current);

        // 🔁 6. Считаем дельту, если возможно
        const delta = isNaN(current) ? null : value - current;
        const absDelta = delta !== null ? Math.abs(delta) : null;
        console.log(`[loadPredictions] Прогноз: ${value}, Дельта: ${delta}, Абс. дельта: ${absDelta}`);

        // 📥 7. Вставляем текст прогноза и дельты
        target.textContent = `Прогноз: ${value.toFixed(1)}`;
        if (deltaTarget) {
          deltaTarget.textContent = delta !== null ? `Δ ${delta.toFixed(1)}` : "";
        }

        // 🎨 8. Вычисляем цвет подсказки
        let color = "gray";
        if (absDelta !== null) {
          if (absDelta < 1) color = "green";
          else if (absDelta <= 2) color = "yellow";
          else color = "red";
        }
        console.log(`[loadPredictions] Цвет для ${paramKey}:`, color);

        // 🟢 9. Вставляем цвет как data-атрибут (для CSS-стилизации)
        target.dataset.color = color;
      }
    });

    // ✅ Лог в консоль: успех
    console.log("[loadPredictions] Прогнозы успешно обработаны:", data);

  } catch (err) {
    // ❌ Если ошибка — логируем в консоль
    console.error("[loadPredictions] ❌ Ошибка загрузки прогнозов", err);
  }
}

// --- Графики истории значений параметров ---
async function loadParameterHistory(paramKey, dateStr) {
  const chartId = `history-chart-${paramKey}`;
  const emptyId = `history-chart-empty-${paramKey}`;
  const ctx = document.getElementById(chartId);
  const emptyDiv = document.getElementById(emptyId);
  if (!ctx) return;

  // Удаляем старый график, если есть
  if (ctx._chartInstance) {
    ctx._chartInstance.destroy();
    ctx._chartInstance = null;
  }

  try {
    const res = await fetch(`/api/parameter_history/?param=${encodeURIComponent(paramKey)}&date=${encodeURIComponent(dateStr)}`);
    const data = await res.json();
    if (!data.dates || !data.values || data.dates.length === 0) {
      ctx.style.display = 'none';
      if (emptyDiv) emptyDiv.style.display = '';
      return;
    }
    ctx.style.display = '';
    if (emptyDiv) emptyDiv.style.display = 'none';

    // Один dataset, цвет линии меняется динамически через segment.borderColor
    const monthsRu = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
    const labels = data.dates.map(d => {
      const [y, m, d2] = d.split('-');
      return `${parseInt(d2,10)} ${monthsRu[parseInt(m,10)-1]}`;
    });
    ctx._chartInstance = new window.Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: '',
          data: data.values,
          borderColor: '#28a745', // по умолчанию
          backgroundColor: 'rgba(40,167,69,0.10)',
          pointRadius: 2.5,
          pointBackgroundColor: '#28a745',
          pointBorderColor: '#222',
          borderWidth: 2,
          tension: 0.25,
          fill: true,
          spanGaps: true,
          segment: {
            borderColor: ctx => {
              const v = ctx.p0.parsed.y;
              return v >= 3 ? '#e0a800' : '#28a745';
            },
            backgroundColor: ctx => {
              const v = ctx.p0.parsed.y;
              return v >= 3 ? 'rgba(224,168,0,0.10)' : 'rgba(40,167,69,0.10)';
            }
          }
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: { enabled: true }
        },
        scales: {
          x: {
            ticks: { color: '#aaa', font: { size: 11 } },
            grid: { color: '#222' }
          },
          y: {
            min: 0, max: 5,
            ticks: { color: '#aaa', font: { size: 11 }, stepSize: 1 },
            grid: { color: '#222' }
          }
        }
      }
    });
  } catch (e) {
    ctx.style.display = 'none';
    if (emptyDiv) emptyDiv.style.display = '';
  }
}

// --- Инициализация графиков для всех параметров ---
function initAllParameterCharts(dateStr) {
  document.querySelectorAll('.parameter-block').forEach(block => {
    const paramKey = block.getAttribute('data-key');
    loadParameterHistory(paramKey, dateStr);
  });
}

// --- Управление отображением графиков ---
function setChartsVisible(visible) {
  document.querySelectorAll('.history-chart-block').forEach(block => {
    block.style.display = visible ? '' : 'none';
  });
  const btn = document.getElementById('charts-toggle-btn');
  if (btn) btn.classList.toggle('active', visible);
}

function saveChartsVisibleState(visible) {
  localStorage.setItem('diary_charts_visible', visible ? '1' : '0');
}

function loadChartsVisibleState() {
  const val = localStorage.getItem('diary_charts_visible');
  if (val === null) return true; // по умолчанию графики включены
  return val === '1';
}

function setupChartsToggleBtn() {
  const btn = document.getElementById('charts-toggle-btn');
  if (!btn) return;
  btn.addEventListener('click', function() {
    const nowVisible = !loadChartsVisibleState();
    setChartsVisible(nowVisible);
    saveChartsVisibleState(nowVisible);
  });
}

// --- Управление отображением прогнозов ---
function setPredictionsVisible(visible) {
  document.querySelectorAll('.prediction-wrapper').forEach(block => {
    block.style.display = visible ? '' : 'none';
  });
  const btn = document.getElementById('predictions-toggle-btn');
  if (btn) btn.classList.toggle('active', visible);
}

function savePredictionsVisibleState(visible) {
  localStorage.setItem('diary_predictions_visible', visible ? '1' : '0');
}

function loadPredictionsVisibleState() {
  const val = localStorage.getItem('diary_predictions_visible');
  if (val === null) return true; // по умолчанию прогнозы включены
  return val === '1';
}

function setupPredictionsToggleBtn() {
  const btn = document.getElementById('predictions-toggle-btn');
  if (!btn) return;
  btn.addEventListener('click', function() {
    const nowVisible = !loadPredictionsVisibleState();
    setPredictionsVisible(nowVisible);
    savePredictionsVisibleState(nowVisible);
  });
}
