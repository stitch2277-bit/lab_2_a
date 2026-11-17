from decimal import Decimal

import pytest
import xlrd

from main import demo_recipe
from recipes.models import Ingredient, Pizza
from recipes.reports import export_xls, render_result
from recipes.storage import CalculationStore


def test_database_survives_reopening_and_escapes_sql(tmp_path):
    path = tmp_path / "кириллица" / "history.sqlite3"
    recipe = demo_recipe()
    recipe.name = "'; DROP TABLE calculations; --"
    with CalculationStore(path) as store:
        first = store.save(recipe)
        second = store.save(demo_recipe("wok"))
        assert len(store) == 2
        assert [item["id"] for item in store.history(1)] == [second]
        assert str(path) in str(store)
    with CalculationStore(path) as store:
        result = store.get(first)
        assert result["name"] == recipe.name
        assert result["created_at"].endswith("+00:00")
        assert Decimal(result["total_cost"]) == 150
        assert result["ingredients"][0]["name"] == "Тесто"
        assert len(store) == 2


def test_empty_history_missing_id_and_invalid_limit(tmp_path):
    with CalculationStore(tmp_path / "empty.sqlite3") as store:
        assert store.history() == []
        with pytest.raises(ValueError, match="не найден"):
            store.get(42)
        with pytest.raises(ValueError):
            store.history(0)


def test_xls_roundtrip_unicode_numbers_and_totals(tmp_path):
    result = demo_recipe().snapshot()
    path = export_xls(result, tmp_path / "отчёты" / "пицца.xls")
    assert path.read_bytes().startswith(bytes.fromhex("D0CF11E0A1B11AE1"))
    with xlrd.open_workbook(str(path)) as book:
        assert book.biff_version == 80
        sheet = book.sheet_by_index(0)
        assert sheet.cell_value(2, 1) == "Учебная пицца"
        assert sheet.cell_value(6, 0) == "Тесто"
        assert sheet.cell_type(6, 1) == xlrd.XL_CELL_NUMBER
        assert sheet.cell_value(6, 1) == 200
        assert sheet.cell_value(12, 1) == 150


def test_xls_names_are_text_not_formulas(tmp_path):
    result = Pizza("=1+1", 1, [Ingredient("=HYPERLINK(\"https://example.com\")", 100, 1, 1)]).snapshot()
    path = export_xls(result, tmp_path / "text.xls")
    with xlrd.open_workbook(str(path)) as book:
        sheet = book.sheet_by_index(0)
        assert sheet.cell_type(2, 1) == xlrd.XL_CELL_TEXT
        assert sheet.cell_value(2, 1) == "=1+1"
        assert sheet.cell_type(6, 0) == xlrd.XL_CELL_TEXT


def test_export_does_not_overwrite_without_permission(tmp_path):
    path = tmp_path / "existing.xls"
    path.write_bytes(b"original")
    with pytest.raises(FileExistsError):
        export_xls(demo_recipe().snapshot(), path)
    assert path.read_bytes() == b"original"
    export_xls(demo_recipe().snapshot(), path, overwrite=True)
    assert path.read_bytes() != b"original"


def test_wrong_extension(tmp_path):
    with pytest.raises(ValueError, match=".xls"):
        export_xls(demo_recipe().snapshot(), tmp_path / "fake.xlsx")


def test_result_contains_units_and_limitations():
    result = render_result(demo_recipe().snapshot())
    for value in ("870.00 ккал", "150.00 руб.", "217.50 ккал", "435.00 ккал", "75.00 руб.", "потери"):
        assert value in result
