# -*- coding: utf-8 -*-
"""
pyRevit smoke-test harness for batch_dwg_to_rvt.py
====================================================

Runs the batch_dwg_to_rvt pipeline one stage at a time against a SINGLE
sample DWG, instead of the full 60-file batch loop - use this to iterate on
create_doc_from_template / import_or_link_dwg without waiting on the whole
pipeline (or Dynamo) each time.

Usage (inside Revit, with pyRevit installed):
    1. Edit TEST_TEMPLATE_PATH and TEST_DWG_PATH below.
    2. Open a project in Revit, then run this file as a pyRevit button, or
       paste its contents into pyRevit's Python console.
    3. Read the printed PASS/FAIL report - fix the failing stage, rerun.

The test document is left open (not saved/closed) so you can inspect the
result in the Revit UI - close it yourself between runs.

Does not touch batch_dwg_to_rvt.py's own DWG_FOLDER/OUTPUT_FOLDER config;
this is a separate, throwaway single-file run.
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import batch_dwg_to_rvt as b

# pyRevit injects __revit__ (UIApplication) as a builtin.
app = __revit__.Application

TEST_TEMPLATE_PATH = r"C:\Path\To\Your\StandardTemplate.rte"
TEST_DWG_PATH = r"C:\Path\To\Your\sample.dwg"


def report(name, fn, *args):
    print("--- {} ---".format(name))
    try:
        result = fn(*args)
        print("PASS: {}".format(name))
        return True, result
    except Exception:
        print("FAIL: {}".format(name))
        print(traceback.format_exc())
        return False, None


def main():
    ok, doc = report(
        "create_doc_from_template", b.create_doc_from_template, app, TEST_TEMPLATE_PATH
    )
    if not ok:
        return

    ok, _ = report(
        "import_or_link_dwg", b.import_or_link_dwg, doc, TEST_DWG_PATH, b.IMPORT_MODE
    )
    if not ok:
        doc.Close(False)
        return

    print("Done - doc left open for inspection, close it manually when finished.")


main()
