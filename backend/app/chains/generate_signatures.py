# Define the function to generate class templates
from pathlib import Path

INCLUDE_EXAMPLE = True

FILE_EDITING_RULES: str = """# Instructions:
Act as an expert Java software developer.
The program has issues after a version upgrade of a dependency.
Try using minimal changes to the code to fix the issues. 
Do not attempt to add new dependencies.
Do not explain your actions, just provide diffs that always adhere to the rules.

# File editing rules:
Return edits similar to unified diffs that `diff -U0` would produce.

Make sure you include the first 2 lines with the file paths.
Don't include timestamps with the file paths.

Start each hunk of changes with a `@@ ... @@` line.
Don't include line numbers like `diff -U0` does.
The user's patch tool doesn't need them.

The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
Make sure you mark all new or modified lines with `+`.
Don't leave out any lines or the diff patch won't apply correctly.

Indentation matters in the diffs!

Start a new hunk for each section of the file that needs changes.

Only output hunks that specify changes with `+` or `-` lines.
Skip any hunks that are entirely unchanging ` ` lines.

Output hunks in whatever order makes the most sense.
Hunks don't need to be in any particular order.

When editing a function, method, loop, etc use a hunk to replace the *entire* code block.
Delete the entire existing version with `-` lines and then add a new, updated version with `+` lines.
This will help you generate correct code and correct diffs.
"""

SIMPLE_EXAMPLE = """
# Example:

Updated Dependency Details: mysql:mysql-connector-java 5.1.49 -> 8.0.28

Initial Error: Failed to execute goal maven-compiler-plugin:3.10.1:compile (default-compile) on project pdb: Compilation failure: Compilation failure:
src/main/java/com/feedzai/commons/sql/abstraction/engine/impl/mysql/MySqlQueryExceptionHandler.java package com.mysql.jdbc.exceptions does not exist
src/main/java/com/feedzai/commons/sql/abstraction/engine/impl/mysql/MySqlQueryExceptionHandler.java cannot find symbol
symbol:   class MySQLTimeoutException
location: class com.feedzai.commons.sql.abstraction.engine.impl.mysql.MySqlQueryExceptionHandler

Code: package com.feedzai.commons.sql.abstraction.engine.impl.mysql;  import com.feedzai.commons.sql.abstraction.engine.handler.QueryExceptionHandler;  import com.mysql.jdbc.exceptions.MySQLTimeoutException;  import java.sql.SQLException;  /**  * A specific implementation of {@link QueryExceptionHandler} for MySQL engine.  *  * @author José Fidalgo (jose.fidalgo@feedzai.com)  * @since 2.5.1  */ public class MySqlQueryExceptionHandler extends QueryExceptionHandler {      /**      * The MySQL error code that indicates a unique constraint violation.      */     private static final int UNIQUE_CONSTRAINT_VIOLATION_ERROR_CODE = 1062;      @Override     public boolean isTimeoutException(final SQLException exception) {         return exception instanceof MySQLTimeoutException || super.isTimeoutException(exception);     }      @Override     public boolean isUniqueConstraintViolationException(final SQLException exception) {         return UNIQUE_CONSTRAINT_VIOLATION_ERROR_CODE == exception.getErrorCode()                 || super.isUniqueConstraintViolationException(exception);     } } 

Path: src/main/java/com/feedzai/commons/sql/abstraction/engine/impl/mysql/MySqlQueryExceptionHandler.java

Answer: ```diff
--- a/src/main/java/com/feedzai/commons/sql/abstraction/engine/impl/mysql/MySqlQueryExceptionHandler.java
+++ b/src/main/java/com/feedzai/commons/sql/abstraction/engine/impl/mysql/MySqlQueryExceptionHandler.java
@@ ... @@ 
 package com.feedzai.commons.sql.abstraction.engine.impl.mysql;

 import com.feedzai.commons.sql.abstraction.engine.handler.QueryExceptionHandler;

-import com.mysql.jdbc.exceptions.MySQLTimeoutException;
+import com.mysql.cj.jdbc.exceptions.MySQLTimeoutException;

 import java.sql.SQLException;
```
"""

if INCLUDE_EXAMPLE:
    FILE_EDITING_RULES = FILE_EDITING_RULES + SIMPLE_EXAMPLE


def generate_class(name, additional_fields):
    template = '''class {class_name}(dspy.Signature):
    #fmt: off
    """{FILE_EDITING_RULES}
"""
#fmt: on
{input_fields}
    code = dspy.InputField(desc="The source code of the program.")
    path = dspy.InputField(desc="The path to the file that needs to be edited.")
    answer = dspy.OutputField(desc="A compliant diff to fix the changes in the API")'''

    input_fields = "\n".join(
        [
            f'    {field} = dspy.InputField(desc="{desc}")'
            for field, desc in additional_fields.items()
        ]
    )
    return template.format(
        class_name=name,
        input_fields=input_fields,
        FILE_EDITING_RULES=FILE_EDITING_RULES,
    )


# Define the different classes with their additional fields
updated_dependency_details_description = (
    "The details of the updated dependency version."
)
api_changes_description = "Changes in the API of the dependency."
initial_error_description = "The maven error that occurred during the build."
classes = {
    "CodeDiffGenerator": {},
    "CodeDiffGeneratorWithUpdatedDependencyDetails": {
        "updated_dependency_details": updated_dependency_details_description
    },
    "CodeDiffGeneratorWithApiChanges": {"api_changes": api_changes_description},
    "CodeDiffGeneratorWithInitialError": {"initial_error": initial_error_description},
    "CodeDiffGeneratorWithUpdatedDependencyDetailsAndApiChanges": {
        "updated_dependency_details": updated_dependency_details_description,
        "api_changes": api_changes_description,
    },
    "CodeDiffGeneratorWithUpdatedDependencyDetailsAndInitialError": {
        "updated_dependency_details": updated_dependency_details_description,
        "initial_error": initial_error_description,
    },
    "CodeDiffGeneratorWithApiChangesAndInitialError": {
        "api_changes": api_changes_description,
        "initial_error": initial_error_description,
    },
    "CodeDiffGeneratorWithAll": {
        "updated_dependency_details": updated_dependency_details_description,
        "api_changes": api_changes_description,
        "initial_error": initial_error_description,
    },
}

# Generate class definitions
generated_classes = "\n\n".join(
    [generate_class(name, fields) for name, fields in classes.items()]
)

# Write to signatures.py
with open(Path(__file__).parent / "signatures.py", "w", encoding="utf-8") as f:
    f.write("import dspy\n\n")
    f.write(
        "# Inspired by https://github.com/paul-gauthier/aider/blob/main/aider/coders/udiff_prompts.py\n"
    )
    f.write(generated_classes)
