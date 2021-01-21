from jinja2 import Template


def render_jinja_file(template_path: str, output_path: str, data: dict):
    with open(template_path, "r") as t:
        template_text = t.read()

    template = Template(template_text)
    rendered = template.render(**data)

    with open(output_path, "w") as out_t:
        out_t.write(rendered)
