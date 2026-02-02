"""
Recipe Generator
Generates rewrite.yaml files and updates pom.xml with OpenRewrite plugin.
"""

import os
from pathlib import Path
from typing import Dict, List, Any
import xml.etree.ElementTree as ET
from app.utils.logger import logger


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
        logger.debug(f"Content:\n{yaml_content}")
        
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
    
    def add_rewrite_plugin_to_pom(self, recipe_name: str, maven_only_recipes: bool = True) -> bool:
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
            # Register namespaces to preserve them
            namespaces = {'': 'http://maven.apache.org/POM/4.0.0'}
            ET.register_namespace('', 'http://maven.apache.org/POM/4.0.0')
            
            tree = ET.parse(self.pom_path)
            root = tree.getroot()
            
            # Handle namespace
            ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
            
            # Check if using namespace
            if root.tag.startswith('{'):
                ns_uri = root.tag.split('}')[0] + '}'
                build = root.find(f"{ns_uri}build")
                if build is None:
                    build = ET.SubElement(root, f"{ns_uri}build")
                
                plugins = build.find(f"{ns_uri}plugins")
                if plugins is None:
                    plugins = ET.SubElement(build, f"{ns_uri}plugins")
                
                # Check if rewrite plugin already exists
                for plugin in plugins.findall(f"{ns_uri}plugin"):
                    artifact_id = plugin.find(f"{ns_uri}artifactId")
                    if artifact_id is not None and artifact_id.text == "rewrite-maven-plugin":
                        logger.info("rewrite-maven-plugin already exists in pom.xml")
                        # Update the active recipe
                        self._update_active_recipe(plugin, recipe_name, ns_uri)
                        tree.write(self.pom_path, encoding='utf-8', xml_declaration=True)
                        return True
                
                # Add the plugin
                plugin = self._create_rewrite_plugin_element(recipe_name, ns_uri)
                plugins.append(plugin)
            else:
                # No namespace
                build = root.find("build")
                if build is None:
                    build = ET.SubElement(root, "build")
                
                plugins = build.find("plugins")
                if plugins is None:
                    plugins = ET.SubElement(build, "plugins")
                
                # Check if rewrite plugin already exists
                for plugin in plugins.findall("plugin"):
                    artifact_id = plugin.find("artifactId")
                    if artifact_id is not None and artifact_id.text == "rewrite-maven-plugin":
                        logger.info("rewrite-maven-plugin already exists in pom.xml")
                        self._update_active_recipe(plugin, recipe_name, "")
                        tree.write(self.pom_path, encoding='utf-8', xml_declaration=True)
                        return True
                
                # Add the plugin
                plugin = self._create_rewrite_plugin_element(recipe_name, "")
                plugins.append(plugin)
            
            # Write back to file
            tree.write(self.pom_path, encoding='utf-8', xml_declaration=True)
            logger.info(f"Added rewrite-maven-plugin to {self.pom_path}")
            return True
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse pom.xml: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to modify pom.xml: {e}")
            return False
    
    def _create_rewrite_plugin_element(self, recipe_name: str, ns_uri: str) -> ET.Element:
        """Create the rewrite-maven-plugin XML element."""
        
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
        config_location = elem("configLocation", "${project.basedir}/rewrite.yaml")
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
        
        # Dependencies - add rewrite-java for Java recipes
        dependencies = elem("dependencies")
        
        # rewrite-maven dependency
        dependency = elem("dependency")
        dep_group_id = elem("groupId", "org.openrewrite")
        dependency.append(dep_group_id)
        dep_artifact_id = elem("artifactId", "rewrite-maven")
        dependency.append(dep_artifact_id)
        dep_version = elem("version", self.REWRITE_MAVEN_DEPENDENCY_VERSION)
        dependency.append(dep_version)
        dependencies.append(dependency)
        
        # rewrite-java dependency (needed for Java-related recipes)
        dependency2 = elem("dependency")
        dep2_group_id = elem("groupId", "org.openrewrite")
        dependency2.append(dep2_group_id)
        dep2_artifact_id = elem("artifactId", "rewrite-java")
        dependency2.append(dep2_artifact_id)
        dep2_version = elem("version", self.REWRITE_MAVEN_DEPENDENCY_VERSION)
        dependency2.append(dep2_version)
        dependencies.append(dependency2)
        
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
