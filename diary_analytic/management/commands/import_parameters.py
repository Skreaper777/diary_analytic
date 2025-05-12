from django.core.management.base import BaseCommand
import pandas as pd
from diary_analytic.models import Parameter


class Command(BaseCommand):
    help = "Импортирует параметры из Excel-файла в таблицу Parameter"

    def add_arguments(self, parser):
        parser.add_argument("xlsx_file", type=str, help="Путь к Excel-файлу")

    def handle(self, *args, **options):
        file_path = options["xlsx_file"]

        # Загружаем таблицу
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Не удалось прочитать Excel: {e}"))
            return

        # Проверяем нужные столбцы
        if not {"key", "name"}.issubset(df.columns):
            self.stderr.write(self.style.ERROR("❌ В файле должны быть колонки: key, name"))
            return

        # Счётчики
        created, updated = 0, 0

        for _, row in df.iterrows():
            key = str(row["key"]).strip()
            name = str(row["name"]).strip()

            param, is_created = Parameter.objects.update_or_create(
                key=key,
                defaults={"name": name, "is_active": True},
            )
            if is_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Импорт завершён: создано {created}, обновлено {updated}"))
