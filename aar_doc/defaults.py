"""
Defaults module for aar_doc.

This module provides utilities for collecting the default values
of an argument_spec and writing the final defaults file.
"""

from dataclasses import dataclass, field
from os import linesep
from pathlib import Path
from typing import Any

import typer
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import LiteralScalarString

yaml = YAML()
yaml.indent(mapping=2, sequence=2, offset=2)
yaml.encoding = "utf-8"
yaml.allow_unicode = True


@dataclass
class RoleDefault:
    """
    Class that represents a role default.
    """

    name: str
    value: Any
    description: str


@dataclass
class RoleDefaultsManager:
    """Class for managing all the role defaults of a role.

    Args:
        _overwrite (bool): Whether a default should be overwritten,
        if it's already known. Defaults to False.
    """

    _defaults: dict[str, RoleDefault] = field(default_factory=lambda: {}, init=False)
    _overwrite: bool = False

    @property
    def defaults(self) -> list[RoleDefault]:
        """Get the list of tracked defaults.

        Returns:
            list[RoleDefault]: List of role defaults.
        """
        return list(self._defaults.values())

    def add_default(
        self,
        name: str,
        value: Any,
        description: str = "No description provided.",
    ) -> None:
        """Add a default.

        Args:
            name (str): Variable name of the default.
            value (Any): Value of the default.
            description (str, optional): Description of the default.
            Defaults to "No description provided.".
        """
        if isinstance(value, str):
            value = value.strip()

        if self._overwrite:
            self._defaults[name] = RoleDefault(name, value, description)
        else:
            self._defaults.setdefault(name, RoleDefault(name, value, description))

    def to_commented_map(self) -> CommentedMap:
        """
        Returns all tracked defaults as a CommentedMap.
        """
        commented_defaults = CommentedMap()
        for role_default in self.defaults:
            value = role_default.value
            if isinstance(value, str) and "\n" in value:
                value = LiteralScalarString(value)
            commented_defaults[role_default.name] = value
            commented_defaults.yaml_set_comment_before_after_key(
                role_default.name,
                role_default.description,
            )
        return commented_defaults


def generate_commented_defaults(
    argument_spec_data: dict,
    overwrite_duplicate_defaults: bool,
) -> CommentedMap:
    """Generates the inital RoleDefaults"""
    defaults_manager = RoleDefaultsManager(overwrite_duplicate_defaults)

    for entry_point in argument_spec_data:
        options = argument_spec_data.get(entry_point, {}).get("options")
        if not options:
            continue
        for name, spec in options.items():
            value = spec.get("default")
            if value is not None:
                description = spec.get("description")
                defaults_manager.add_default(
                    name,
                    value,
                    description,
                )
    return defaults_manager.to_commented_map()


def write_defaults(
    output_file_path: Path,
    role_path: Path,
    role_defaults: CommentedMap,
) -> None:
    """
    Writes the generated defaults CommentedMap to the given file.
    """
    if output_file_path.name == "README.md":
        output: Path = role_path / "defaults" / "main.yml"
    elif output_file_path.is_absolute():
        output = output_file_path
    else:
        output = role_path / "defaults" / output_file_path
    output.resolve()

    try:
        # Create parent directories if they don't exist yet.
        # Needed if the <role_path>/defaults was not created yet.
        output.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        typer.echo(
            f"Unable to create necessary directories for '{output}'. "
            "The following error occured: '{exc.strerror}'.",
        )
        raise typer.Exit(1) from exc

    try:
        with open(output, "w", encoding="utf-8") as defaults_file:
            defaults_file.writelines(
                ["---" + linesep, "# Automatically generated by aar-doc" + linesep],
            )
            yaml.dump(role_defaults, defaults_file)
    except OSError as exc:
        typer.echo(
            f"Unable to write the file '{output}'. The following error occured: '{exc.strerror}'",
        )
        raise typer.Exit(1) from exc
