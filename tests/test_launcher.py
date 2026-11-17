"""Регрессия реального cmd.exe: пути с пробелами и кириллицей, аргументы и ошибки."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Проверка батника Windows")
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def launcher(tmp_path):
    project = tmp_path / "Проверка запуска с пробелами"
    project.mkdir()
    shutil.copyfile(ROOT / "run.bat", project / "run.bat")
    (project / "main.py").write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "print('Проверка запуска', flush=True)\n"
        "Path('started.txt').write_text(str(Path.cwd()), encoding='utf-8')\n"
        "if '--fail' in sys.argv:\n"
        "    print('Ошибка для проверки журнала', file=sys.stderr, flush=True)\n"
        "    raise SystemExit(7)\n"
        "if '--ask' in sys.argv:\n"
        "    print('Ответ:', input('Введите ответ: '), flush=True)\n"
        "print('Arguments:', '|'.join(sys.argv[1:]), flush=True)\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    # Без локальной .venv батник найдёт именно интерпретатор этого запуска pytest.
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    return project, env


def run_batch(project, env, cwd, *args, input_text=None):
    return subprocess.run(
        [env.get("COMSPEC", "cmd.exe"), "/d", "/c", "call", str(project / "run.bat"), *args],
        cwd=cwd, env=env,
        **({"stdin": subprocess.DEVNULL} if input_text is None else {"input": input_text}),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        encoding="utf-8", errors="replace", timeout=20,
    )


def test_batch_launches_and_passes_arguments(launcher):
    project, env = launcher
    result = run_batch(project, env, project, "--version", "argument with spaces")
    assert result.returncode == 0, result.stdout
    assert "Проверка запуска" in result.stdout
    assert "--version|argument with spaces" in result.stdout
    assert (project / "started.txt").exists()


def test_batch_uses_project_folder_from_any_working_directory(launcher, tmp_path):
    project, env = launcher
    outside = tmp_path / "Другая папка"
    outside.mkdir()
    result = run_batch(project, env, outside)
    assert result.returncode == 0, result.stdout
    assert Path((project / "started.txt").read_text(encoding="utf-8")) == project
    assert not (outside / "started.txt").exists()


def test_batch_reports_real_error_and_keeps_failure_code(launcher):
    project, env = launcher
    result = run_batch(project, env, project, "--fail")
    assert result.returncode == 7, result.stdout
    assert "Ошибка для проверки журнала" in result.stdout
    assert "Code: 7" in result.stdout
    assert "pip install -r" in result.stdout


def test_batch_keeps_interactive_input_and_output(launcher):
    project, env = launcher
    result = run_batch(project, env, project, "--ask", input_text="Привет из консоли\n")
    assert result.returncode == 0, result.stdout
    assert "Введите ответ:" in result.stdout
    assert "Ответ: Привет из консоли" in result.stdout
