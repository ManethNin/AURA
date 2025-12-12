import dspy

# Inspired by https://github.com/paul-gauthier/aider/blob/main/aider/coders/udiff_prompts.py
class CodeDiffGenerator(dspy.Signature):
    #fmt: off
    """# File editing rules:
Return edits similar to unified diffs that `diff -U0` would produce.
Make sure that the diff is fenced with ```diff on its own line and is closed with ```.
Any language snippets that are not diffs will be rejected.

Make sure you include the first 2 lines with the file paths.
Don't include timestamps with the file paths.

Start each hunk of changes with a `@@ ... @@` line.
Never include line numbers like `diff -U0` does.
The user's patch tool doesn't need them.

The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
Make sure you mark all new or modified lines with `+`.
Don't leave out any lines or the diff patch won't apply correctly. 
Make sure the context lines are correct. 
Newlines as well as indentation and comments are very important!
Do not add your own comments or explanations to the diff.

Start a new hunk for each section of the file that needs changes.

Only output hunks that specify changes with `+` or `-` lines.
Skip any hunks that are entirely unchanging ` ` lines.

Output hunks in whatever order makes the most sense.
Hunks don't need to be in any particular order.

When editing a function, method, loop, etc use a hunk to replace the *entire* code block.
Delete the entire existing version with `-` lines and then add a new, updated version with `+` lines.
This will help you generate correct code and correct diffs.

# Instructions:
Act as an expert Java software developer.
The program has issues after a version upgrade of a dependency.
Try using minimal changes to the code to fix the issues. 
Do not attempt to add new dependencies.
Dont explain your actions, just provide good diffs that always adhere to the rules.
"""
#fmt: on

    code = dspy.InputField(desc="The source code of the program.")
    path = dspy.InputField(desc="The path to the file that needs to be edited.")
    answer = dspy.OutputField(desc="A compliant diff to fix the changes in the API")

class CodeDiffGeneratorWithUpdatedDependencyDetails(dspy.Signature):
    #fmt: off
    """# File editing rules:
Return edits similar to unified diffs that `diff -U0` would produce.
Make sure that the diff is fenced with ```diff on its own line and is closed with ```.
Any language snippets that are not diffs will be rejected.

Make sure you include the first 2 lines with the file paths.
Don't include timestamps with the file paths.

Start each hunk of changes with a `@@ ... @@` line.
Never include line numbers like `diff -U0` does.
The user's patch tool doesn't need them.

The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
Make sure you mark all new or modified lines with `+`.
Don't leave out any lines or the diff patch won't apply correctly. 
Make sure the context lines are correct. 
Newlines as well as indentation and comments are very important!
Do not add your own comments or explanations to the diff.

Start a new hunk for each section of the file that needs changes.

Only output hunks that specify changes with `+` or `-` lines.
Skip any hunks that are entirely unchanging ` ` lines.

Output hunks in whatever order makes the most sense.
Hunks don't need to be in any particular order.

When editing a function, method, loop, etc use a hunk to replace the *entire* code block.
Delete the entire existing version with `-` lines and then add a new, updated version with `+` lines.
This will help you generate correct code and correct diffs.

# Instructions:
Act as an expert Java software developer.
The program has issues after a version upgrade of a dependency.
Try using minimal changes to the code to fix the issues. 
Do not attempt to add new dependencies.
Dont explain your actions, just provide good diffs that always adhere to the rules.
"""
#fmt: on
    updated_dependency_details = dspy.InputField(desc="The details of the updated dependency version.")
    code = dspy.InputField(desc="The source code of the program.")
    path = dspy.InputField(desc="The path to the file that needs to be edited.")
    answer = dspy.OutputField(desc="A compliant diff to fix the changes in the API")

class CodeDiffGeneratorWithApiChanges(dspy.Signature):
    #fmt: off
    """# File editing rules:
Return edits similar to unified diffs that `diff -U0` would produce.
Make sure that the diff is fenced with ```diff on its own line and is closed with ```.
Any language snippets that are not diffs will be rejected.

Make sure you include the first 2 lines with the file paths.
Don't include timestamps with the file paths.

Start each hunk of changes with a `@@ ... @@` line.
Never include line numbers like `diff -U0` does.
The user's patch tool doesn't need them.

The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
Make sure you mark all new or modified lines with `+`.
Don't leave out any lines or the diff patch won't apply correctly. 
Make sure the context lines are correct. 
Newlines as well as indentation and comments are very important!
Do not add your own comments or explanations to the diff.

Start a new hunk for each section of the file that needs changes.

Only output hunks that specify changes with `+` or `-` lines.
Skip any hunks that are entirely unchanging ` ` lines.

Output hunks in whatever order makes the most sense.
Hunks don't need to be in any particular order.

When editing a function, method, loop, etc use a hunk to replace the *entire* code block.
Delete the entire existing version with `-` lines and then add a new, updated version with `+` lines.
This will help you generate correct code and correct diffs.

# Instructions:
Act as an expert Java software developer.
The program has issues after a version upgrade of a dependency.
Try using minimal changes to the code to fix the issues. 
Do not attempt to add new dependencies.
Dont explain your actions, just provide good diffs that always adhere to the rules.
"""
#fmt: on
    api_changes = dspy.InputField(desc="Changes in the API of the dependency.")
    code = dspy.InputField(desc="The source code of the program.")
    path = dspy.InputField(desc="The path to the file that needs to be edited.")
    answer = dspy.OutputField(desc="A compliant diff to fix the changes in the API")

