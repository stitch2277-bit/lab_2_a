import builtins
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

import main
from recipes.storage import CalculationStore


def user_input(monkeypatch, values):
    iterator = iter(values)
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(iterator))


def test_menu_help_about_invalid_choice_and_exit(tmp_path, monkeypatch, capsys):
    user_input(monkeypatch, ["99", "5", "6", "0"])
    assert main.main(["--db", str(tmp_path / "db.sqlite3")]) == 0
    output = capsys.readouterr().out
    for text in ("Неизвестный пункт", "СПРАВКА", "О программе", main.VERSION, "Работа завершена"):
        assert text in output


def test_manual_recipe_recovers_after_bad_input_and_saves(tmp_path, monkeypatch, capsys):
    path = tmp_path / "manual.sqlite3"
    user_input(monkeypatch, [
        "1", "9", "3", "Моя пицца", "0", "2", "1", "Сыр",
        "NaN", "-1", "100,5", "350", "80", "3", "1", "0",
    ])
    assert main.main(["--db", str(path)]) == 0
    with CalculationStore(path) as store:
        result = store.get(1)
        assert result["name"] == "Моя пицца"
        assert result["total_cost"] == "80.4"
    output = capsys.readouterr().out
    assert "Ошибка ввода" in output
    assert "Расчёт №1 сохранён" in output


def test_cancel_leaves_database_empty(tmp_path, monkeypatch):
    path = tmp_path / "cancel.sqlite3"
    user_input(monkeypatch, ["1", "отмена", "0"])
    assert main.main(["--db", str(path)]) == 0
    with CalculationStore(path) as store:
        assert len(store) == 0


def test_context_help_repeats_the_same_question(monkeypatch, capsys):
    user_input(monkeypatch, ["?", "2"])
    assert main.read_value("Порций: ", main.integer) == 2
    assert "СПРАВКА" in capsys.readouterr().out


@pytest.mark.parametrize("signal", [EOFError, KeyboardInterrupt])
def test_eof_and_ctrl_c_close_cleanly(tmp_path, monkeypatch, capsys, signal):
    def stop(prompt=""):
        raise signal
    monkeypatch.setattr(builtins, "input", stop)
    path = tmp_path / "quit.sqlite3"
    assert main.main(["--db", str(path)]) == 0
    assert "Программа закрыта" in capsys.readouterr().out
    # Закрытое соединение не удерживает блокировку после выхода.
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE calculations")


def test_guide_does_not_create_database(tmp_path, capsys):
    path = tmp_path / "not_created.sqlite3"
    assert main.main(["--guide", "--db", str(path)]) == 0
    assert not path.exists()
    assert "СПРАВКА" in capsys.readouterr().out


def test_cli_demo_and_export(tmp_path, capsys):
    path = tmp_path / "demo.xls"
    assert main.main(["--demo", "pizza", "--db", str(tmp_path / "db.sqlite3"), "--export", str(path)]) == 0
    assert path.is_file()
    assert "Отчёт сохранён" in capsys.readouterr().out
    assert main.main(["--demo", "pizza", "--db", str(tmp_path / "db.sqlite3"), "--export", str(path)]) == 1


def test_export_requires_demo(tmp_path):
    with pytest.raises(SystemExit) as error:
        main.main(["--export", str(tmp_path / "report.xls")])
    assert error.value.code == 2


def test_database_error_is_explained(tmp_path, capsys):
    # Каталог с именем файла БД — воспроизводимая ошибка без прав администратора.
    path = tmp_path / "directory"
    path.mkdir()
    assert main.main(["--db", str(path)]) == 1
    assert "Ошибка:" in capsys.readouterr().out


def test_database_failure_preserves_result_for_export(tmp_path, monkeypatch, capsys):
    with CalculationStore(tmp_path / "db.sqlite3") as store:
        def fail(recipe):
            raise sqlite3.OperationalError("test write failure")
        monkeypatch.setattr(store, "save", fail)
        result = main.save_calculation(store, main.demo_recipe())
        assert result["total_cost"] == "150"
        assert "доступен для экспорта" in capsys.readouterr().out


def test_export_overwrite_refusal_preserves_file(tmp_path, monkeypatch, capsys):
    path = tmp_path / "existing.xls"
    path.write_bytes(b"original")
    user_input(monkeypatch, [str(path), "нет"])
    main.save_report(main.demo_recipe().snapshot())
    assert path.read_bytes() == b"original"
    assert "Сохранение отменено" in capsys.readouterr().out


def test_default_entrypoint_opens_console_help_and_about(tmp_path):
    env = os.environ.copy()
    env["RECIPES_DATA_DIR"] = str(tmp_path)
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, str(Path(main.__file__))],
        input="5\n6\n0\n", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", env=env, timeout=20,
    )
    assert result.returncode == 0, result.stderr
    for text in ("1. Новый рецепт", "СПРАВКА", main.VERSION, "Работа завершена"):
        assert text in result.stdout
    with CalculationStore(tmp_path / "recipes.sqlite3") as store:
        assert len(store) == 0
