"""Shared fixtures for the stylized_facts tests.

model.py creates results/figures/ in the working directory when imported, so it is imported once
from a temporary folder. The scripts import it too, so they are loaded after it.
"""

import importlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("MPLBACKEND", "Agg")

SF_ROOT = Path(__file__).resolve().parents[1]   # stylized_facts/
REPO_ROOT = SF_ROOT.parent


@pytest.fixture(scope="session")
def im(tmp_path_factory):
    old = os.getcwd()
    os.chdir(tmp_path_factory.mktemp("import_dir"))
    try:
        return importlib.import_module("ising_market.model")
    finally:
        os.chdir(old)


def _load_script(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SF_ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def crm(im):
    return _load_script("compare_return_models")


@pytest.fixture(scope="session")
def mf(im):
    return _load_script("make_figures")


@pytest.fixture(scope="session")
def gx(im):
    return _load_script("garch_x_breadth")


@pytest.fixture(scope="session")
def kuf(im):
    return _load_script("k_under_feedback")