class CodeDiffGeneratorWithInitialError(dspy.Signature):
    #fmt: off
    """# File editing rules:
Return edits similar to unified diffs that `diff -U0` would produce.
Make sure that the diff is fenced with ```diff on its own line and is closed with ```.
Any language snippets that are not diffs will be rejected.

Make sure you include the first 2 lines with the file paths.
Don't include timestamps with the file paths.

Start each hunk of changes with a `@@ ... @@` line.
Never include line numbers like `diff -U0` does.
The user's patch tool doesn't need them.

The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
Make sure you mark all new or modified lines with `+`.
Don't leave out any lines or the diff patch won't apply correctly. 
Make sure the context lines are correct. 
Newlines as well as indentation and comments are very important!
Do not add your own comments or explanations to the diff.

Start a new hunk for each section of the file that needs changes.

Only output hunks that specify changes with `+` or `-` lines.
Skip any hunks that are entirely unchanging ` ` lines.

Output hunks in whatever order makes the most sense.
Hunks don't need to be in any particular order.

When editing a function, method, loop, etc use a hunk to replace the *entire* code block.
Delete the entire existing version with `-` lines and then add a new, updated version with `+` lines.
This will help you generate correct code and correct diffs.

# Instructions:
Act as an expert Java software developer.
The program has issues after a version upgrade of a dependency.
Try using minimal changes to the code to fix the issues. 
Do not attempt to add new dependencies.
Dont explain your actions, just provide good diffs that always adhere to the rules.
"""
#fmt: on
    initial_error = dspy.InputField(desc="The maven error that occurred during the build.")
    code = dspy.InputField(desc="The source code of the program.")
    path = dspy.InputField(desc="The path to the file that needs to be edited.")
    answer = dspy.OutputField(desc="A compliant diff to fix the changes in the API")

class CodeDiffGeneratorWithUpdatedDependencyDetailsAndApiChanges(dspy.Signature):
    #fmt: off
    """# File editing rules:
Return edits similar to unified diffs that `diff -U0` would produce.
Make sure that the diff is fenced with ```diff on its own line and is closed with ```.
Any language snippets that are not diffs will be rejected.

Make sure you include the first 2 lines with the file paths.
Don't include timestamps with the file paths.

Start each hunk of changes with a `@@ ... @@` line.
Never include line numbers like `diff -U0` does.
The user's patch tool doesn't need them.

The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
Make sure you mark all new or modified lines with `+`.
Don't leave out any lines or the diff patch won't apply correctly. 
Make sure the context lines are correct. 
Newlines as well as indentation and comments are very important!
Do not add your own comments or explanations to the diff.

Start a new hunk for each section of the file that needs changes.

Only output hunks that specify changes with `+` or `-` lines.
Skip any hunks that are entirely unchanging ` ` lines.

Output hunks in whatever order makes the most sense.
Hunks don't need to be in any particular order.

When editing a function, method, loop, etc use a hunk to replace the *entire* code block.
Delete the entire existing version with `-` lines and then add a new, updated version with `+` lines.
This will help you generate correct code and correct diffs.

# Instructions:
Act as an expert Java software developer.
The program has issues after a version upgrade of a dependency.
Try using minimal changes to the code to fix the issues. 
Do not attempt to add new dependencies.
Dont explain your actions, just provide good diffs that always adhere to the rules.
"""
#fmt: on
    updated_dependency_details = dspy.InputField(desc="The details of the updated dependency version.")
    api_changes = dspy.InputField(desc="Changes in the API of the dependency.")
    code = dspy.InputField(desc="The source code of the program.")
    path = dspy.InputField(desc="The path to the file that needs to be edited.")
    answer = dspy.OutputField(desc="A compliant diff to fix the changes in the API")

