# -*- coding: utf-8 -*-
"""
Tests for the pure-Python logic in batch_dwg_to_rvt.py (no live Revit needed).

Everything else in that module touches real Revit API objects and can only
be exercised inside Revit - see the pyRevit harness for that.
"""

import os

import batch_dwg_to_rvt as b


def test_get_dwg_files_filters_to_dwg_only(tmp_path):
    (tmp_path / "a.dwg").write_text("")
    (tmp_path / "b.dxf").write_text("")
    (tmp_path / "notes.txt").write_text("")

    result = b.get_dwg_files(str(tmp_path))

    assert result == [str(tmp_path / "a.dwg")]


def test_get_dwg_files_is_case_insensitive(tmp_path):
    (tmp_path / "a.DWG").write_text("")
    (tmp_path / "b.Dwg").write_text("")

    result = sorted(b.get_dwg_files(str(tmp_path)))

    assert result == sorted([str(tmp_path / "a.DWG"), str(tmp_path / "b.Dwg")])


def test_get_dwg_files_empty_folder(tmp_path):
    assert b.get_dwg_files(str(tmp_path)) == []


def test_get_dwg_files_returns_full_paths(tmp_path):
    (tmp_path / "stand.dwg").write_text("")

    result = b.get_dwg_files(str(tmp_path))

    assert result == [os.path.join(str(tmp_path), "stand.dwg")]
