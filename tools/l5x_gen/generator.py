from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined


def generate(config_path: Path) -> None:
    with open(config_path, encoding="utf-8") as f:
        entries = yaml.safe_load(f)

    for entry in entries:
        entry = dict(entry)
        input_file = Path(entry.pop("input_file"))
        output_file = Path(entry.pop("output_file"))

        env = Environment(
            loader=FileSystemLoader(str(input_file.parent)),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )
        template = env.get_template(input_file.name)
        rendered = template.render(**entry)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(rendered, encoding="utf-8")
        print(f"  {output_file}")
