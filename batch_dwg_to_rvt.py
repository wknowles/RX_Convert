# -*- coding: utf-8 -*-
"""
Batch DWG -> RVT stand conversion.

For each DWG in DWG_FOLDER: new doc from TEMPLATE_PATH -> import/link the DWG
-> create walls + rooms from stand outlines [stubs below] -> save to
OUTPUT_FOLDER, close.

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
STAND_OUTLINE_LAYER = "Expo_Stand_Outline"
STAND_ID_LAYER = "Expo_Stand_ID"


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


def extract_stand_geometry(doc, cad_element_id, outline_layer, id_layer):
    """STUB: return [{"boundary_curves": [Curve, ...], "centroid": XYZ, "stand_id_text": str|None}, ...]."""
    raise NotImplementedError


def create_walls_for_stand(doc, boundary_curves, wall_type_id, level_id):
    """STUB: Wall.Create(doc, curve, wall_type_id, level_id, ...) per boundary curve. Call inside an open Transaction."""
    raise NotImplementedError


def place_rooms_in_enclosed_areas(doc, level, stands):
    """Put a Room in every wall-enclosed area on level (like Room > Place Rooms
    Automatically), then name each from the nearest stand's stand_id_text.
    Call inside an open Transaction.
    """
    rooms = [doc.Create.NewRoom(level, circuit) for circuit in doc.get_PlanTopology(level).Circuits]

    for room in rooms:
        point = room.Location.Point
        nearest = min(stands, key=lambda s: point.DistanceTo(s["centroid"])) if stands else None
        if nearest and nearest["stand_id_text"]:
            room.Name = nearest["stand_id_text"]

    return rooms


def process_single_dwg(app, dwg_path, output_folder):
    """One DWG -> one RVT. Returns (success, message)."""
    doc = None
    try:
        doc = create_doc_from_template(app, TEMPLATE_PATH)
        cad_id = import_or_link_dwg(doc, dwg_path, IMPORT_MODE)

        wall_type_id = None   # TODO: resolve from template
        level_id = None       # TODO: resolve from template
        level = None          # TODO: resolve from template

        stands = extract_stand_geometry(doc, cad_id, STAND_OUTLINE_LAYER, STAND_ID_LAYER)

        t = Transaction(doc, "Create walls and rooms")
        t.Start()
        try:
            for stand in stands:
                create_walls_for_stand(doc, stand["boundary_curves"], wall_type_id, level_id)
            place_rooms_in_enclosed_areas(doc, level, stands)
            t.Commit()
        except Exception:
            t.RollBack()
            raise

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
