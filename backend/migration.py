import os
import re
from pathlib import Path

BASE_DIR = Path(r"d:\FYP\master\AURA\backend")

moves = [
    ("app/agents/workflow.py", "app/graph/workflow.py"),
    ("app/recipe_agent/recipe_orchestrator.py", "app/graph/recipe_orchestrator.py"),
    ("app/main.py", "app/nodes/main.py"),
    ("app/api/routes/auth.py", "app/nodes/routes/auth.py"),
    ("app/api/routes/changes.py", "app/nodes/routes/changes.py"),
    ("app/api/routes/local_repos.py", "app/nodes/routes/local_repos.py"),
    ("app/api/routes/repositories.py", "app/nodes/routes/repositories.py"),
    ("app/api/routes/users.py", "app/nodes/routes/users.py"),
    ("app/api/routes/webhook.py", "app/nodes/routes/webhook.py"),
    ("app/api/routes/__init__.py", "app/nodes/routes/__init__.py"),
    ("app/api/__init__.py", "app/nodes/__init__.py"),
    ("app/agents/service.py", "app/nodes/service.py"),
    ("app/recipe_agent/recipe_service.py", "app/nodes/recipe_service.py"),
    ("app/services/repair_service.py", "app/nodes/repair_service.py"),
    ("app/services/webhook_service.py", "app/nodes/webhook_service.py"),
    ("app/models/change.py", "app/state/models/change.py"),
    ("app/models/repository.py", "app/state/models/repository.py"),
    ("app/models/user.py", "app/state/models/user.py"),
    ("app/models/__init__.py", "app/state/models/__init__.py"),
    ("app/schemas/schemas.py", "app/state/schemas.py"),
    ("app/schemas/__init__.py", "app/state/__init__.py"),
    ("app/masterthesis/dataset/dataset_types.py", "app/state/dataset_types.py"),
    ("app/masterthesis/dataset/feature_flags.py", "app/state/feature_flags.py"),
    ("app/masterthesis/llm/types.py", "app/state/llm_types.py"),
    ("app/agents/tools.py", "app/tools/tools.py"),
    ("app/agents/callback.py", "app/tools/callback.py"),
    ("app/recipe_agent/recipe_executor.py", "app/tools/recipe_executor.py"),
    ("app/recipe_agent/recipe_generator.py", "app/tools/recipe_generator.py"),
    ("app/masterthesis/agent/DiffAgent.py", "app/tools/agents/DiffAgent.py"),
    ("app/masterthesis/agent/DockerAgent.py", "app/tools/agents/DockerAgent.py"),
    ("app/masterthesis/agent/GitAgent.py", "app/tools/agents/GitAgent.py"),
    ("app/masterthesis/agent/JapiCmpAgent.py", "app/tools/agents/JapiCmpAgent.py"),
    ("app/masterthesis/agent/LSPAgent.py", "app/tools/agents/LSPAgent.py"),
    ("app/masterthesis/agent/MarkdownAgent.py", "app/tools/agents/MarkdownAgent.py"),
    ("app/masterthesis/agent/MavenReproducerAgent.py", "app/tools/agents/MavenReproducerAgent.py"),
    ("app/masterthesis/agent/SpoonAgent.py", "app/tools/agents/SpoonAgent.py"),
    ("app/masterthesis/agent/TreeAgent.py", "app/tools/agents/TreeAgent.py"),
    ("app/masterthesis/agent/__init__.py", "app/tools/agents/__init__.py"),
    ("app/masterthesis/agent/aider/AdvancedDiffAgent.py", "app/tools/agents/aider/AdvancedDiffAgent.py"),
    ("app/masterthesis/agent/aider/GitTemporaryDirectory.py", "app/tools/agents/aider/GitTemporaryDirectory.py"),
    ("app/masterthesis/agent/aider/search_replace.py", "app/tools/agents/aider/search_replace.py"),
    ("app/masterthesis/agent/aider/__init__.py", "app/tools/agents/aider/__init__.py"),
    ("app/agents/planning_service.py", "app/chains/planning_service.py"),
    ("app/masterthesis/llm/pipeline.py", "app/chains/pipeline.py"),
    ("app/masterthesis/llm/generate_signatures.py", "app/chains/generate_signatures.py"),
    ("app/masterthesis/llm/__init__.py", "app/chains/__init__.py"),
    ("app/masterthesis/llm/signatures.py", "app/prompts/signatures.py"),
    ("app/services/github_service.py", "app/retrievers/github_service.py"),
    ("app/services/local_repository_service.py", "app/retrievers/local_repository_service.py"),
    ("app/masterthesis/maven/get_all_package_versions.py", "app/retrievers/maven/get_all_package_versions.py"),
    ("app/masterthesis/maven/get_classpaths_from_maven.py", "app/retrievers/maven/get_classpaths_from_maven.py"),
    ("app/masterthesis/maven/get_maven_dependencies_via_cli.py", "app/retrievers/maven/get_maven_dependencies_via_cli.py"),
    ("app/masterthesis/maven/get_maven_dependencies_via_parsing.py", "app/retrievers/maven/get_maven_dependencies_via_parsing.py"),
    ("app/masterthesis/maven/get_maven_package_metadata.py", "app/retrievers/maven/get_maven_package_metadata.py"),
    ("app/masterthesis/maven/test.py", "app/retrievers/maven/test.py"),
    ("app/masterthesis/maven/__init__.py", "app/retrievers/maven/__init__.py"),
    ("app/database/mongodb.py", "app/memory/mongodb.py"),
    ("app/database/__init__.py", "app/memory/__init__.py"),
    ("app/repositories/change_repository.py", "app/memory/change_repository.py"),
    ("app/repositories/repo_repository.py", "app/memory/repo_repository.py"),
    ("app/repositories/user_repository.py", "app/memory/user_repository.py"),
    ("app/repositories/init.py", "app/memory/init.py"),
    ("app/repositories/__init__.py", "app/memory/__init__.py"),
    ("app/core/config.py", "app/config/config.py"),
    ("app/core/__init__.py", "app/config/__init__.py"),
    ("app/utils/helpers.py", "app/utilities/helpers.py"),
    ("app/utils/logger.py", "app/utilities/logger.py"),
    ("app/utils/pipeline_logger.py", "app/utilities/pipeline_logger.py"),
    ("app/utils/__init__.py", "app/utilities/__init__.py"),
    ("app/auth/github_oauth.py", "app/utilities/auth/github_oauth.py"),
    ("app/auth/jwt.py", "app/utilities/auth/jwt.py"),
    ("app/auth/__init__.py", "app/utilities/auth/__init__.py"),
    ("app/masterthesis/ast/collect_imports.py", "app/utilities/ast/collect_imports.py"),
    ("app/masterthesis/ast/extract_usages.py", "app/utilities/ast/extract_usages.py"),
    ("app/masterthesis/ast/find_dependency_usages.py", "app/utilities/ast/find_dependency_usages.py"),
    ("app/masterthesis/ast/read_java_files.py", "app/utilities/ast/read_java_files.py"),
    ("app/masterthesis/ast/__init__.py", "app/utilities/ast/__init__.py"),
    ("app/masterthesis/dataset/find_compilation_errors.py", "app/utilities/dataset/find_compilation_errors.py"),
    ("app/masterthesis/dataset/load_dataset.py", "app/utilities/dataset/load_dataset.py"),
    ("app/masterthesis/dataset/prepare_folders.py", "app/utilities/dataset/prepare_folders.py"),
    ("app/masterthesis/dataset/__init__.py", "app/utilities/dataset/__init__.py"),
    ("app/masterthesis/evaluation/output_success_criterion.py", "app/utilities/evaluation/output_success_criterion.py"),
    ("app/masterthesis/evaluation/__init__.py", "app/utilities/evaluation/__init__.py"),
]

