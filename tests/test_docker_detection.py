"""Docker Desktop доступен сразу после установки, даже со старым PATH терминала."""
import os
from pathlib import Path

import pytest

import verify_docker


def test_docker_from_path_has_priority(monkeypatch):
    monkeypatch.setattr(verify_docker.shutil, "which", lambda name: "docker-from-path")
    assert verify_docker.find_docker() == "docker-from-path"


@pytest.mark.skipif(os.name != "nt", reason="Установка Docker Desktop в Windows")
def test_per_user_docker_found_with_old_path(monkeypatch, tmp_path):
    monkeypatch.setattr(verify_docker.shutil, "which", lambda name: None)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "user"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "user/AppData/Local"))
    executable = tmp_path / "user/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"test executable location")
    assert Path(verify_docker.find_docker()) == executable


@pytest.mark.skipif(os.name != "nt", reason="Установка Docker Desktop в Windows")
def test_missing_docker_is_reported_as_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(verify_docker.shutil, "which", lambda name: None)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "user"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "programs"))
    assert verify_docker.find_docker() is None
