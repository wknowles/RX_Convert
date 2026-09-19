# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single Revit/Dynamo automation script (`batch_dwg_to_rvt.py`) that batch-converts a folder of exhibit-floorplan DWG files into individual RVT project files. Currently it only imports/links each DWG into a template-based document and saves it; the stand extraction, wall and room steps were removed and are not yet re-added.

There is no build system or package manifest — this is not a standalone-runnable Python project. Most of the logic only executes inside the Revit API environment (see below); a small pure-Python slice is unit-tested locally.

## Code style

The user needs to read this script quickly and be confident each line actually works — this is Revit API code, hard to test, so clarity and correctness matter more than cleverness or completeness:

- Simple, terse, minimal code. No abstractions, no defensive handling for cases that can't happen.
- One-line docstrings only where the name/signature doesn't already say it (e.g. a return shape). Skip them otherwise.
- No dead code, no unused imports, no commented-out alternatives.
- Every line should be something the user can look at and verify is correct, not something that "should probably work."

## Running / testing

Two separate tracks, since only part of the script is Revit-API-dependent:

- **Pure logic** (currently just `get_dwg_files`): unit-tested with pytest, no Revit needed. Run with `python3 -m pytest tests/`. `tests/conftest.py` stubs `Autodesk.Revit.DB`, `clr`, and `RevitServices` in `sys.modules` so the module can be imported outside Revit; the rest of the module's functions touch real Revit API objects and aren't exercised by these tests.
- **Revit-API logic** (everything else): can only run inside a live Revit process. Use `pyrevit_smoke_test.py` — run it as a pyRevit button or paste it into pyRevit's Python console (after editing `TEST_TEMPLATE_PATH` / `TEST_DWG_PATH` at the top). It runs the pipeline stage-by-stage against a single sample DWG and prints a PASS/FAIL report per stage, instead of requiring the full batch loop against all 60 files. It leaves the resulting document open for inspection rather than saving/closing it.

Periodically also run the real script through Dynamo against a throwaway 2-3 file test folder — the pyRevit harness checks each pipeline stage in isolation but doesn't exercise the batch loop's per-document transaction/save/close handling.

Check which engine the Dynamo Python node is set to (IronPython2 vs CPython3) — the `import clr` / `clr.AddReference("RevitServices")` lines at the top of the file are needed for IronPython2 and are harmless no-ops if already unnecessary under CPython3.

## Architecture

The script runs as the body of a single Dynamo Python node (`OUT = main()` at the bottom is the Dynamo node's output convention — keep it as the last line). It's guarded behind `if __name__ == "__main__":` so the file stays importable (by pytest, `pyrevit_smoke_test.py`, etc.) without immediately running the batch loop — this doesn't change Dynamo/pyRevit behavior, since both execute node/script code with `__name__ == "__main__"`.

`app` (the Revit `Application` object) is grabbed once at module load, via Dynamo's `RevitServices.DocumentManager` if available, falling back to pyRevit's `__revit__.Application` (injected as a builtin) if not — this is what makes the module loadable under both hosts. Key constraint driving the rest of the structure: `DocumentManager.Instance.CurrentDBDocument` (Dynamo's bound document) is only used **once**, for this. Every subsequent operation works against explicit `doc` references returned by `NewProjectDocument` / `OpenDocumentFile` — the code must never call `CurrentDBDocument` again after that point, since it won't follow into the newly created documents.

Per-DWG pipeline (`process_single_dwg`), run once for every file in `DWG_FOLDER`:
1. `create_doc_from_template` — new unsaved `Document` from `TEMPLATE_PATH`
2. `import_or_link_dwg` — imports or links the DWG per `IMPORT_MODE` (`"import"` embeds geometry, `"link"` keeps it as a live external reference); wrapped in its own `Transaction`. Resolves a real `View` via `FilteredElementCollector(doc).OfClass(ViewPlan)` rather than `doc.ActiveView` — `Document.ActiveView` throws for documents that were never opened in the Revit UI, which is every document `NewProjectDocument` creates here. Also checks the `success` bool `Document.Import` returns and raises if it's `False`, instead of silently proceeding as if the import worked.
3. Save the document to `OUTPUT_FOLDER/<dwg_basename>.rvt` and close; on any failure, close without saving (avoids leaving half-built files)

Wall/room creation from stand outlines is the intended next stage, to be filled in with existing per-file logic the user already has working elsewhere — the point of this script is to wrap that logic in a loop with correct per-document transaction/save/close handling.

Config constants (`TEMPLATE_PATH`, `DWG_FOLDER`, `OUTPUT_FOLDER`, `IMPORT_MODE`) live at the top of the file and are meant to be edited directly before each run rather than passed as arguments.
