"""
Recipe Generator
Generates rewrite.yaml files and updates pom.xml with OpenRewrite plugin.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any
import xml.etree.ElementTree as ET
from app.utilities.logger import logger


class RecipeGenerator:
    """
    Generates OpenRewrite configuration files for Maven projects.
    Creates rewrite.yaml and adds the rewrite-maven-plugin to pom.xml.
    """
    
    REWRITE_MAVEN_PLUGIN_VERSION = "5.43.0"
    REWRITE_MAVEN_DEPENDENCY_VERSION = "8.38.0"
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.pom_path = self.project_path / "pom.xml"
        self.rewrite_yaml_path = self.project_path / "rewrite.yaml"
    
    def generate_rewrite_yaml(
        self,
        recipe_name: str,
        display_name: str,
        description: str,
        recipe_list: List[Dict[str, Any]]
    ) -> str:
        """
        Generate rewrite.yaml content from selected recipes.
        
        Args:
            recipe_name: Fully qualified name for the custom recipe (e.g., com.aura.fix.FixIssue)
            display_name: Human-readable name
            description: Description of what this recipe does
            recipe_list: List of recipes with their arguments
            
        Returns:
            The generated YAML content
        """
        yaml_lines = [
            "---",
            "type: specs.openrewrite.org/v1beta/recipe",
            f"name: {recipe_name}",
            f"displayName: {display_name}",
            f"description: {description}",
            "",
            "recipeList:"
        ]
        
        for recipe in recipe_list:
            # Support both Recipe dataclass and plain dict
            if hasattr(recipe, 'name') and hasattr(recipe, 'arguments'):
                recipe_name_item = recipe.name
                arguments = recipe.arguments
            else:
                recipe_name_item = recipe.get("name", "")
                arguments = recipe.get("arguments", {})
            
            if arguments:
                # Recipe with arguments
                yaml_lines.append(f"  - {recipe_name_item}:")
                for arg_name, arg_value in arguments.items():
                    # Handle different types of values
                    if isinstance(arg_value, bool):
                        yaml_lines.append(f"      {arg_name}: {str(arg_value).lower()}")
                    elif isinstance(arg_value, (int, float)):
                        yaml_lines.append(f"      {arg_name}: {arg_value}")
                    elif arg_value is None:
                        continue  # Skip null values
                    else:
                        # Quote strings that might have special characters
                        yaml_lines.append(f"      {arg_name}: {arg_value}")
            else:
                # Recipe without arguments
                yaml_lines.append(f"  - {recipe_name_item}")
        
        yaml_content = "\n".join(yaml_lines)
        
        logger.debug(f"Generated rewrite.yaml content:\n{yaml_content}")
        return yaml_content
    
    def write_rewrite_yaml(
        self,
        recipe_name: str,
        display_name: str,
        description: str,
        recipe_list: List[Dict[str, Any]]
    ) -> Path:
        """
        Write rewrite.yaml file to the project root.
        
        Returns:
            Path to the created file
        """
        yaml_content = self.generate_rewrite_yaml(
            recipe_name, display_name, description, recipe_list
        )
        
        logger.info(f"Writing rewrite.yaml to {self.rewrite_yaml_path}")
        logger.info(f"rewrite.yaml content:\n{yaml_content}")
        
        with open(self.rewrite_yaml_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        return self.rewrite_yaml_path
    
    def apply_add_dependency_directly(self, group_id: str, artifact_id: str, version: str, scope: str = None) -> bool:
        """
        Directly add a dependency to pom.xml without using OpenRewrite.
        This is more reliable for projects that don't compile.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.pom_path.exists():
            logger.error(f"pom.xml not found at {self.pom_path}")
            return False
        
        try:
            # Register namespace to preserve it
            namespaces = {'': 'http://maven.apache.org/POM/4.0.0'}
            ET.register_namespace('', 'http://maven.apache.org/POM/4.0.0')
            
            tree = ET.parse(self.pom_path)
            root = tree.getroot()
            
            # Handle namespace
            ns_uri = ""
            if root.tag.startswith('{'):
                ns_uri = root.tag.split('}')[0] + '}'
            
            def elem(tag, text=None):
                e = ET.Element(f"{ns_uri}{tag}")
                if text:
                    e.text = text
                return e
            
            # Find or create dependencies section
            dependencies = root.find(f"{ns_uri}dependencies")
            if dependencies is None:
                dependencies = ET.SubElement(root, f"{ns_uri}dependencies")
            
            # Check if dependency already exists
            for dep in dependencies.findall(f"{ns_uri}dependency"):
                existing_group = dep.find(f"{ns_uri}groupId")
                existing_artifact = dep.find(f"{ns_uri}artifactId")
                if (existing_group is not None and existing_group.text == group_id and
                    existing_artifact is not None and existing_artifact.text == artifact_id):
                    logger.info(f"Dependency {group_id}:{artifact_id} already exists in pom.xml")
                    return True
            
            # Create new dependency element
            new_dep = elem("dependency")
            
            group_elem = elem("groupId", group_id)
            new_dep.append(group_elem)
            
            artifact_elem = elem("artifactId", artifact_id)
            new_dep.append(artifact_elem)
            
            version_elem = elem("version", version)
            new_dep.append(version_elem)
            
            if scope:
                scope_elem = elem("scope", scope)
                new_dep.append(scope_elem)
            
            dependencies.append(new_dep)
            
            # Write back to file with proper formatting
            self._indent_xml(root)
            tree.write(self.pom_path, encoding='utf-8', xml_declaration=True)
            
            logger.info(f"Added dependency {group_id}:{artifact_id}:{version} to pom.xml")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add dependency to pom.xml: {e}")
            return False
    
    def _indent_xml(self, elem, level=0):
        """Add proper indentation to XML elements."""
        i = "\n" + level * "    "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "    "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for child in elem:
                self._indent_xml(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def _detect_newline(self, content: str) -> str:
        return "\r\n" if "\r\n" in content else "\n"

    def _indent_block(self, block: str, indent: str, newline: str) -> str:
        return newline.join(f"{indent}{line}" if line else line for line in block.splitlines())

    def _find_rewrite_plugin_block(self, pom_content: str) -> tuple[int, int, str] | None:
        plugin_start_pattern = re.compile(r"(?m)^(?P<indent>[ \t]*)<plugin>\s*$")

        for match in plugin_start_pattern.finditer(pom_content):
            start = match.start()
            indent = match.group("indent")
            end_match = re.search(r"(?m)^[ \t]*</plugin>\s*$", pom_content[match.end():])
            if not end_match:
                continue

            end = match.end() + end_match.end()
            plugin_block = pom_content[start:end]
            if "<artifactId>rewrite-maven-plugin</artifactId>" not in plugin_block:
                continue

            line_end_match = re.match(r"(?:\r\n|\n)?", pom_content[end:])
            if line_end_match:
                end += line_end_match.end()
            return start, end, indent

        return None

    def _build_rewrite_plugin_xml(
        self,
        recipe_name: str,
        maven_only_recipes: bool,
        plugin_dependencies: List[Dict[str, str]] = None,
        newline: str = "\n",
        indent_unit: str = "    ",
    ) -> str:
        lines = [
            "<plugin>",
            f"{indent_unit}<groupId>org.openrewrite.maven</groupId>",
            f"{indent_unit}<artifactId>rewrite-maven-plugin</artifactId>",
            f"{indent_unit}<version>{self.REWRITE_MAVEN_PLUGIN_VERSION}</version>",
            f"{indent_unit}<configuration>",
            f"{indent_unit * 2}<configLocation>${{maven.multiModuleProjectDirectory}}/rewrite.yaml</configLocation>",
        ]

        if maven_only_recipes:
            lines.extend([
                f"{indent_unit * 2}<plainTextMasks>",
                f"{indent_unit * 3}<plainTextMask>**/*.java</plainTextMask>",
                f"{indent_unit * 2}</plainTextMasks>",
            ])

        lines.extend([
            f"{indent_unit * 2}<activeRecipes>",
            f"{indent_unit * 3}<recipe>{recipe_name}</recipe>",
            f"{indent_unit * 2}</activeRecipes>",
            f"{indent_unit}</configuration>",
            f"{indent_unit}<executions>",
            f"{indent_unit * 2}<execution>",
            f"{indent_unit * 3}<id>run-rewrite</id>",
            f"{indent_unit * 3}<phase>validate</phase>",
            f"{indent_unit * 3}<goals>",
            f"{indent_unit * 4}<goal>run</goal>",
            f"{indent_unit * 3}</goals>",
            f"{indent_unit * 2}</execution>",
            f"{indent_unit}</executions>",
            f"{indent_unit}<dependencies>",
            f"{indent_unit * 2}<dependency>",
            f"{indent_unit * 3}<groupId>org.openrewrite</groupId>",
            f"{indent_unit * 3}<artifactId>rewrite-maven</artifactId>",
            f"{indent_unit * 3}<version>{self.REWRITE_MAVEN_DEPENDENCY_VERSION}</version>",
            f"{indent_unit * 2}</dependency>",
            f"{indent_unit * 2}<dependency>",
            f"{indent_unit * 3}<groupId>org.openrewrite</groupId>",
            f"{indent_unit * 3}<artifactId>rewrite-java</artifactId>",
            f"{indent_unit * 3}<version>{self.REWRITE_MAVEN_DEPENDENCY_VERSION}</version>",
            f"{indent_unit * 2}</dependency>",
        ])

        for extra_dep in plugin_dependencies or []:
            lines.extend([
                f"{indent_unit * 2}<dependency>",
                f"{indent_unit * 3}<groupId>{extra_dep['groupId']}</groupId>",
                f"{indent_unit * 3}<artifactId>{extra_dep['artifactId']}</artifactId>",
                f"{indent_unit * 3}<version>{extra_dep['version']}</version>",
                f"{indent_unit * 2}</dependency>",
            ])

        lines.extend([
            f"{indent_unit}</dependencies>",
            "</plugin>",
        ])

        return newline.join(lines)

    def _replace_or_insert_rewrite_plugin(
        self,
        pom_content: str,
        plugin_xml: str,
    ) -> str:
        existing_plugin = self._find_rewrite_plugin_block(pom_content)
        if existing_plugin:
            start, end, indent = existing_plugin
            newline = self._detect_newline(pom_content)
            replacement = self._indent_block(plugin_xml, indent, newline)
            return pom_content[:start] + replacement + pom_content[end:]

        newline = self._detect_newline(pom_content)
        build_match = re.search(
            r"(?s)(?P<indent>^[ \t]*)<build>(?P<body>.*?)(?P=indent)</build>",
            pom_content,
            re.MULTILINE,
        )
        if build_match:
            build_indent = build_match.group("indent")
            build_body = build_match.group("body")
            search_start = 0

            plugin_management_match = re.search(
                r"(?s)^[ \t]*<pluginManagement>.*?^[ \t]*</pluginManagement>\s*",
                build_body,
                re.MULTILINE,
            )
            if plugin_management_match:
                search_start = plugin_management_match.end()

            direct_plugins_close = re.search(
                r"(?m)^(?P<indent>[ \t]*)</plugins>",
                build_body[search_start:],
            )
            if direct_plugins_close:
                indent = direct_plugins_close.group("indent")
                plugin_block = self._indent_block(plugin_xml, indent + "    ", newline)
                insertion = f"{plugin_block}{newline}"
                insert_at = build_match.start("body") + search_start + direct_plugins_close.start()
                return pom_content[:insert_at] + insertion + pom_content[insert_at:]

            build_close = build_match.end() - len(f"{build_indent}</build>")
            plugin_block = self._indent_block(plugin_xml, build_indent + "        ", newline)
            plugins_block = (
                f"{build_indent}    <plugins>{newline}"
                f"{plugin_block}{newline}"
                f"{build_indent}    </plugins>{newline}"
            )
            return pom_content[:build_close] + plugins_block + pom_content[build_close:]

        project_close = re.search(r"(?m)^(?P<indent>[ \t]*)</project>", pom_content)
        if project_close:
            indent = project_close.group("indent")
            plugin_block = self._indent_block(plugin_xml, indent + "        ", newline)
            build_block = (
                f"{indent}    <build>{newline}"
                f"{indent}        <plugins>{newline}"
                f"{plugin_block}{newline}"
                f"{indent}        </plugins>{newline}"
                f"{indent}    </build>{newline}"
            )
            return pom_content[:project_close.start()] + build_block + pom_content[project_close.start():]

        raise ValueError("Could not find insertion point for rewrite-maven-plugin in pom.xml")

    def remove_rewrite_plugin_from_pom(self) -> bool:
        """Remove the temporary rewrite plugin without reserializing the whole pom.xml."""
        if not self.pom_path.exists():
            return False

        try:
            pom_content = self.pom_path.read_text(encoding='utf-8')
            original_content = pom_content

            existing_plugin = self._find_rewrite_plugin_block(pom_content)
            if existing_plugin:
                start, end, _ = existing_plugin
                pom_content = pom_content[:start] + pom_content[end:]

            pom_content = re.sub(r"(?ms)^([ \t]*)<plugins>\s*</plugins>\s*\n?", "", pom_content)
            pom_content = re.sub(r"(?ms)^([ \t]*)<build>\s*</build>\s*\n?", "", pom_content)

            if pom_content != original_content:
                self.pom_path.write_text(pom_content, encoding='utf-8')
                logger.info(f"Removed rewrite-maven-plugin from {self.pom_path} without rewriting pom.xml structure")
            return True
        except Exception as e:
            logger.error(f"Failed to remove rewrite plugin from pom.xml: {e}")
            return False
    
    def add_rewrite_plugin_to_pom(
    self, 
    recipe_name: str, 
    maven_only_recipes: bool = True, 
    plugin_dependencies: List[Dict[str, str]] = None  # <--- NEW ARGUMENT
    ) -> bool:
        """
        Add OpenRewrite Maven plugin to pom.xml if not already present.
        
        Args:
            recipe_name: The fully qualified recipe name to activate
            maven_only_recipes: If True, skip Java source parsing (for pom.xml-only changes)
            
        Returns:
            True if successful, False otherwise
        """
        self._maven_only_recipes = maven_only_recipes
        
        if not self.pom_path.exists():
            logger.error(f"pom.xml not found at {self.pom_path}")
            return False
        
        try:
            pom_content = self.pom_path.read_text(encoding='utf-8')
            plugin_xml = self._build_rewrite_plugin_xml(
                recipe_name=recipe_name,
                maven_only_recipes=maven_only_recipes,
                plugin_dependencies=plugin_dependencies,
                newline=self._detect_newline(pom_content),
            )
            updated_content = self._replace_or_insert_rewrite_plugin(pom_content, plugin_xml)
            self.pom_path.write_text(updated_content, encoding='utf-8')
            logger.info(f"Added rewrite-maven-plugin to {self.pom_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to modify pom.xml: {e}")
            return False
    
    def _create_rewrite_plugin_element(self, recipe_name: str, ns_uri: str, 
                                   extra_dependencies: list = None) -> ET.Element:
        """
        Create the rewrite-maven-plugin XML element.
        
        Args:
            recipe_name: Recipe to activate
            ns_uri: XML namespace URI
            extra_dependencies: Optional list of dicts with 'groupId', 'artifactId', 'version'
        """
        
        maven_only = getattr(self, '_maven_only_recipes', True)
        
        def elem(tag, text=None):
            e = ET.Element(f"{ns_uri}{tag}")
            if text:
                e.text = text
            return e
        
        plugin = elem("plugin")
        
        group_id = elem("groupId", "org.openrewrite.maven")
        plugin.append(group_id)
        
        artifact_id = elem("artifactId", "rewrite-maven-plugin")
        plugin.append(artifact_id)
        
        version = elem("version", self.REWRITE_MAVEN_PLUGIN_VERSION)
        plugin.append(version)
        
        # Configuration
        configuration = elem("configuration")
        
        # Point to the rewrite.yaml file
        config_location = elem("configLocation", "${maven.multiModuleProjectDirectory}/rewrite.yaml")
        configuration.append(config_location)
        
        # For Maven-only recipes (AddDependency, UpgradeDependency, etc.)
        # Skip parsing Java sources to avoid compilation errors
        if maven_only:
            plain_text_masks = elem("plainTextMasks")
            mask1 = elem("plainTextMask", "**/*.java")
            plain_text_masks.append(mask1)
            configuration.append(plain_text_masks)
            logger.info("Configured to skip Java source parsing (Maven-only recipes)")
        
        # Active recipes
        active_recipes = elem("activeRecipes")
        recipe_elem = elem("recipe", recipe_name)
        active_recipes.append(recipe_elem)
        configuration.append(active_recipes)
        
        plugin.append(configuration)
        
        # Add execution to bind to validate phase (before compile)
        executions = elem("executions")
        execution = elem("execution")
        ex_id = elem("id", "run-rewrite")
        execution.append(ex_id)
        ex_phase = elem("phase", "validate")
        execution.append(ex_phase)
        ex_goals = elem("goals")
        ex_goal = elem("goal", "run")
        ex_goals.append(ex_goal)
        execution.append(ex_goals)
        executions.append(execution)
        plugin.append(executions)
        
        # Dependencies section
        dependencies = elem("dependencies")
        
        # Default dependencies (rewrite-maven, rewrite-java)
        dependency = elem("dependency")
        dependency.append(elem("groupId", "org.openrewrite"))
        dependency.append(elem("artifactId", "rewrite-maven"))
        dependency.append(elem("version", self.REWRITE_MAVEN_DEPENDENCY_VERSION))
        dependencies.append(dependency)
        
        dependency2 = elem("dependency")
        dependency2.append(elem("groupId", "org.openrewrite"))
        dependency2.append(elem("artifactId", "rewrite-java"))
        dependency2.append(elem("version", self.REWRITE_MAVEN_DEPENDENCY_VERSION))
        dependencies.append(dependency2)
        
        # Add extra dependencies (for migration recipes)
        if extra_dependencies:
            for extra_dep in extra_dependencies:
                dependency = elem("dependency")
                dependency.append(elem("groupId", extra_dep['groupId']))
                dependency.append(elem("artifactId", extra_dep['artifactId']))
                dependency.append(elem("version", extra_dep['version']))
                dependencies.append(dependency)
                logger.info(f"Added extra dependency: {extra_dep['groupId']}:{extra_dep['artifactId']}")
        
        plugin.append(dependencies)
        
        return plugin
    
    def _update_active_recipe(self, plugin: ET.Element, recipe_name: str, ns_uri: str) -> None:
        """Update the active recipe in an existing plugin configuration."""
        config = plugin.find(f"{ns_uri}configuration") if ns_uri else plugin.find("configuration")
        if config is None:
            config = ET.SubElement(plugin, f"{ns_uri}configuration" if ns_uri else "configuration")
        
        active_recipes = config.find(f"{ns_uri}activeRecipes") if ns_uri else config.find("activeRecipes")
        if active_recipes is None:
            active_recipes = ET.SubElement(config, f"{ns_uri}activeRecipes" if ns_uri else "activeRecipes")
        
        # Clear existing recipes and add new one
        active_recipes.clear()
        recipe_elem = ET.SubElement(active_recipes, f"{ns_uri}recipe" if ns_uri else "recipe")
        recipe_elem.text = recipe_name
    
    def cleanup(self) -> None:
        """Remove generated rewrite.yaml file."""
        if self.rewrite_yaml_path.exists():
            os.remove(self.rewrite_yaml_path)
            logger.info(f"Removed {self.rewrite_yaml_path}")

    def add_migration_dependencies_to_plugin(self, old_deps: list, new_deps: list) -> bool:
        """
        Add old and new dependencies to the rewrite-maven-plugin for type migration recipes.
        
        Args:
            old_deps: List of dicts with 'groupId', 'artifactId', 'version' for old types
            new_deps: List of dicts with 'groupId', 'artifactId', 'version' for new types
            
        Returns:
            True if successful, False otherwise
        """
        if not self.pom_path.exists():
            logger.error(f"pom.xml not found at {self.pom_path}")
            return False
        
        try:
            ET.register_namespace('', 'http://maven.apache.org/POM/4.0.0')
            tree = ET.parse(self.pom_path)
            root = tree.getroot()
            
            # Handle namespace
            if root.tag.startswith('{'):
                ns_uri = root.tag.split('}')[0] + '}'
            else:
                ns_uri = ""
            
            # Find the rewrite plugin
            build = root.find(f"{ns_uri}build")
            if build is None:
                logger.error("No <build> section found")
                return False
            
            plugins = build.find(f"{ns_uri}plugins")
            if plugins is None:
                logger.error("No <plugins> section found")
                return False
            
            rewrite_plugin = None
            for plugin in plugins.findall(f"{ns_uri}plugin"):
                artifact_id = plugin.find(f"{ns_uri}artifactId")
                if artifact_id is not None and artifact_id.text == "rewrite-maven-plugin":
                    rewrite_plugin = plugin
                    break
            
            if rewrite_plugin is None:
                logger.error("rewrite-maven-plugin not found in pom.xml")
                return False
            
            # Find or create dependencies section in plugin
            dependencies = rewrite_plugin.find(f"{ns_uri}dependencies")
            if dependencies is None:
                dependencies = ET.SubElement(rewrite_plugin, f"{ns_uri}dependencies")
            
            def elem(tag, text=None):
                e = ET.Element(f"{ns_uri}{tag}")
                if text:
                    e.text = text
                return e
            
            # Add old dependencies
            for old_dep in old_deps:
                dependency = elem("dependency")
                dependency.append(elem("groupId", old_dep['groupId']))
                dependency.append(elem("artifactId", old_dep['artifactId']))
                dependency.append(elem("version", old_dep['version']))
                dependencies.append(dependency)
                logger.info(f"Added old dependency: {old_dep['groupId']}:{old_dep['artifactId']}")
            
            # Add new dependencies
            for new_dep in new_deps:
                dependency = elem("dependency")
                dependency.append(elem("groupId", new_dep['groupId']))
                dependency.append(elem("artifactId", new_dep['artifactId']))
                dependency.append(elem("version", new_dep['version']))
                dependencies.append(dependency)
                logger.info(f"Added new dependency: {new_dep['groupId']}:{new_dep['artifactId']}")
            
            tree.write(self.pom_path, encoding='utf-8', xml_declaration=True)
            logger.info("Successfully added migration dependencies to rewrite-maven-plugin")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add migration dependencies: {e}")
            return False