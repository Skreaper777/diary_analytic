from django.contrib import admin, messages
from django import forms
from django.shortcuts import redirect
from django.urls import path
from django.template.response import TemplateResponse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.conf import settings

import os
import pandas as pd
from slugify import slugify

from .models import Entry, EntryValue, Parameter


# 📥 Форма для загрузки Excel-файла
class ExcelImportForm(forms.Form):
    excel_file = forms.FileField(label="Excel-файл с данными")


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
                columns = [col.strip() for col in df.columns]
                df.columns = columns

                if len(columns) < 2:
                    self.message_user(request, "❌ Файл должен содержать дату и хотя бы один параметр", messages.ERROR)
                    return redirect("..")

                param_cache = {p.name_ru.strip(): p for p in Parameter.objects.all()}
                param_counter = len(param_cache)
                entries = {}
                entry_values_to_create = []
                entry_values_to_update = []
                existing_entry_values = {
                    (ev.entry_id, ev.parameter_id): ev
                    for ev in EntryValue.objects.select_related("entry", "parameter")
                }

                for index, row in df.iterrows():
                    date_str = str(row[columns[0]]).strip()
                    try:
                        entry_date = pd.to_datetime(date_str).date()
                    except Exception as e:
                        self.message_user(request, f"⚠️ Пропущена строка с некорректной датой '{date_str}': {e}", messages.WARNING)
                        continue

                    if entry_date not in entries:
                        entries[entry_date], _ = Entry.objects.get_or_create(date=entry_date)

                    entry = entries[entry_date]

                    for col in columns[1:]:
                        value = row[col]
                        if pd.isnull(value):
                            continue

                        name_ru = col.strip()
                        param = param_cache.get(name_ru)

                        if not param:
                            key = slugify(name_ru)
                            if not key:
                                param_counter += 1
                                key = f"param_{param_counter}"
                            param = Parameter.objects.create(name=name_ru, key=key)
                            param_cache[name_ru] = param

                        key_tuple = (entry.id, param.id)
                        if key_tuple in existing_entry_values:
                            ev = existing_entry_values[key_tuple]
                            ev.value = float(value)
                            entry_values_to_update.append(ev)
                        else:
                            ev = EntryValue(entry=entry, parameter=param, value=float(value))
                            entry_values_to_create.append(ev)

                if entry_values_to_create:
                    EntryValue.objects.bulk_create(entry_values_to_create)
                if entry_values_to_update:
                    EntryValue.objects.bulk_update(entry_values_to_update, ["value"])

                created = len(entry_values_to_create)
                updated = len(entry_values_to_update)

                self.message_user(request, f"✅ Импорт завершён. Создано: {created}, обновлено: {updated}", messages.SUCCESS)
                return redirect("..")

            except Exception as e:
                self.message_user(request, f"❌ Ошибка при импорте: {e}", messages.ERROR)
                return redirect("..")

        context = {
            "title": "Импорт Excel-файла с Entry и параметрами",
            "form": form,
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "admin/import_excel.html", context)
