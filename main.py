"""Консольный калькулятор рецептов для Windows и Docker."""

import argparse
import os
import sqlite3
from pathlib import Path

from recipes.models import Burger, Ingredient, Pizza, Wok
from recipes.reports import export_xls, render_result
from recipes.storage import CalculationStore

VERSION = "1.2.0"
ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("RECIPES_DATA_DIR", str(ROOT / "data")))

HELP = """
СПРАВКА
Назначение: расчёт калорийности и стоимости вока, бургера и пиццы.
1. Выберите «Новый рецепт» и тип блюда.
2. Введите название, число порций и ингредиенты.
3. Для каждого ингредиента укажите массу в ГРАММАХ, ккал НА 100 Г
   и цену в РУБЛЯХ НА 100 Г. Значения берите с упаковки или вводите сами.
   Цена на 100 г = цена упаковки / масса упаковки в граммах * 100.
4. Программа покажет сумму для рецепта, на порцию и ккал на 100 г.
5. После расчёта результат автоматически сохраняется в SQLite.
6. Пункт «Сохранить в Excel» создаёт настоящий .xls, включая ингредиенты.
   Расчёт из истории можно открыть и повторно выгрузить.

Ввод: точка или запятая, до 4 знаков после неё, значения до 1000000.
Масса строго положительна; цена и калорийность могут быть равны нулю.
Порций и ингредиентов — от 1 до 1000. Названия — до 100 символов.
«?» или «справка» на любом запросе показывает эту справку и повторяет ввод.
«назад» или «отмена» отменяет текущую операцию и возвращает меню.
«выход», «exit» или Ctrl+C завершает программу. Ctrl+D/Ctrl+Z — конец ввода.

Формулы: ккал = масса * ккал_на_100г / 100;
стоимость = масса * цена_на_100г / 100. Сначала суммы, затем округление.
Все порции считаются одинаковыми. Потери массы при готовке не учитываются.
Цены и пищевая ценность примеров учебные. Это стоимость ингредиентов,
без доставки, электричества, работы повара и наценки.
"""

ABOUT = f"""
Калькулятор рецептов {VERSION}
Лабораторная работа №2 «Модули и пакеты Python. ООП».
Вариант 9 по порядку: «Рецепты» (ошибочная метка №11 в методичке).
Типы блюд: вок, бургер, пицца. Реализованы ООП, SQLite и экспорт.
Контейнерный запуск и его проверка описаны в DOCKER.md.
Автор: впишите ФИО и группу в REPORT.md перед сдачей.
Данные хранятся локально; подключение к интернету при работе не требуется.
"""


def ask(prompt):
    while True:
        value = input(prompt).strip()
        command = value.casefold()
        if command in ("?", "справка"):
            print(HELP)
        elif command in ("назад", "отмена"):
            raise InterruptedError
        elif command in ("выход", "exit"):
            raise EOFError
        else:
            return value


def read_value(prompt, converter):
    while True:
        try:
            return converter(ask(prompt))
        except ValueError as error:
            print(f"Ошибка ввода: {error}")


def integer(value):
    try:
        result = int(value)
    except ValueError:
        raise ValueError("Введите целое число от 1 до 1000.") from None
    if not 1 <= result <= 1000:
        raise ValueError("Введите целое число от 1 до 1000.")
    return result


def make_recipe():
    from recipes.models import number, text

    kinds = {"1": Wok, "2": Burger, "3": Pizza}
    print("\nТип блюда: 1 — Вок; 2 — Бургер; 3 — Пицца.")
    def choose(value):
        if value not in kinds:
            raise ValueError("Выберите 1, 2 или 3.")
        return kinds[value]
    recipe_class = read_value("Тип: ", choose)
    name = read_value("Название рецепта: ", lambda value: text(value, "Рецепт"))
    portions = read_value("Количество порций: ", integer)
    count = read_value("Количество ингредиентов: ", integer)
    ingredients = []
    for index in range(count):
        print(f"\nИнгредиент {index + 1} из {count}")
        ingredient_name = read_value("Название: ", lambda value: text(value, "Ингредиент"))
        grams = read_value("Масса, г: ", lambda value: number(value, "Масса", positive=True))
        calories = read_value("Калорийность, ккал на 100 г: ", lambda value: number(value, "Калорийность"))
        price = read_value("Цена, руб. на 100 г: ", lambda value: number(value, "Цена"))
        ingredients.append(Ingredient(ingredient_name, grams, calories, price))
    return recipe_class(name, portions, ingredients)


