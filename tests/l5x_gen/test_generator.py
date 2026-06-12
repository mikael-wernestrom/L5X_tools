import csv
import pytest
import yaml
from pathlib import Path

from tools.l5x_gen.generator import generate
from tools.l5x_gen.loader import is_list_query, load_list_query


@pytest.fixture
def template_dir(tmp_path):
    d = tmp_path / "input"
    d.mkdir()
    return d


def make_config(tmp_path, entries):
    config = tmp_path / "config.yaml"
    config.write_text(yaml.dump(entries), encoding="utf-8")
    return config


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


# --- generator tests ---

def test_basic_variable_substitution(tmp_path, template_dir):
    (template_dir / "t.L5X").write_text(
        "<Controller Name='{{ tag_prefix }}'/>", encoding="utf-8"
    )
    config = make_config(tmp_path, [{
        "input_file": str(template_dir / "t.L5X"),
        "output_file": str(tmp_path / "output" / "out.L5X"),
        "tag_prefix": "P04",
    }])

    generate(config)

    result = (tmp_path / "output" / "out.L5X").read_text(encoding="utf-8")
    assert result == "<Controller Name='P04'/>"


def test_multiple_entries(tmp_path, template_dir):
    (template_dir / "t.L5X").write_text("{{ tag_prefix }}", encoding="utf-8")
    config = make_config(tmp_path, [
        {
            "input_file": str(template_dir / "t.L5X"),
            "output_file": str(tmp_path / "output" / "P04.L5X"),
            "tag_prefix": "P04",
        },
        {
            "input_file": str(template_dir / "t.L5X"),
            "output_file": str(tmp_path / "output" / "P05.L5X"),
            "tag_prefix": "P05",
        },
    ])

    generate(config)

    assert (tmp_path / "output" / "P04.L5X").read_text(encoding="utf-8") == "P04"
    assert (tmp_path / "output" / "P05.L5X").read_text(encoding="utf-8") == "P05"


def test_boolean_variable(tmp_path, template_dir):
    (template_dir / "t.L5X").write_text(
        "{% if has_agitator %}HAS_AGITATOR{% else %}NO_AGITATOR{% endif %}",
        encoding="utf-8",
    )
    config = make_config(tmp_path, [{
        "input_file": str(template_dir / "t.L5X"),
        "output_file": str(tmp_path / "out.L5X"),
        "has_agitator": True,
    }])

    generate(config)

    assert (tmp_path / "out.L5X").read_text(encoding="utf-8") == "HAS_AGITATOR"


def test_output_directory_created(tmp_path, template_dir):
    (template_dir / "t.L5X").write_text("x", encoding="utf-8")
    out = tmp_path / "deep" / "nested" / "dir" / "out.L5X"
    config = make_config(tmp_path, [{
        "input_file": str(template_dir / "t.L5X"),
        "output_file": str(out),
    }])

    generate(config)

    assert out.exists()


def test_undefined_variable_raises(tmp_path, template_dir):
    (template_dir / "t.L5X").write_text("{{ missing_var }}", encoding="utf-8")
    config = make_config(tmp_path, [{
        "input_file": str(template_dir / "t.L5X"),
        "output_file": str(tmp_path / "out.L5X"),
    }])

    with pytest.raises(Exception):
        generate(config)


# --- is_list_query detection ---

def test_is_list_query_detects_plain_paths():
    assert is_list_query("valves.csv")
    assert is_list_query("motors.xlsx")
    assert is_list_query("data.xls")
    assert is_list_query(r"list_data\valves.csv")


def test_is_list_query_detects_pipe_expressions():
    assert is_list_query("list_data/valves.csv | select: tag, descr | distinct")
    assert is_list_query("data.xlsx | where: type=inlet | sort: tag")


def test_is_list_query_ignores_non_file_values():
    assert not is_list_query("P04")
    assert not is_list_query("true")
    assert not is_list_query(True)
    assert not is_list_query(42)
    assert not is_list_query(None)


# --- load_list_query operations ---

VALVE_ROWS = [
    {"valve_tag": "FV_101", "valve_descr": "Feed Valve 1", "routine_name": "Fill",   "valve_type": "inlet",  "udt_type": "VALVE_STD"},
    {"valve_tag": "FV_102", "valve_descr": "Feed Valve 2", "routine_name": "Fill",   "valve_type": "inlet",  "udt_type": "VALVE_STD"},
    {"valve_tag": "DV_101", "valve_descr": "Drain Valve",  "routine_name": "Drain",  "valve_type": "outlet", "udt_type": "VALVE_STD"},
    {"valve_tag": "SV_101", "valve_descr": "Sample Valve", "routine_name": "Sample", "valve_type": "outlet", "udt_type": "VALVE_SAMPLE"},
]