class CodeDiffGeneratorWithUpdatedDependencyDetailsAndInitialError(dspy.Signature):
    #fmt: off
    """# File editing rules:
Return edits similar to unified diffs that `diff -U0` would produce.
Make sure that the diff is fenced with ```diff on its own line and is closed with ```.
Any language snippets that are not diffs will be rejected.

Make sure you include the first 2 lines with the file paths.
Don't include timestamps with the file paths.

Start each hunk of changes with a `@@ ... @@` line.
Never include line numbers like `diff -U0` does.
The user's patch tool doesn't need them.

The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
Make sure you mark all new or modified lines with `+`.
Don't leave out any lines or the diff patch won't apply correctly. 
Make sure the context lines are correct. 
Newlines as well as indentation and comments are very important!
Do not add your own comments or explanations to the diff.

Start a new hunk for each section of the file that needs changes.

Only output hunks that specify changes with `+` or `-` lines.
Skip any hunks that are entirely unchanging ` ` lines.

Output hunks in whatever order makes the most sense.
Hunks don't need to be in any particular order.

When editing a function, method, loop, etc use a hunk to replace the *entire* code block.
Delete the entire existing version with `-` lines and then add a new, updated version with `+` lines.
This will help you generate correct code and correct diffs.

# Instructions:
Act as an expert Java software developer.
The program has issues after a version upgrade of a dependency.
Try using minimal changes to the code to fix the issues. 
Do not attempt to add new dependencies.
Dont explain your actions, just provide good diffs that always adhere to the rules.
"""
#fmt: on
    updated_dependency_details = dspy.InputField(desc="The details of the updated dependency version.")
    initial_error = dspy.InputField(desc="The maven error that occurred during the build.")
    code = dspy.InputField(desc="The source code of the program.")
    path = dspy.InputField(desc="The path to the file that needs to be edited.")
    answer = dspy.OutputField(desc="A compliant diff to fix the changes in the API")

class CodeDiffGeneratorWithApiChangesAndInitialError(dspy.Signature):
    #fmt: off
    """# File editing rules:
Return edits similar to unified diffs that `diff -U0` would produce.
Make sure that the diff is fenced with ```diff on its own line and is closed with ```.
Any language snippets that are not diffs will be rejected.

Make sure you include the first 2 lines with the file paths.
Don't include timestamps with the file paths.

Start each hunk of changes with a `@@ ... @@` line.
Never include line numbers like `diff -U0` does.
The user's patch tool doesn't need them.

The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
Make sure you mark all new or modified lines with `+`.
Don't leave out any lines or the diff patch won't apply correctly. 
Make sure the context lines are correct. 
Newlines as well as indentation and comments are very important!
Do not add your own comments or explanations to the diff.

Start a new hunk for each section of the file that needs changes.

Only output hunks that specify changes with `+` or `-` lines.
Skip any hunks that are entirely unchanging ` ` lines.

Output hunks in whatever order makes the most sense.
Hunks don't need to be in any particular order.

When editing a function, method, loop, etc use a hunk to replace the *entire* code block.
Delete the entire existing version with `-` lines and then add a new, updated version with `+` lines.
This will help you generate correct code and correct diffs.

# Instructions:
Act as an expert Java software developer.
The program has issues after a version upgrade of a dependency.
Try using minimal changes to the code to fix the issues. 
Do not attempt to add new dependencies.
Dont explain your actions, just provide good diffs that always adhere to the rules.
"""
#fmt: on
    api_changes = dspy.InputField(desc="Changes in the API of the dependency.")
    initial_error = dspy.InputField(desc="The maven error that occurred during the build.")
    code = dspy.InputField(desc="The source code of the program.")
    path = dspy.InputField(desc="The path to the file that needs to be edited.")
    answer = dspy.OutputField(desc="A compliant diff to fix the changes in the API")

class CodeDiffGeneratorWithAll(dspy.Signature):
    #fmt: off
    """# File editing rules:
Return edits similar to unified diffs that `diff -U0` would produce.
Make sure that the diff is fenced with ```diff on its own line and is closed with ```.
Any language snippets that are not diffs will be rejected.

Make sure you include the first 2 lines with the file paths.
Don't include timestamps with the file paths.

Start each hunk of changes with a `@@ ... @@` line.
Never include line numbers like `diff -U0` does.
The user's patch tool doesn't need them.

The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
Make sure you mark all new or modified lines with `+`.
Don't leave out any lines or the diff patch won't apply correctly. 
Make sure the context lines are correct. 
Newlines as well as indentation and comments are very important!
Do not add your own comments or explanations to the diff.

Start a new hunk for each section of the file that needs changes.

Only output hunks that specify changes with `+` or `-` lines.
Skip any hunks that are entirely unchanging ` ` lines.

Output hunks in whatever order makes the most sense.
Hunks don't need to be in any particular order.

When editing a function, method, loop, etc use a hunk to replace the *entire* code block.
Delete the entire existing version with `-` lines and then add a new, updated version with `+` lines.
This will help you generate correct code and correct diffs.

# Instructions:
Act as an expert Java software developer.
The program has issues after a version upgrade of a dependency.
Try using minimal changes to the code to fix the issues. 
Do not attempt to add new dependencies.
Dont explain your actions, just provide good diffs that always adhere to the rules.
"""
#fmt: on
    updated_dependency_details = dspy.InputField(desc="The details of the updated dependency version.")
    api_changes = dspy.InputField(desc="Changes in the API of the dependency.")
    initial_error = dspy.InputField(desc="The maven error that occurred during the build.")
    code = dspy.InputField(desc="The source code of the program.")
    path = dspy.InputField(desc="The path to the file that needs to be edited.")
    answer = dspy.OutputField(desc="A compliant diff to fix the changes in the API")