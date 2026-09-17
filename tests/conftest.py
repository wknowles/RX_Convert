# -*- coding: utf-8 -*-
"""
Stubs out the Revit/Dynamo-only imports (Autodesk.Revit.DB, clr,
RevitServices) so batch_dwg_to_rvt.py can be imported by plain CPython/pytest
on a machine with no Revit installed. Only the pure-Python logic (functions
that don't touch real Revit API objects) is actually exercised by the tests -
these stubs just need to exist, not behave correctly.
"""

import os
import sys
import types
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _install_revit_mocks():
    revit_db = types.ModuleType("Autodesk.Revit.DB")
    for name in [
        "Transaction",
        "SaveAsOptions",
        "DWGImportOptions",
        "ImportPlacement",
        "FilteredElementCollector",
        "ViewPlan",
    ]:
        setattr(revit_db, name, MagicMock(name=name))

    autodesk = types.ModuleType("Autodesk")
    revit = types.ModuleType("Autodesk.Revit")
    autodesk.Revit = revit
    revit.DB = revit_db

    sys.modules.setdefault("Autodesk", autodesk)
    sys.modules.setdefault("Autodesk.Revit", revit)
    sys.modules.setdefault("Autodesk.Revit.DB", revit_db)

    clr = types.ModuleType("clr")
    clr.AddReference = MagicMock()
    sys.modules.setdefault("clr", clr)

    revit_services = types.ModuleType("RevitServices")
    persistence = types.ModuleType("RevitServices.Persistence")
    persistence.DocumentManager = MagicMock()
    revit_services.Persistence = persistence
    sys.modules.setdefault("RevitServices", revit_services)
    sys.modules.setdefault("RevitServices.Persistence", persistence)


_install_revit_mocks()
