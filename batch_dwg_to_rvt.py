# -*- coding: utf-8 -*-
"""
Batch DWG -> RVT stand conversion.

For each DWG in DWG_FOLDER: new doc from TEMPLATE_PATH -> import/link the DWG
-> save to OUTPUT_FOLDER, close.

Runs as a Dynamo Python node, or standalone via pyRevit/RevitPythonShell.

DocumentManager.CurrentDBDocument (Dynamo's bound doc) is read exactly once,
for `app` below - never again. It won't follow into the docs this script
creates.
"""

import os
import traceback

from Autodesk.Revit.DB import (
    Transaction,
    SaveAsOptions,
    DWGImportOptions,
    ImportPlacement,
    FilteredElementCollector,
    ViewPlan,
)

try:
    import clr
    clr.AddReference("RevitServices")
    from RevitServices.Persistence import DocumentManager
    app = DocumentManager.Instance.CurrentDBDocument.Application
except ImportError:
    app = __revit__.Application  # pyRevit / RevitPythonShell


# --- config: edit before running --------------------------------------------
TEMPLATE_PATH = r"C:\Path\To\Your\StandardTemplate.rte"
DWG_FOLDER = r"C:\Path\To\Your\DWGs"
OUTPUT_FOLDER = r"C:\Path\To\Your\Output"
IMPORT_MODE = "link"  # "import" | "link"


def get_dwg_files(folder):
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".dwg")]


def create_doc_from_template(app, template_path):
    return app.NewProjectDocument(template_path)


def import_or_link_dwg(doc, dwg_path, mode):
    """Import or link dwg_path into doc. Returns the resulting ElementId."""
    options = DWGImportOptions()
    options.Placement = ImportPlacement.Origin

    # NewProjectDocument has no ActiveView (only UI-opened docs do) - use any
    # non-template plan view from the template instead.
    view = next((v for v in FilteredElementCollector(doc).OfClass(ViewPlan) if not v.IsTemplate), None)
    if view is None:
        raise RuntimeError("Template has no usable plan view")

    t = Transaction(doc, "Import/Link DWG")
    t.Start()
    try:
        if mode == "import":
            success, new_id = doc.Import(dwg_path, options, view)
            if not success:
                raise RuntimeError("Document.Import failed for {}".format(dwg_path))
        elif mode == "link":
            new_id = doc.Link(dwg_path, options, view)
        else:
            raise ValueError("IMPORT_MODE must be 'import' or 'link'")
        t.Commit()
        return new_id
    except Exception:
        t.RollBack()
        raise


def process_single_dwg(app, dwg_path, output_folder):
    """One DWG -> one RVT. Returns (success, message)."""
    doc = None
    try:
        doc = create_doc_from_template(app, TEMPLATE_PATH)
        import_or_link_dwg(doc, dwg_path, IMPORT_MODE)

        out_path = os.path.join(output_folder, os.path.splitext(os.path.basename(dwg_path))[0] + ".rvt")
        save_options = SaveAsOptions()
        save_options.OverwriteExistingFile = True
        doc.SaveAs(out_path, save_options)
        doc.Close(False)
        return True, "OK: {}".format(out_path)

    except Exception:
        if doc is not None:
            try:
                doc.Close(False)  # discard, don't save a half-built file
            except Exception:
                pass
        return False, "FAILED: {} - {}".format(os.path.basename(dwg_path), traceback.format_exc())


def main():
    results = []
    for dwg_path in get_dwg_files(DWG_FOLDER):
        success, message = process_single_dwg(app, dwg_path, OUTPUT_FOLDER)
        results.append(message)
        print(message)
    return results


# In Dynamo, the last expression becomes the node's OUT value. Guarded so the
# file stays importable (tests, pyrevit_smoke_test.py) without auto-running.
if __name__ == "__main__":
    OUT = main()
