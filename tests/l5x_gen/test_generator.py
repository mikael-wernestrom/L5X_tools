import pytest
import yaml
from pathlib import Path

from tools.l5x_gen.generator import generate


@pytest.fixture
def template_dir(tmp_path):
    d = tmp_path / "input"
    d.mkdir()
    return d


def make_config(tmp_path, entries):
    config = tmp_path / "config.yaml"
    config.write_text(yaml.dump(entries), encoding="utf-8")
    return config


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
