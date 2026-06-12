from pathlib import Path

LIST_EXTENSIONS = {".csv", ".xls", ".xlsx"}


def is_list_query(value: object) -> bool:
    if not isinstance(value, str):
        return False
    first_segment = value.split("|")[0].strip()
    return Path(first_segment).suffix.lower() in LIST_EXTENSIONS


def load_list_query(value: str, base: Path) -> list[dict]:
    segments = [s.strip() for s in value.split("|")]
    file_str = segments[0]
    ops = segments[1:]

    file_path = Path(file_str)
    if not file_path.is_absolute():
        file_path = (base / file_str).resolve()

    df = _load_file(file_path)
    df = _apply_operations(df, ops)
    return df.to_dict("records")


def _load_file(path: Path):
    import pandas as pd

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def _apply_operations(df, ops: list[str]):
    import pandas as pd

    for op in ops:
        if op == "distinct":
            df = df.drop_duplicates()
        elif op.startswith("select:"):
            cols = [c.strip() for c in op[7:].split(",")]
            df = df[cols]
        elif op.startswith("sort:"):
            cols = [c.strip() for c in op[5:].split(",")]
            df = df.sort_values(cols).reset_index(drop=True)
        elif op.startswith("where:"):
            expr = op[6:].strip()
            col, val = expr.split("=", 1)
            col, val = col.strip(), val.strip()
            col_series = df[col]
            if pd.api.types.is_bool_dtype(col_series):
                typed_val = val.lower() in ("true", "1", "yes")
            elif pd.api.types.is_numeric_dtype(col_series):
                try:
                    typed_val = col_series.dtype.type(val)
                except (ValueError, TypeError):
                    typed_val = val
            else:
                typed_val = val
            df = df[col_series == typed_val]
        else:
            raise ValueError(f"Unknown query operation: '{op}'")
    return df