module_replacements = [
    ("app.masterthesis.maven.get_maven_dependencies_via_cli", "app.retrievers.maven.get_maven_dependencies_via_cli"),
    ("app.masterthesis.maven.get_maven_dependencies_via_parsing", "app.retrievers.maven.get_maven_dependencies_via_parsing"),
    ("app.masterthesis.maven.get_all_package_versions", "app.retrievers.maven.get_all_package_versions"),
    ("app.masterthesis.maven.get_classpaths_from_maven", "app.retrievers.maven.get_classpaths_from_maven"),
    ("app.masterthesis.maven.get_maven_package_metadata", "app.retrievers.maven.get_maven_package_metadata"),
    ("app.masterthesis.maven.test", "app.retrievers.maven.test"),
    ("app.masterthesis.maven", "app.retrievers.maven"),
    ("app.masterthesis.agent.aider.AdvancedDiffAgent", "app.tools.agents.aider.AdvancedDiffAgent"),
    ("app.masterthesis.agent.aider.GitTemporaryDirectory", "app.tools.agents.aider.GitTemporaryDirectory"),
    ("app.masterthesis.agent.aider.search_replace", "app.tools.agents.aider.search_replace"),
    ("app.masterthesis.agent.aider", "app.tools.agents.aider"),
    ("app.masterthesis.agent.DiffAgent", "app.tools.agents.DiffAgent"),
    ("app.masterthesis.agent.DockerAgent", "app.tools.agents.DockerAgent"),
    ("app.masterthesis.agent.GitAgent", "app.tools.agents.GitAgent"),
    ("app.masterthesis.agent.JapiCmpAgent", "app.tools.agents.JapiCmpAgent"),
    ("app.masterthesis.agent.LSPAgent", "app.tools.agents.LSPAgent"),
    ("app.masterthesis.agent.MarkdownAgent", "app.tools.agents.MarkdownAgent"),
    ("app.masterthesis.agent.MavenReproducerAgent", "app.tools.agents.MavenReproducerAgent"),
    ("app.masterthesis.agent.SpoonAgent", "app.tools.agents.SpoonAgent"),
    ("app.masterthesis.agent.TreeAgent", "app.tools.agents.TreeAgent"),
    ("app.masterthesis.agent", "app.tools.agents"),
    ("app.masterthesis.dataset.dataset_types", "app.state.dataset_types"),
    ("app.masterthesis.dataset.feature_flags", "app.state.feature_flags"),
    ("app.masterthesis.dataset.find_compilation_errors", "app.utilities.dataset.find_compilation_errors"),
    ("app.masterthesis.dataset.load_dataset", "app.utilities.dataset.load_dataset"),
    ("app.masterthesis.dataset.prepare_folders", "app.utilities.dataset.prepare_folders"),
    ("app.masterthesis.dataset", "app.utilities.dataset"),
    ("app.masterthesis.ast.collect_imports", "app.utilities.ast.collect_imports"),
    ("app.masterthesis.ast.extract_usages", "app.utilities.ast.extract_usages"),
    ("app.masterthesis.ast.find_dependency_usages", "app.utilities.ast.find_dependency_usages"),
    ("app.masterthesis.ast.read_java_files", "app.utilities.ast.read_java_files"),
    ("app.masterthesis.ast", "app.utilities.ast"),
    ("app.masterthesis.evaluation.output_success_criterion", "app.utilities.evaluation.output_success_criterion"),
    ("app.masterthesis.evaluation", "app.utilities.evaluation"),
    ("app.masterthesis.llm.pipeline", "app.chains.pipeline"),
    ("app.masterthesis.llm.generate_signatures", "app.chains.generate_signatures"),
    ("app.masterthesis.llm.signatures", "app.prompts.signatures"),
    ("app.masterthesis.llm.types", "app.state.llm_types"),
    ("app.masterthesis.llm", "app.chains"),
    ("app.api.routes.auth", "app.nodes.routes.auth"),
    ("app.api.routes.changes", "app.nodes.routes.changes"),
    ("app.api.routes.local_repos", "app.nodes.routes.local_repos"),
    ("app.api.routes.repositories", "app.nodes.routes.repositories"),
    ("app.api.routes.users", "app.nodes.routes.users"),
    ("app.api.routes.webhook", "app.nodes.routes.webhook"),
    ("app.api.routes", "app.nodes.routes"),
    ("app.api", "app.nodes"),
    ("app.models.change", "app.state.models.change"),
    ("app.models.repository", "app.state.models.repository"),
    ("app.models.user", "app.state.models.user"),
    ("app.models", "app.state.models"),
    ("app.schemas.schemas", "app.state.schemas"),
    ("app.schemas", "app.state.schemas"),
    ("app.agents.workflow", "app.graph.workflow"),
    ("app.agents.planning_service", "app.chains.planning_service"),
    ("app.agents.service", "app.nodes.service"),
    ("app.agents.tools", "app.tools.tools"),
    ("app.agents.callback", "app.tools.callback"),
    ("app.agents", "app.nodes"),
    ("app.recipe_agent.recipe_orchestrator", "app.graph.recipe_orchestrator"),
    ("app.recipe_agent.recipe_service", "app.nodes.recipe_service"),
    ("app.recipe_agent.recipe_executor", "app.tools.recipe_executor"),
    ("app.recipe_agent.recipe_generator", "app.tools.recipe_generator"),
    ("app.recipe_agent", "app.nodes"),
    ("app.services.github_service", "app.retrievers.github_service"),
    ("app.services.local_repository_service", "app.retrievers.local_repository_service"),
    ("app.services.repair_service", "app.nodes.repair_service"),
    ("app.services.webhook_service", "app.nodes.webhook_service"),
    ("app.services", "app.nodes"),
    ("app.repositories.change_repository", "app.memory.change_repository"),
    ("app.repositories.repo_repository", "app.memory.repo_repository"),
    ("app.repositories.user_repository", "app.memory.user_repository"),
    ("app.repositories.init", "app.memory.init"),
    ("app.repositories", "app.memory"),
    ("app.database.mongodb", "app.memory.mongodb"),
    ("app.database", "app.memory"),
    ("app.core.config", "app.config.config"),
    ("app.core", "app.config"),
    ("app.utils.helpers", "app.utilities.helpers"),
    ("app.utils.logger", "app.utilities.logger"),
    ("app.utils.pipeline_logger", "app.utilities.pipeline_logger"),
    ("app.utils", "app.utilities"),
    ("app.auth.github_oauth", "app.utilities.auth.github_oauth"),
    ("app.auth.jwt", "app.utilities.auth.jwt"),
    ("app.auth", "app.utilities.auth"),
]

