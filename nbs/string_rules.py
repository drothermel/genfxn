import marimo

__generated_with = "0.20.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import random

    from genfxn.ops.simple_str_transform_op import SimpleStrTransformOp
    from genfxn.spaces.simple_str_transform_space import SimpleStrTransformSpace

    return SimpleStrTransformOp, SimpleStrTransformSpace, mo, random


@app.cell
def _(mo):
    is_script_mode = mo.app_meta().mode == "script"
    mode_label = "script" if is_script_mode else "interactive"
    return


@app.cell(hide_code=True)
def _(mo):
    input_text = mo.ui.text(
        value="  AbC\tdeF 123  ",
        label="**Input String**",
        full_width=True,
    )
    input_text
    return (input_text,)


@app.cell(hide_code=True)
def _(SimpleStrTransformOp, SimpleStrTransformSpace, input_text, mo):
    rows: list[dict[str, str]] = []
    for _transform in SimpleStrTransformSpace().values:
        _op = SimpleStrTransformOp(transform=_transform)
        rows.append(
            {
                "transform": _transform,
                "output_repr": repr(_op.eval(input_text.value)),
                "python_expr": _op.render_python("s"),
            }
        )
    header = (
        "| transform | output (`repr`) | python expression |\n|---|---|---|\n"
    )
    body = "".join(
        f"| `{_row['transform']}` | `{_row['output_repr']}` | "
        f"`{_row['python_expr']}` |\n"
        for _row in rows
    )
    mo.md("## Transform Outputs\n\n" + header + body)
    return


@app.cell(hide_code=True)
def _(SimpleStrTransformOp, random):
    sampler_op = SimpleStrTransformOp(transform="lowercase")
    sampled_inputs = sampler_op.input_space.sample(
        n_samples=20,
        rng=random.Random(7),
    )
    sampled_inputs
    return


if __name__ == "__main__":
    app.run()
