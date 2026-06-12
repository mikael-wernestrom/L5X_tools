import csv
import pytest
import yaml
from pathlib import Path

from tools.l5x_gen.generator import generate
from tools.l5x_gen.loader import is_list_file, load_list_file


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


# --- existing tests ---

def test_basic_variable_substitution(tmp_path, template_dir):
    (template_dir / "Tank_Pxx.L5X").write_text(
        "<Controller Name='{{ tag_prefix }}'/>", encoding="utf-8"
    )
    config = make_config(tmp_path, [{
        "input_file": str(template_dir / "Tank_Pxx.L5X"),
        "output_file": str(tmp_path / "output" / "Tank_P04.L5X"),
        "tag_prefix": "P04",
    }])

    generate(config)

    result = (tmp_path / "output" / "Tank_P04.L5X").read_text(encoding="utf-8")
    assert result == "<Controller Name='P04'/>"


def test_multiple_entries(tmp_path, template_dir):
    (template_dir / "Tank_Pxx.L5X").write_text(
        "{{ tag_prefix }}", encoding="utf-8"
    )
    config = make_config(tmp_path, [
        {
            "input_file": str(template_dir / "Tank_Pxx.L5X"),
            "output_file": str(tmp_path / "output" / "Tank_P04.L5X"),
            "tag_prefix": "P04",
        },
        {
            "input_file": str(template_dir / "Tank_Pxx.L5X"),
            "output_file": str(tmp_path / "output" / "Tank_P05.L5X"),
            "tag_prefix": "P05",
        },
    ])

    generate(config)

    assert (tmp_path / "output" / "Tank_P04.L5X").read_text(encoding="utf-8") == "P04"
    assert (tmp_path / "output" / "Tank_P05.L5X").read_text(encoding="utf-8") == "P05"


def test_boolean_variable(tmp_path, template_dir):
    (template_dir / "Tank_Pxx.L5X").write_text(
        "{% if has_agitator %}HAS_AGITATOR{% else %}NO_AGITATOR{% endif %}",
        encoding="utf-8",
    )
    config = make_config(tmp_path, [{
        "input_file": str(template_dir / "Tank_Pxx.L5X"),
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


# --- list file tests ---

def test_is_list_file_detects_extensions():
    assert is_list_file("valves.csv")
    assert is_list_file("motors.xlsx")
    assert is_list_file("data.xls")
    assert is_list_file(r"list_data\valves.csv")
    assert not is_list_file("P04")
    assert not is_list_file("true")
    assert not is_list_file(True)
    assert not is_list_file(42)


def test_load_csv(tmp_path):
    csv_file = tmp_path / "valves.csv"
    write_csv(csv_file, [
        {"tag": "FV_101", "description": "Feed Valve"},
        {"tag": "DV_101", "description": "Drain Valve"},
    ])

    result = load_list_file(csv_file)

    assert result == [
        {"tag": "FV_101", "description": "Feed Valve"},
        {"tag": "DV_101", "description": "Drain Valve"},
    ]


def test_csv_injected_as_list_into_template(tmp_path, template_dir):
    csv_file = tmp_path / "list_data" / "valves.csv"
    write_csv(csv_file, [
        {"tag": "FV_101", "description": "Feed Valve"},
        {"tag": "DV_101", "description": "Drain Valve"},
    ])
    (template_dir / "t.L5X").write_text(
        "{% for v in valves %}{{ v.tag }}\n{% endfor %}", encoding="utf-8"
    )
    config = make_config(tmp_path, [{
        "input_file": str(template_dir / "t.L5X"),
        "output_file": str(tmp_path / "out.L5X"),
        "valves": str(csv_file),
    }])

    generate(config)

    assert (tmp_path / "out.L5X").read_text(encoding="utf-8") == "FV_101\nDV_101\n"


def test_relative_csv_path_resolves_from_config(tmp_path, template_dir):
    csv_file = tmp_path / "list_data" / "valves.csv"
    write_csv(csv_file, [{"tag": "FV_101", "description": "Feed Valve"}])
    (template_dir / "t.L5X").write_text("{{ valves[0].tag }}", encoding="utf-8")

    config = tmp_path / "config.yaml"
    config.write_text(yaml.dump([{
        "input_file": str(template_dir / "t.L5X"),
        "output_file": str(tmp_path / "out.L5X"),
        "valves": "list_data/valves.csv",
    }]), encoding="utf-8")

    generate(config)

    assert (tmp_path / "out.L5X").read_text(encoding="utf-8") == "FV_101"


def test_optional_list_file_absent_when_not_defined(tmp_path, template_dir):
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


def test_xlsx_loaded_as_list(tmp_path):
    pytest.importorskip("openpyxl")
    import openpyxl
    xlsx_file = tmp_path / "motors.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["tag", "description", "kw"])
    ws.append(["AGT_101", "Agitator Motor", 7.5])
    wb.save(xlsx_file)

    result = load_list_file(xlsx_file)

    assert result == [{"tag": "AGT_101", "description": "Agitator Motor", "kw": 7.5}]