def apply_refactor():
    print("Moving files...")
    # Do moving
    moved_files = []
    for old, new in moves:
        old_path = BASE_DIR / old
        new_path = BASE_DIR / new
        if old_path.exists():
            new_path.parent.mkdir(parents=True, exist_ok=True)
            old_path.rename(new_path)
            moved_files.append(new_path)
            print(f"Moved {old} -> {new}")
        else:
            if new_path.exists():
                moved_files.append(new_path)
            print(f"Warning: {old} does not exist!")

    print("\nUpdating imports...")
    # Collect all python files in the new structure
    py_files = []
    for root, dirs, files in os.walk(str(BASE_DIR / "app")):
        for f in files:
            if f.endswith(".py"):
                py_files.append(Path(root) / f)

    for py_file in py_files:
        with open(py_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        original_content = content
        
        # 1. Custom implicit fix for service.py
        if py_file.name == "service.py":
            content = re.sub(r'\bfrom tools import\b', 'from app.tools.tools import', content)
            content = re.sub(r'\bfrom workflow import\b', 'from app.graph.workflow import', content)

        # 2. Custom implicit fixes for __init__.py of recipe_agent (now nodes/__init__.py?)
        # Since I moved recipe_agent and nodes merged them, I'll explicitly patch those just in case
        content = re.sub(r'\brecipe_service\.RecipeAgentService\b', 'app.nodes.recipe_service.RecipeAgentService', content)
        content = re.sub(r'\brecipe_executor\.RecipeExecutor\b', 'app.tools.recipe_executor.RecipeExecutor', content)
        content = re.sub(r'\brecipe_generator\.RecipeGenerator\b', 'app.tools.recipe_generator.RecipeGenerator', content)
        content = re.sub(r'\brecipe_orchestrator\.RecipeOrchestrator\b', 'app.graph.recipe_orchestrator.RecipeOrchestrator', content)
        
        # 3. Apply global replacements mapping
        for old_mod, new_mod in module_replacements:
            # We look for the exact module string separated by non-word chars.
            # E.g. `import app.models` -> `import app.state.models`
            # Wait, `app.models` can have dots. \b handles word boundaries nicely at the ends.
            pattern = re.compile(r'(?<![\w\.])' + re.escape(old_mod) + r'(?![\w\.])')
            content = pattern.sub(new_mod, content)

        if content != original_content:
            with open(py_file, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Updated imports in {py_file.name}")

if __name__ == "__main__":
    apply_refactor()
