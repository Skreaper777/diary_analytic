from diary_analytic.models import Entry, EntryValue, Parameter
from slugify import slugify
import pandas as pd

def import_excel_dataframe(df) -> tuple[int, int]:
    columns = [col.strip() for col in df.columns]
    df.columns = columns

    if len(columns) < 2:
        raise ValueError("Файл должен содержать хотя бы два столбца: дата и параметры")

    param_cache = {p.name.strip(): p for p in Parameter.objects.all()}
    param_counter = len(param_cache)

    entries = {}
    entry_values_to_create = []
    entry_values_to_update = []

    existing_entry_values = {
        (ev.entry_id, ev.parameter_id): ev
        for ev in EntryValue.objects.select_related("entry", "parameter")
    }

    for _, row in df.iterrows():
        date_str = str(row[columns[0]]).strip()
        entry_date = pd.to_datetime(date_str).date()

        if entry_date not in entries:
            entries[entry_date], _ = Entry.objects.get_or_create(date=entry_date)

        entry = entries[entry_date]

        for col in columns[1:]:
            value = row[col]
            if pd.isnull(value):
                continue

            name = col.strip()
            param = param_cache.get(name)

            if not param:
                key = slugify(name)
                if not key:
                    param_counter += 1
                    key = f"param_{param_counter}"
                param = Parameter.objects.create(name=name, key=key)
                param_cache[name] = param

            key_tuple = (entry.id, param.id)
            if key_tuple in existing_entry_values:
                ev = existing_entry_values[key_tuple]
                ev.value = float(value)
                entry_values_to_update.append(ev)
            else:
                entry_values_to_create.append(EntryValue(entry=entry, parameter=param, value=float(value)))

    if entry_values_to_create:
        EntryValue.objects.bulk_create(entry_values_to_create)
    if entry_values_to_update:
        EntryValue.objects.bulk_update(entry_values_to_update, ["value"])

    return len(entry_values_to_create), len(entry_values_to_update)
