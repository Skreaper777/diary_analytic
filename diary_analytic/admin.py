from django.contrib import admin, messages
from django import forms
from django.shortcuts import redirect
from django.urls import path
import pandas as pd
from .models import Parameter
from django.template.response import TemplateResponse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _  # для надписей, если надо переводить интерфейс

class ExcelImportForm(forms.Form):
    excel_file = forms.FileField(label="Excel-файл с параметрами")


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "is_active")
    actions = None

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-excel/", self.admin_site.admin_view(self.import_excel), name="import_excel"),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_button"] = format_html(
            '<a class="button" href="import-excel/">📥 Импорт из Excel</a>'
        )
        return super().changelist_view(request, extra_context=extra_context)

    def import_excel(self, request):
        form = ExcelImportForm(request.POST or None, request.FILES or None)

        if request.method == "POST" and form.is_valid():
            try:
                df = pd.read_excel(form.cleaned_data["excel_file"])
                if not {"key", "name"}.issubset(df.columns):
                    self.message_user(request, "❌ В Excel не хватает колонок 'key' и 'name'", messages.ERROR)
                    return redirect("..")

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

                self.message_user(request, f"✅ Импорт завершён: создано {created}, обновлено {updated}")
                return redirect("..")

            except Exception as e:
                self.message_user(request, f"❌ Ошибка импорта: {e}", messages.ERROR)
                return redirect("..")

        context = {
            "title": "Импорт параметров из Excel",
            "form": form,
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "admin/import_excel.html", context)


