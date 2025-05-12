document.addEventListener("DOMContentLoaded", function () {
    // Получаем дату из input
    const dateInput = document.getElementById("date-input");
    const dateValue = dateInput ? dateInput.value : "";
  
    // Все блоки параметров
    const parameterBlocks = document.querySelectorAll(".parameter-block");
  
    parameterBlocks.forEach((block) => {
      const paramKey = block.getAttribute("data-key");
      const buttons = block.querySelectorAll(".value-button");
  
      buttons.forEach((btn) => {
        btn.addEventListener("click", async function () {
          const selectedValue = parseInt(this.getAttribute("data-value"));
  
          // 1. Подсветка активной кнопки
          buttons.forEach((b) => b.classList.remove("selected"));
          this.classList.add("selected");
  
          // 2. Отправка на сервер
          try {
            const response = await fetch("/update_value/", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
              },
              body: JSON.stringify({
                parameter: paramKey,
                value: selectedValue,
                date: dateValue,
              }),
            });
  
            if (response.ok) {
              console.log(`✅ Обновлено: ${paramKey} = ${selectedValue}`);
            } else {
              console.error(`❌ Ошибка обновления ${paramKey}`);
            }
          } catch (error) {
            console.error("Ошибка соединения:", error);
          }
        });
      });
    });
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
  