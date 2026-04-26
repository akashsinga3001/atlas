"""Interactive terminal launcher for run_*.py scripts.

This launcher auto-discovers script runners in the scripts folder and
extracts argparse options from each script so new scripts are picked up
without changing this file.
"""

import argparse
import ast
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / 'scripts'


@dataclass
class ArgSpec:
    """Structured argparse option extracted from a script."""

    flag: str
    dest: str
    help_text: str
    default: Any
    required: bool
    choices: list[str]
    action: str | None
    type_name: str | None


@dataclass
class ScriptSpec:
    """Structured metadata for a runnable script."""

    name: str
    path: Path
    description: str
    arguments: list[ArgSpec]


@dataclass
class DiscoveryWarning:
    """Warning captured during script metadata discovery."""

    file_name: str
    message: str


class _ArgparseVisitor(ast.NodeVisitor):
    """Collect parser.add_argument calls in source order."""

    def __init__(self) -> None:
        self.arguments: list[ArgSpec] = []

    def visit_Call(self, node: ast.Call) -> Any:
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'add_argument':
            spec = _parse_add_argument_call(node)
            if spec:
                self.arguments.append(spec)
        self.generic_visit(node)


def _safe_literal(node: ast.AST | None) -> Any:
    """Safely read constant/list/tuple literals from AST nodes."""
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return None


def _extract_type_name(node: ast.AST | None) -> str | None:
    """Return readable callable name passed to argparse type=."""
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _parse_add_argument_call(call: ast.Call) -> ArgSpec | None:
    """Convert one parser.add_argument(...) call into ArgSpec."""
    option_strings: list[str] = []
    for arg in call.args:
        value = _safe_literal(arg)
        if isinstance(value, str) and value.startswith('-'):
            option_strings.append(value)

    long_flags = [flag for flag in option_strings if flag.startswith('--')]
    if not long_flags:
        return None

    preferred_flag = long_flags[0]

    kwargs: dict[str, Any] = {}
    for keyword in call.keywords:
        if keyword.arg is None:
            continue
        if keyword.arg == 'type':
            kwargs[keyword.arg] = _extract_type_name(keyword.value)
        else:
            kwargs[keyword.arg] = _safe_literal(keyword.value)

    dest = kwargs.get('dest')
    if not isinstance(dest, str):
        dest = preferred_flag[2:].replace('-', '_')

    choices_value = kwargs.get('choices')
    if isinstance(choices_value, (list, tuple, set)):
        choices = [str(item) for item in choices_value]
    else:
        choices = []

    help_text = kwargs.get('help')
    if not isinstance(help_text, str):
        help_text = ''

    default = kwargs.get('default')
    required = bool(kwargs.get('required', False))
    action = kwargs.get('action') if isinstance(kwargs.get('action'), str) else None
    type_name = kwargs.get('type') if isinstance(kwargs.get('type'), str) else None

    return ArgSpec(
        flag=preferred_flag,
        dest=dest,
        help_text=help_text,
        default=default,
        required=required,
        choices=choices,
        action=action,
        type_name=type_name,
    )


def _script_description(path: Path, tree: ast.Module) -> str:
    """Pick the script description from module docstring."""
    doc = ast.get_docstring(tree) or ''
    if doc.strip():
        return doc.strip().splitlines()[0]
    return f'Run {path.stem}'


def _human_name(path: Path) -> str:
    """Readable menu name from run_<name>.py."""
    base = path.stem
    if base.startswith('run_'):
        base = base[4:]
    return base.replace('_', ' ').title()


def _discover_scripts() -> tuple[list[ScriptSpec], list[DiscoveryWarning]]:
    """Auto-discover run_*.py scripts and parse their CLI flags."""
    specs: list[ScriptSpec] = []
    warnings: list[DiscoveryWarning] = []
    current_name = Path(__file__).name

    for path in sorted(SCRIPTS_DIR.glob('run_*.py')):
        if path.name == current_name:
            continue

        try:
            source = path.read_text(encoding='utf-8')
            tree = ast.parse(source)
            visitor = _ArgparseVisitor()
            visitor.visit(tree)

            specs.append(
                ScriptSpec(
                    name=_human_name(path),
                    path=path,
                    description=_script_description(path, tree),
                    arguments=visitor.arguments,
                )
            )
        except (OSError, SyntaxError, UnicodeDecodeError, ValueError) as error:
            warnings.append(DiscoveryWarning(file_name=path.name, message=str(error)))

    return specs, warnings


def _print_discovery_warnings(console: Console, warnings: list[DiscoveryWarning]) -> None:
    """Display non-fatal warnings from script discovery."""
    if not warnings:
        return

    console.print('[yellow]Some scripts were skipped during discovery:[/yellow]')
    for warning in warnings:
        console.print(f'- {warning.file_name}: {warning.message}')
    console.print('')


