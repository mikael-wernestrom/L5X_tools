from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .loader import is_list_file, load_list_file


def generate(config_path: Path) -> None:
    base = config_path.parent.resolve()

    with open(config_path, encoding="utf-8") as f:
        entries = yaml.safe_load(f)

    for entry in entries:
        entry = dict(entry)
        input_file = (base / entry.pop("input_file")).resolve()
        output_file = (base / entry.pop("output_file")).resolve()

        context = {}
        for key, value in entry.items():
            if is_list_file(value):
                file_path = Path(value)
                if not file_path.is_absolute():
                    file_path = (base / value).resolve()
                context[key] = load_list_file(file_path)
            else:
                context[key] = value

        env = Environment(
            loader=FileSystemLoader(str(input_file.parent)),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            autoescape=False,       # L5X is not HTML; template author controls XML structure
            trim_blocks=True,       # remove newline after {% %} tags to avoid blank lines
            lstrip_blocks=True,     # strip leading whitespace before {% %} tags
        )
        template = env.get_template(input_file.name)
        rendered = template.render(**context)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(rendered, encoding="utf-8")
        print(f"  {output_file}")
