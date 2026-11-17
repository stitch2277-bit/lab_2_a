"""Проверка реального образа, расчёта и сохранности SQLite между контейнерами.

Запуск: python verify_docker.py. Нужны Docker CLI и работающий Docker Engine.
Для проверки используются отдельные данные .qa/docker-*; история пользователя не меняется.
"""

from datetime import datetime, timezone
from pathlib import Path
import os
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent


def find_docker():
    """Найти Docker, включая per-user установку до обновления PATH терминала."""
    executable = shutil.which("docker")
    if executable or os.name != "nt":
        return executable
    local = Path.home() / "AppData" / "Local"
    candidates = (
        Path(os.environ.get("LOCALAPPDATA", local)) / "Programs/DockerDesktop/resources/bin/docker.exe",
        local / "Programs/DockerDesktop/resources/bin/docker.exe",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Docker/Docker/resources/bin/docker.exe",
    )
    return next((str(path) for path in candidates if path.is_file()), None)


def main():
    log_path = ROOT / "docs" / "docker-verification.txt"
    log_path.parent.mkdir(exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        def report(message):
            print(message)
            log.write(message + "\n")
            log.flush()

        report("Docker verification: " + datetime.now(timezone.utc).isoformat())
        docker = find_docker()
        if docker is None:
            report("NOT RUN: Docker CLI is not installed or is not in PATH.")
            report("No image was built and no container was started.")
            return 2
        docker_env = os.environ.copy()
        docker_env["PATH"] = str(Path(docker).parent) + os.pathsep + docker_env.get("PATH", "")

        def execute(*args):
            report("\n> docker " + " ".join(args))
            # Потоковый вывод показывает ход первой загрузки образа и установки пакетов.
            with subprocess.Popen(
                [docker, *args], cwd=ROOT, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=docker_env,
            ) as process:
                for line in process.stdout:
                    report(line.rstrip())
                if process.wait():
                    raise subprocess.CalledProcessError(process.returncode, process.args)

        try:
            execute("version")
            execute("build", "--tag", "recipes-lab:local", ".")
            qa = ROOT / ".qa"
            qa.mkdir(exist_ok=True)
            # Каталог сохраняется для просмотра результатов; каждый запуск создаёт новый.
            evidence = Path(tempfile.mkdtemp(prefix="docker-", dir=qa))
            mount = f"type=bind,source={evidence},target=/app/data"
            execute("run", "--rm", "--mount", mount, "recipes-lab:local",
                    "--demo", "pizza", "--export", "/app/data/pizza.xls")
            check = (
                "import json,sqlite3; from pathlib import Path; "
                "db=sqlite3.connect('/app/data/recipes.sqlite3'); "
                "rows=db.execute('SELECT payload FROM calculations').fetchall(); "
                "assert len(rows)==1,rows; r=json.loads(rows[0][0]); "
                "assert r['total_cost']=='150',r; assert r['total_calories']=='870',r; "
                "assert Path('/app/data/pizza.xls').read_bytes()[:8]==bytes.fromhex('D0CF11E0A1B11AE1'); "
                "db.close(); print('PASS: second container read the first container database and XLS report')"
            )
            execute("run", "--rm", "--mount", mount, "--entrypoint", "python",
                    "recipes-lab:local", "-c", check)
            execute("image", "inspect", "recipes-lab:local", "--format", "{{.Id}}")
            report("\nPASS: image built; calculation and persistence between two containers verified.")
            report("Evidence: " + str(evidence))
            return 0
        except (OSError, subprocess.CalledProcessError) as error:
            report("\nFAILED: " + str(error))
            report("The container check did not complete successfully.")
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
