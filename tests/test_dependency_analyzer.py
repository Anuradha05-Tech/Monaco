from app.analyzer.dependency_analyzer import DependencyAnalyzer


def test_simple_import_statements():
    code = """
import os
import sys
"""
    analyzer = DependencyAnalyzer()
    assert analyzer.analyze(code) == ["os", "sys"]


def test_multiple_imports_on_one_line():
    code = """
import os, sys, math
"""
    analyzer = DependencyAnalyzer()
    assert analyzer.analyze(code) == ["math", "os", "sys"]


def test_from_import_statements():
    code = """
from pathlib import Path
from json import loads
"""
    analyzer = DependencyAnalyzer()
    assert analyzer.analyze(code) == ["json", "pathlib"]


def test_dotted_module_paths():
    code = """
from urllib.request import urlopen
from app.database.query import execute
"""
    analyzer = DependencyAnalyzer()
    assert analyzer.analyze(code) == ["app.database.query", "urllib.request"]


def test_multiple_from_imports_same_module():
    code = """
from pathlib import Path, PurePath, PosixPath
"""
    analyzer = DependencyAnalyzer()
    assert analyzer.analyze(code) == ["pathlib"]


def test_relative_imports():
    code = """
from . import utils
from .foo import bar
from .. import config
from ..baz import qux
"""
    analyzer = DependencyAnalyzer()
    assert analyzer.analyze(code) == ["..baz", "..config", ".foo", ".utils"]



def test_no_imports():
    code = """
def hello_world():
    print("Hello, world!")
"""
    analyzer = DependencyAnalyzer()
    assert analyzer.analyze(code) == []


def test_invalid_syntax_graceful_handling():
    code = """
def hello_world(
    print("Hello, world!")
"""
    analyzer = DependencyAnalyzer()
    assert analyzer.analyze(code) == []


def test_deduplication_and_sorting():
    code = """
import sys
from os import path
import os
import sys
from pathlib import Path
"""
    analyzer = DependencyAnalyzer()
    assert analyzer.analyze(code) == ["os", "pathlib", "sys"]
