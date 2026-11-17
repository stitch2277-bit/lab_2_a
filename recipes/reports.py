"""Вывод снимка расчёта и экспорт в настоящий Excel 97–2003 (.xls)."""

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


def formatted(value):
    return format(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f")


def render_result(result):
    lines = [f"\n{result['kind']} «{result['name']}»; порций: {result['portions']}"]
    for item in result["ingredients"]:
        lines.append(
            f"  {item['name']}: {formatted(item['grams'])} г; "
            f"{formatted(item['calories'])} ккал; {formatted(item['cost'])} руб."
        )
    lines.extend([
        f"Общая масса ингредиентов: {formatted(result['total_grams'])} г",
        f"Калорийность всего рецепта: {formatted(result['total_calories'])} ккал",
        f"Стоимость всего рецепта: {formatted(result['total_cost'])} руб.",
        f"Одна порция: {formatted(result['portion_grams'])} г; "
        f"{formatted(result['portion_calories'])} ккал; {formatted(result['portion_cost'])} руб.",
        f"Калорийность на 100 г ингредиентов: {formatted(result['kcal_per_100g'])} ккал",
        "Расчёт по массе ингредиентов: потери при готовке и дополнительные расходы не учтены.",
    ])
    return "\n".join(lines)


def export_xls(result, path, *, overwrite=False):
    """Текст записывается текстом, даже если имя начинается с '='."""
    try:
        import xlwt
    except ImportError:
        raise RuntimeError("Для экспорта установите зависимости: python -m pip install -r requirements.txt") from None

    destination = Path(path).expanduser()
    if destination.suffix.lower() != ".xls":
        raise ValueError("Имя отчёта должно оканчиваться на .xls.")
    if destination.exists() and not overwrite:
        raise FileExistsError("Файл уже существует. Выберите другое имя или подтвердите перезапись.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    book = xlwt.Workbook(encoding="utf-8")
    sheet = book.add_sheet("Расчёт рецепта")
    heading = xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray25;")
    numeric = xlwt.easyxf(num_format_str="0.00")
    sheet.col(0).width = 42 * 256
    for column in range(1, 6):
        sheet.col(column).width = 21 * 256
    sheet.write(0, 0, "Калькулятор рецептов", heading)
    sheet.write(1, 0, "Тип блюда")
    sheet.write(1, 1, result["kind"])
    sheet.write(2, 0, "Название")
    sheet.write(2, 1, result["name"])
    sheet.write(3, 0, "Количество порций")
    sheet.write(3, 1, result["portions"])
    headers = ("Ингредиент", "Масса, г", "Ккал на 100 г", "Руб. на 100 г", "Калории, ккал", "Стоимость, руб.")
    for column, title in enumerate(headers):
        sheet.write(5, column, title, heading)
    for row, item in enumerate(result["ingredients"], 6):
        sheet.write(row, 0, item["name"])
        for column, key in enumerate(("grams", "kcal_per_100g", "price_per_100g", "calories", "cost"), 1):
            sheet.write(row, column, float(Decimal(formatted(item[key]))), numeric)
    row = len(result["ingredients"]) + 7
    for title, key in (
        ("Общая масса, г", "total_grams"),
        ("Калории всего, ккал", "total_calories"),
        ("Стоимость всего, руб.", "total_cost"),
        ("Масса порции, г", "portion_grams"),
        ("Калории порции, ккал", "portion_calories"),
        ("Стоимость порции, руб.", "portion_cost"),
        ("Ккал на 100 г ингредиентов", "kcal_per_100g"),
    ):
        sheet.write(row, 0, title)
        sheet.write(row, 1, float(Decimal(formatted(result[key]))), numeric)
        row += 1
    sheet.write(row + 1, 0, "Модель: без потерь при готовке и дополнительных расходов.")
    if "created_at" in result:
        sheet.write(row + 2, 0, "Время сохранения (UTC)")
        sheet.write(row + 2, 1, result["created_at"])
    # Эксклюзивное создание защищает существующий файл и при гонке имён.
    mode = "wb" if overwrite else "xb"
    with destination.open(mode) as stream:
        book.save(stream)
    return destination.resolve()