def _validate_known_type(value: str, type_name: str | None) -> str:
    """Validate value for known custom argparse validators."""
    if type_name == 'positive_int':
        parsed = int(value)
        if parsed < 1:
            raise ValueError('Value must be >= 1')
    return value


def _render_scripts_table(console: Console, scripts: list[ScriptSpec]) -> None:
    """Display discovered scripts in an indexed table."""
    table = Table(title='Available Script Runners')
    table.add_column('#', justify='right')
    table.add_column('Name')
    table.add_column('File')
    table.add_column('Description')

    for idx, script in enumerate(scripts, start=1):
        table.add_row(str(idx), script.name, script.path.name, script.description)

    console.print(table)


def _prompt_argument(console: Console, arg: ArgSpec) -> list[str]:
    """Prompt for one argument and return CLI tokens to append."""
    label = arg.flag
    if arg.help_text:
        console.print(f'[cyan]{label}[/cyan] - {arg.help_text}')
    else:
        console.print(f'[cyan]{label}[/cyan]')

    if arg.action in {'store_true', 'store_false'}:
        default_enabled = bool(arg.default)
        selected = Confirm.ask('Enable this option?', default=default_enabled)
        should_include = selected if arg.action == 'store_true' else not selected
        return [arg.flag] if should_include else []

    if arg.choices:
        choice_default = str(arg.default) if arg.default is not None else arg.choices[0]
        chosen = Prompt.ask('Choose value', choices=arg.choices, default=choice_default)
        return [arg.flag, chosen]

    default_text = str(arg.default) if arg.default is not None else None

    if arg.type_name == 'int':
        if arg.default is None:
            value = IntPrompt.ask('Enter integer value')
            return [arg.flag, str(value)]
        value = IntPrompt.ask('Enter integer value', default=int(arg.default))
        return [arg.flag, str(value)]

    while True:
        prompt_text = 'Enter value'
        raw = Prompt.ask(prompt_text, default=default_text) if default_text is not None else Prompt.ask(prompt_text)

        if raw == '' and not arg.required:
            return []

        try:
            validated = _validate_known_type(raw, arg.type_name)
            return [arg.flag, validated]
        except (TypeError, ValueError) as error:
            console.print(f'[red]Invalid value: {error}[/red]')


def _collect_cli_args(console: Console, script: ScriptSpec) -> list[str]:
    """Prompt interactively for all arguments of a selected script."""
    console.print(Panel.fit(f'{script.name}\n{script.description}', title='Selected Script'))

    cli_tokens: list[str] = []
    for arg in script.arguments:
        cli_tokens.extend(_prompt_argument(console, arg))
        console.print('')

    return cli_tokens


def _run_script(console: Console, script: ScriptSpec, cli_tokens: list[str]) -> int:
    """Execute selected script and stream output in the same terminal."""
    relative_script = script.path.relative_to(PROJECT_ROOT)
    command = [sys.executable, str(relative_script), *cli_tokens]

    console.print('[bold]Command preview:[/bold]')
    console.print(' '.join(shlex.quote(part) for part in command))

    if not Confirm.ask('Run this command now?', default=True):
        console.print('[yellow]Execution cancelled.[/yellow]')
        return 0

    process = subprocess.run(command, cwd=PROJECT_ROOT)
    return int(process.returncode)


def _choose_script(console: Console, scripts: list[ScriptSpec]) -> ScriptSpec | None:
    """Prompt for script selection by index."""
    _render_scripts_table(console, scripts)
    valid_choices = [str(i) for i in range(1, len(scripts) + 1)] + ['q']
    selected = Prompt.ask('Select script number (or q to quit)', choices=valid_choices, default='q')
    if selected == 'q':
        return None
    return scripts[int(selected) - 1]


def main() -> None:
    """Entry point for interactive script launcher."""
    parser = argparse.ArgumentParser(description='Interactive launcher for scripts/run_*.py')
    parser.add_argument('--list', action='store_true', help='List discovered scripts and exit.')
    args = parser.parse_args()

    console = Console()
    scripts, warnings = _discover_scripts()
    _print_discovery_warnings(console, warnings)

    if not scripts:
        console.print('[red]No run_*.py scripts found in scripts/.[/red]')
        sys.exit(1)

    if args.list:
        for spec in scripts:
            print(f'{spec.path.name}: {spec.description}')
        return

    console.print(Panel.fit('Atlas Script Launcher', subtitle='Interactive Terminal GUI'))

    while True:
        selected_script = _choose_script(console, scripts)
        if selected_script is None:
            console.print('Goodbye')
            break

        selected_args = _collect_cli_args(console, selected_script)
        exit_code = _run_script(console, selected_script, selected_args)
        if exit_code == 0:
            console.print('[green]Script finished successfully.[/green]')
        else:
            console.print(f'[red]Script exited with code {exit_code}.[/red]')

        if not Confirm.ask('Run another script?', default=True):
            break
        console.print('')


if __name__ == '__main__':
    main()