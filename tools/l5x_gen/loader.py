import csv
from pathlib import Path

LIST_EXTENSIONS = {".csv", ".xls", ".xlsx"}


def is_list_file(value: object) -> bool:
    return isinstance(value, str) and Path(value).suffix.lower() in LIST_EXTENSIONS


def load_list_file(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _load_csv(path)
    if suffix == ".xlsx":
        return _load_xlsx(path)
    if suffix == ".xls":
        return _load_xls(path)
    raise ValueError(f"Unsupported list file type: {suffix}")


def _load_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _load_xlsx(path: Path) -> list[dict]:
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        return []
    headers = [str(h) for h in rows[0]]
    return [dict(zip(headers, row)) for row in rows[1:]]


def _load_xls(path: Path) -> list[dict]:
    import xlrd
    wb = xlrd.open_workbook(str(path))
    ws = wb.sheet_by_index(0)
    if ws.nrows == 0:
        return []
    headers = [str(ws.cell_value(0, c)) for c in range(ws.ncols)]
    return [
        dict(zip(headers, [ws.cell_value(r, c) for c in range(ws.ncols)]))
        for r in range(1, ws.nrows)
    ]
