"""Bundled Athena pipeline layout and optional Olympus wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_bundled_athena_yaml_present():
    base = REPO_ROOT / "repo_analyser" / "pipelines" / "athena"
    assert (base / "athena-pipeline.yaml").is_file()
    agents = base / "agents"
    names = {p.name for p in agents.glob("*.yaml")}
    expected = {
        "lethe.yaml",
        "iris.yaml",
        "pallas.yaml",
        "asclepius.yaml",
        "daedalus.yaml",
        "nike.yaml",
        "tyche.yaml",
        "arete.yaml",
        "athena.yaml",
    }
    assert expected <= names


def test_bundled_athena_paths_from_package():
    from repo_analyser.pipeline_runner import bundled_athena_paths

    p, a = bundled_athena_paths()
    assert p.name == "athena-pipeline.yaml"
    assert (a / "athena.yaml").is_file()


def test_register_schemas_for_athena():
    pytest.importorskip("olympus")
    from olympus.athena_state import register_athena_schemas
    from olympus.iris_tools import register_iris
    from olympus.schema_registry import resolve_state_schema

    register_athena_schemas()
    register_iris()
    cls = resolve_state_schema("AthenaPipelineState")
    assert cls.__name__ == "AthenaPipelineState"