def demo_recipe(kind="pizza"):
    """Значения демонстрационные; не выдаются за справочник продуктов."""
    examples = {
        "pizza": (Pizza, "Учебная пицца", 2, [
            ("Тесто", 200, 250, 20), ("Сыр", 100, 350, 80), ("Томаты", 100, 20, 30)]),
        "wok": (Wok, "Учебный вок", 2, [
            ("Лапша", 200, 150, 20), ("Курица", 150, 165, 40), ("Овощи", 150, 35, 15)]),
        "burger": (Burger, "Учебный бургер", 1, [
            ("Булочка", 80, 260, 25), ("Котлета", 100, 250, 70), ("Овощи", 50, 25, 20)]),
    }
    recipe_class, name, portions, rows = examples[kind]
    return recipe_class(name, portions, [Ingredient(*row) for row in rows])


def save_calculation(store, recipe):
    result = recipe.snapshot()
    print(render_result(result))
    try:
        record_id = store.save(recipe)
        result = store.get(record_id)
        print(f"Расчёт №{record_id} сохранён в базе данных.")
    except (sqlite3.Error, OSError) as error:
        print(f"Не удалось сохранить в БД: {error}. Расчёт доступен для экспорта в Excel.")
    return result


def save_report(result):
    if result is None:
        print("Сначала создайте расчёт или откройте запись из истории.")
        return
    default = DATA_DIR / "reports" / f"recipe_{result.get('id', 'current')}.xls"
    raw = ask(f"Путь к .xls [Enter — {default}]: ")
    path = Path(raw).expanduser() if raw else default
    overwrite = False
    if path.exists():
        overwrite = ask("Файл существует. Перезаписать? [да/нет]: ").casefold() in ("да", "yes", "y")
        if not overwrite:
            print("Сохранение отменено; прежний файл сохранён.")
            return
    print(f"Отчёт сохранён: {export_xls(result, path, overwrite=overwrite)}")


def show_history(store):
    history = store.history()
    if not history:
        print("История пуста. Выполните первый расчёт.")
        return None
    print("\nПоследние 20 расчётов (время UTC):")
    for result in history:
        print(f"№{result['id']} | {result['created_at']} | {result['kind']} «{result['name']}»")
    value = ask("Номер расчёта для просмотра [Enter — вернуться]: ")
    if not value:
        return None
    try:
        record_id = int(value)
    except ValueError:
        raise ValueError("Номер расчёта должен быть положительным целым числом.") from None
    if record_id <= 0:
        raise ValueError("Номер расчёта должен быть положительным целым числом.")
    result = store.get(record_id)
    print(render_result(result))
    return result


def menu(store):
    current = None
    print(f"Калькулятор рецептов {VERSION}. Справка — пункт 5 или «?».")
    print(f"База данных: {store.path.resolve()}")
    while True:
        print("\n1. Новый рецепт\n2. Демонстрационный расчёт\n3. История расчётов"
              "\n4. Сохранить текущий расчёт в Excel\n5. Справка\n6. О программе\n0. Выход")
        try:
            choice = ask("Выберите пункт: ")
            if choice == "0":
                return
            if choice == "1":
                current = save_calculation(store, make_recipe())
            elif choice == "2":
                current = save_calculation(store, demo_recipe())
            elif choice == "3":
                opened = show_history(store)
                if opened is not None:
                    current = opened
            elif choice == "4":
                save_report(current)
            elif choice == "5":
                print(HELP)
            elif choice == "6":
                print(ABOUT)
            else:
                print("Неизвестный пункт. Выберите число от 0 до 6.")
        except InterruptedError:
            print("Операция отменена. Возврат в главное меню.")
        except (ValueError, OSError, sqlite3.Error, RuntimeError) as error:
            print(f"Ошибка: {error}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Калькулятор рецептов. Вариант 9 по порядку (№11 в таблице).",
        epilog="Без параметров открывается меню. Пример: python main.py --demo pizza --export data/pizza.xls",
    )
    parser.add_argument("--version", action="version", version=f"Калькулятор рецептов {VERSION}")
    parser.add_argument("--guide", action="store_true", help="показать встроенную справку")
    # Старые команды с --cli продолжают работать; меню теперь открывается по умолчанию.
    parser.add_argument("--cli", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--demo", choices=("pizza", "wok", "burger"), help="рассчитать учебный пример")
    parser.add_argument("--export", type=Path, metavar="FILE.xls", help="сохранить результат --demo без перезаписи существующего файла")
    parser.add_argument("--db", type=Path, default=DATA_DIR / "recipes.sqlite3", help="путь к базе SQLite")
    args = parser.parse_args(argv)
    if args.export and not args.demo:
        parser.error("--export используется вместе с --demo")
    if args.guide:
        print(HELP)
        return 0
    try:
        with CalculationStore(args.db) as store:
            if args.demo:
                result = save_calculation(store, demo_recipe(args.demo))
                if args.export:
                    print(f"Отчёт сохранён: {export_xls(result, args.export)}")
            else:
                menu(store)
    except (KeyboardInterrupt, EOFError):
        print("\nВвод завершён. Программа закрыта.")
    except (OSError, sqlite3.Error, ValueError, RuntimeError) as error:
        print(f"Ошибка: {error}")
        return 1
    else:
        print("Работа завершена.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
