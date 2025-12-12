import os
import click
import json
from pydantic import BaseModel, Field
from typing import List, Optional


class MethodDetails(BaseModel):
    method_signature: str = Field(
        ...,
        description="The name of the deprecated method.",
        pattern=r"^(\w+\s)|(\*)*\([^()]*\)$|^\*$",
    )
    replacement: Optional[str] = Field(
        None,
        description="The suggested replacement for the deprecated method. If possible use a method signature.",
    )


class ClassBreakingChange(BaseModel):
    class_name: str = Field(
        ..., description="The name of the class affected by the breaking change."
    )
    package_name: Optional[str] = Field(
        None, description="The name of the package where the class is defined."
    )
    deprecations: List[MethodDetails] = Field(
        [], description="List of deprecated methods in the class."
    )
    removals: List[MethodDetails] = Field(
        [], description="List of removed methods in the class."
    )
    notes: Optional[str] = Field(
        None, description="Additional notes about the breaking change."
    )


class PackageBreakingChange(BaseModel):
    package_name: Optional[str] = Field(
        None,
        description="The name of the package where the change happened. Use this only if we are in a non-class context (no OOP).",
    )
    deprecations: List[MethodDetails] = Field(
        [], description="List of deprecated methods in the package."
    )
    removals: List[str] = Field(
        [], description="List of removed methods in the package."
    )
    notes: Optional[str] = Field(
        None, description="Additional notes about the breaking change."
    )


class OOPBreakingChanges(BaseModel):
    class_breaking_changes: List[ClassBreakingChange] = Field(
        ...,
        description="List of breaking changes (deprecations and removals). Use this with Classes in an OOP context.",
    )
    version: str = Field(
        ...,
        description="The version of the API where the breaking changes were introduced.",
    )


def prompt_method_details():
    method_signature = click.prompt(
        "Enter the method signature (e.g., foo() or bar(int, str))", type=str
    )
    replacement = click.prompt(
        "Enter the replacement method signature (optional)",
        type=str,
        default="",
        show_default=False,
    )
    if replacement:
        return MethodDetails(method_signature=method_signature, replacement=replacement)
    return MethodDetails(method_signature=method_signature)


def prompt_class_breaking_change():
    package_name = click.prompt(
        "Enter the package name (optional)", type=str, default="", show_default=False
    )
    class_name = click.prompt("Enter the class name", type=str)

    deprecations = []
    while click.confirm("Add a deprecated method?", default=True):
        deprecations.append(prompt_method_details())
    removals = []
    while click.confirm("Add a removed method?", default=True):
        removals.append(prompt_method_details())
    notes = click.prompt(
        "Enter additional notes (optional)", type=str, default="", show_default=False
    )
    return ClassBreakingChange(
        class_name=class_name,
        package_name=package_name if package_name else None,
        deprecations=deprecations,
        removals=removals,
        notes=notes if notes else None,
    )


def prompt_oop_breaking_changes():
    class_breaking_changes = []
    while click.confirm("Add a class breaking change?", default=True):
        class_breaking_changes.append(prompt_class_breaking_change())
    version = click.prompt("Enter the version of the API", type=str)
    return OOPBreakingChanges(
        class_breaking_changes=class_breaking_changes, version=version
    )


@click.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
)
def generate_json(directory):
    """
    CLI to generate JSON files based on markdown (.md) files in the given DIRECTORY.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                # Print a seperator
                click.echo("=" * 80)
                md_path = os.path.join(root, file)
                json_path = os.path.splitext(md_path)[0] + ".json"
                if not os.path.exists(json_path):
                    click.echo(f"Processing {md_path}")
                    oop_breaking_changes = prompt_oop_breaking_changes()
                    with open(json_path, "w", encoding="utf-8") as json_file:
                        json.dump(
                            oop_breaking_changes.dict(exclude_none=True),
                            json_file,
                            indent=4,
                        )
                    click.echo(f"JSON saved to {json_path}")
                else:
                    click.echo(f"JSON already exists for {md_path}")


if __name__ == "__main__":
    generate_json()