@pytest.fixture
def valves_csv(tmp_path):
    path = tmp_path / "list_data" / "valves.csv"
    write_csv(path, VALVE_ROWS)
    return path


def test_load_no_ops(tmp_path, valves_csv):
    result = load_list_query(str(valves_csv), tmp_path)
    assert len(result) == 4
    assert result[0]["valve_tag"] == "FV_101"


def test_select(tmp_path, valves_csv):
    result = load_list_query(f"{valves_csv} | select: valve_tag, valve_descr", tmp_path)
    assert list(result[0].keys()) == ["valve_tag", "valve_descr"]


def test_distinct(tmp_path, valves_csv):
    result = load_list_query(
        f"{valves_csv} | select: routine_name, udt_type | distinct", tmp_path
    )
    routine_names = [r["routine_name"] for r in result]
    assert sorted(routine_names) == ["Drain", "Fill", "Sample"]


def test_sort(tmp_path, valves_csv):
    result = load_list_query(f"{valves_csv} | sort: valve_tag", tmp_path)
    tags = [r["valve_tag"] for r in result]
    assert tags == sorted(tags)


def test_where(tmp_path, valves_csv):
    result = load_list_query(
        f"{valves_csv} | where: valve_type=inlet", tmp_path
    )
    assert all(r["valve_type"] == "inlet" for r in result)
    assert len(result) == 2


def test_chained_operations(tmp_path, valves_csv):
    result = load_list_query(
        f"{valves_csv} | select: valve_tag, valve_descr, routine_name | distinct | sort: routine_name",
        tmp_path,
    )
    routine_names = [r["routine_name"] for r in result]
    assert routine_names == sorted(routine_names)
    assert list(result[0].keys()) == ["valve_tag", "valve_descr", "routine_name"]


def test_relative_path_resolves_from_config(tmp_path, template_dir, valves_csv):
    (template_dir / "t.L5X").write_text("{{ valves | length }}", encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.write_text(yaml.dump([{
        "input_file": str(template_dir / "t.L5X"),
        "output_file": str(tmp_path / "out.L5X"),
        "valves": "list_data/valves.csv",
    }]), encoding="utf-8")

    generate(config)

    assert (tmp_path / "out.L5X").read_text(encoding="utf-8") == "4"


def test_optional_list_absent_when_not_defined(tmp_path, template_dir):
    (template_dir / "t.L5X").write_text(
        "{% if motors is defined %}HAS_MOTORS{% else %}NO_MOTORS{% endif %}",
        encoding="utf-8",
    )
    config = make_config(tmp_path, [{
        "input_file": str(template_dir / "t.L5X"),
        "output_file": str(tmp_path / "out.L5X"),
    }])

    generate(config)

    assert (tmp_path / "out.L5X").read_text(encoding="utf-8") == "NO_MOTORS"


def test_numeric_types_preserved(tmp_path):
    csv_file = tmp_path / "motors.csv"
    write_csv(csv_file, [{"tag": "AGT_101", "kw": "7.5", "poles": "4"}])

    result = load_list_query(str(csv_file), tmp_path)

    assert isinstance(result[0]["kw"], float)
    assert isinstance(result[0]["poles"], int)


def test_where_on_numeric_column(tmp_path):
    csv_file = tmp_path / "motors.csv"
    write_csv(csv_file, [
        {"tag": "AGT_101", "kw": "7.5"},
        {"tag": "AGT_102", "kw": "11.0"},
    ])

    result = load_list_query(f"{csv_file} | where: kw=7.5", tmp_path)

    assert len(result) == 1
    assert result[0]["tag"] == "AGT_101"


def test_unknown_operation_raises(tmp_path, valves_csv):
    with pytest.raises(ValueError, match="Unknown query operation"):
        load_list_query(f"{valves_csv} | frobnicate: foo", tmp_path)


def test_xlsx_loaded_as_list(tmp_path):
    pytest.importorskip("openpyxl")
    import openpyxl
    xlsx_file = tmp_path / "motors.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["tag", "description", "kw"])
    ws.append(["AGT_101", "Agitator Motor", 7.5])
    wb.save(xlsx_file)

    result = load_list_query(str(xlsx_file), tmp_path)

    assert result == [{"tag": "AGT_101", "description": "Agitator Motor", "kw": 7.5}]
