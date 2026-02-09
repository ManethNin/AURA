# agent/workflow.py
"""
LangGraph workflow logic
"""

import json
import os
import random
import string
from typing import Literal
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from langchain_core.messages.tool import ToolCall
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict
from langgraph.prebuilt import ToolExecutor, ToolInvocation
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_groq import ChatGroq



# Copy your system_prompt from langchain-agent.py line 711
SYSTEM_PROMPT = SystemMessage(
    """Act as an expert Java software developer.
The program has issues after a version upgrade of a dependency.
Try using minimal changes to the code to fix the issues. 
Do not explain your actions or ask questions, just provide diffs that always adhere to the rules.
When you think you are done, reply with the diff that fixes the issues, after that a final verification step will happen and the conversation will be ended if it was successful. If not you get the error back.

# CRITICAL CONSTRAINT:
**DO NOT CHANGE VERSIONS OF EXISTING DEPENDENCIES IN pom.xml.**
The dependency version upgrades in pom.xml are intentional and must be kept.
You MUST adapt the Java source code to work with the NEW dependency versions.
Reverting dependency versions is NOT an acceptable solution.

However, you CAN MODIFY pom.xml to ADD NEW dependencies if needed to fix compilation issues.
For example, you may need to add missing transitive dependencies that were removed in version upgrades.
When adding dependencies:
- ALWAYS use the verify_maven_dependency tool to verify the version exists on Maven Central BEFORE adding it to pom.xml
- Add complete <dependency> blocks with <groupId>, <artifactId>, and <version> tags
- Place new dependencies in the <dependencies> section
- Do NOT modify or remove existing dependency versions
- Only ADD new dependencies, never change or remove existing ones

# File editing rules:
Return edits similar to unified diffs that `diff -U0` would produce.
The diff has to be in a markdown code block, like this: ```diff ```.

Make sure you include the first 2 lines with the file paths.
Don't include timestamps with the file paths.

Start each hunk of changes with a `@@ ... @@` line.
Don't include line numbers like `diff -U0` does.
The user's patch tool doesn't need them.

The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
Make sure you mark all new or modified lines with `+`.
Don't leave out any lines or the diff patch won't apply correctly.
Dont add in new comments or change existing comments.
Make sure the diff is minimal and only includes the changes needed to fix the issue plus at least one context line so the tool can apply the diff correctly.

Indentation matters in the diffs!

Start a new hunk for each section of the file that needs changes.
Dont include unnescessary context, but include at least one line of it.
If no context is included, the tool will try to apply the changes at the end of the line.

Only output hunks that specify changes with `+` or `-` lines.
Skip any hunks that are entirely unchanging ` ` lines.

Output hunks in whatever order makes the most sense.
Hunks don't need to be in any particular order.

When editing a function, method, loop, etc use a hunk to replace the *entire* code block.
Delete the entire existing version with `-` lines and then add a new, updated version with `+` lines.
This will help you generate correct code and correct diffs.

To make a new file, show a diff from `--- /dev/null` to `+++ path/to/new/file.ext`.
"""
)


class MessagesState(TypedDict):
    """State for the agent workflow"""
    messages: Annotated[list, add_messages]
    proposed_diff: str | None  # Store the diff that was validated


from langchain_groq import ChatGroq

def build_workflow(llm, tools, output_path: str):
    """Build the LangGraph workflow"""
    
    # Create tool executor
    tool_executor = ToolExecutor(tools)
    
    def call_model(state: MessagesState):
        messages = state["messages"]
        
        # Add system message with tool descriptions
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.description}" 
            for tool in tools
        ])
        
        system_msg = f"""You have access to these tools:
{tool_descriptions}

To use a tool, respond ONLY with JSON in this format:
{{"tool": "tool_name", "args": {{"param": "value"}}}}

When you have a diff ready to test, provide it ONLY as a markdown code block starting with ```diff - do NOT wrap it in JSON.
"""
        
        messages_with_tools = [{"role": "system", "content": system_msg}] + messages
        response = llm.invoke(messages_with_tools)
        
        # Parse JSON tool calls from content if present
        content = response.content.strip() if hasattr(response, 'content') else str(response)
        
        # Check if it's a JSON tool request
        if content.startswith("{") and '"tool"' in content:
            try:
                # Extract JSON (might have extra text after)
                json_end = content.find("}")
                if json_end != -1:
                    json_str = content[:json_end+1]
                    tool_request = json.loads(json_str)
                    
                    # Convert to proper tool call format
                    tool_call = {
                        "name": tool_request["tool"],
                        "args": tool_request.get("args", {}),
                        "id": "".join(random.choices(string.ascii_uppercase + string.digits, k=9))
                    }
                    
                    # Create AIMessage with tool_calls
                    if not hasattr(response, 'tool_calls'):
                        response.tool_calls = []
                    response.tool_calls = [tool_call]
                    
                    print(f"[DEBUG] Parsed tool call: {tool_request['tool']}")
            except Exception as e:
                print(f"[DEBUG] Failed to parse tool call: {e}")
        
        return {"messages": [response]}
    
    def call_tools(state: MessagesState):
        """Execute tool calls"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # Execute each tool call
        outputs = []
        for tool_call in last_message.tool_calls:
            print(f"[AGENT] Executing tool: {tool_call['name']}")
            tool_invocation = ToolInvocation(
                tool=tool_call["name"],
                tool_input=tool_call["args"]
            )
            try:
                result = tool_executor.invoke(tool_invocation)
                outputs.append(
                    ToolMessage(
                        content=json.dumps(result) if not isinstance(result, str) else result,
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"]
                    )
                )
            except Exception as e:
                print(f"[ERROR] Tool execution failed: {e}")
                outputs.append(
                    ToolMessage(
                        content=f"Error executing tool: {str(e)}",
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"]
                    )
                )
        
        return {"messages": outputs}
    
    def compile_agent(state: MessagesState):
        """Compile agent node to test the proposed fix"""
        print("[AGENT] Compiling")
        messages = state["messages"]
        last_message = messages[-1]

        # Debug: Print what the agent said
        content = last_message.content if hasattr(last_message, 'content') else str(last_message)
        print(f"[DEBUG] Last message content: {content[:200]}...")
        
        # Check if message has actual diff content
        if "```diff" not in content:
            print("[DEBUG] No diff found in message, going back to agent")
            return {"messages": messages}
        
        # SAFETY CHECK: Allow adding dependencies to pom.xml, but reject version changes
        if "pom.xml" in content.lower():
            # Check if diff contains version changes (lines with <version> being removed or modified)
            if "<version>" in content and "-" in content:
                # Look for lines that remove or change version tags
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip().startswith('-') and '<version>' in line:
                        print(f"[AGENT] REJECTED: Diff attempts to change existing dependency version in pom.xml")
                        error_message = AIMessage(
                            content=f"ERROR: You attempted to CHANGE an existing dependency version in pom.xml. This is FORBIDDEN.\n"
                                    f"The dependency version upgrades are intentional and MUST be kept.\n"
                                    f"You MUST fix the Java source code to work with the NEW dependency versions.\n\n"
                                    f"However, you MAY ADD new dependencies (with <dependency> tags) if needed.\n"
                                    f"Just don't modify existing <version> tags."
                        )
                        return {"messages": [error_message]}
            print("[AGENT] Allowing pom.xml modification (appears to be adding new dependencies)")

        tool_name = "compile_maven_stateful"
            
        tool_call = ToolCall(
            name=tool_name,
            args={"diff": content},
            id="".join(random.choices(string.ascii_uppercase + string.digits, k=9))
        )
        
        # Create tool invocation
        tool_invocation = ToolInvocation(
            tool=tool_name,
            tool_input=tool_call["args"]
        )
        
        try:
            print("[AGENT] Running Maven compilation with proposed diff...")
            tool_result = tool_executor.invoke(tool_invocation)
            
            # Format the result more clearly for the LLM
            if isinstance(tool_result, dict):
                compilation_succeeded = tool_result.get("compilation_has_succeeded", False)
                test_succeeded = tool_result.get("test_has_succeeded", False)
                error_text = tool_result.get("error_text", "")
                compile_errors = tool_result.get("compile_error_details", {})
                
                print(f"[DEBUG] Compilation result: succeeded={compilation_succeeded}, errors={len(compile_errors)} files with errors")
                print(f"[DEBUG] Error text length: {len(error_text)} chars")
                if error_text:
                    print(f"[DEBUG] First 500 chars of error_text: {error_text}")
                
                if compilation_succeeded and test_succeeded:
                    result_content = f"Compilation and Testing successful: The diff was applied successfully and all tests passed."
                else:
                    # Format error message clearly
                    error_msg_parts = []
                    error_msg_parts.append(f"Compilation {'succeeded' if compilation_succeeded else 'FAILED'}")
                    error_msg_parts.append(f"Tests {'succeeded' if test_succeeded else 'FAILED'}")
                    
                    # ALWAYS include error_text if compilation failed
                    if error_text:
                        error_msg_parts.append(f"\nMaven Error Output:\n{error_text}")
                    else:
                        error_msg_parts.append("\n⚠️ No error output captured from Maven")
                    
                    if compile_errors:
                        error_msg_parts.append(f"\nParsed errors in {len(compile_errors)} file(s):")
                        for file_path, line_errors in compile_errors.items():
                            error_msg_parts.append(f"\n{file_path}:")
                            for line_no, error_info in line_errors.items():
                                error_texts = error_info.get('error_texts', [])
                                for err in error_texts:
                                    error_msg_parts.append(f"  Line {line_no}: {err}")
                    
                    result_content = "\n".join(error_msg_parts)
                
                result_message = ToolMessage(
                    content=result_content,
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"]
                )
            else:
                result_message = ToolMessage(
                    content=json.dumps(tool_result) if not isinstance(tool_result, str) else tool_result,
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"]
                )
        except Exception as e:
            print(f"[ERROR] Compilation failed: {e}")
            import traceback
            traceback.print_exc()
            result_message = ToolMessage(
                content=f"Error executing compilation: {str(e)}",
                name=tool_call["name"],
                tool_call_id=tool_call["id"]
            )
        
        # Return both the message and the stored diff
        print(f"[DEBUG] Storing proposed_diff in state: {len(content)} chars")
        return {"messages": [result_message], "proposed_diff": content}
    
    def should_continue(state: MessagesState) -> Literal["tools", "compile_agent"]:
        """Routing logic - copy from langchain-agent.py line 782"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # Save chat log
        if output_path:
            try:
                with open(os.path.join(output_path, "chat_log.txt"), "w", encoding="utf-8") as f:
                    for m in messages:
                        if hasattr(m, 'pretty_repr'):
                            f.write(m.pretty_repr() + "\n\n")
                        else:
                            f.write(str(m) + "\n\n")
            except Exception as e:
                print(f"[WARN] Could not save chat log: {e}")
        
        # Check if LLM wants to use a tool
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            print("[AGENT] Routing to tools")
            return "tools"
        
        print("[AGENT] Routing to compile agent")
        return "compile_agent"
    
    def should_improve_non_test_diff(state: MessagesState) -> Literal["agent", END]:
        """Check if compilation succeeded - copy from langchain-agent.py line 800"""
        messages = state["messages"]
        last_message = messages[-1]
        
        content = last_message.content if hasattr(last_message, 'content') else str(last_message)
        
        if "Compilation and Testing successful:" in content:
            print("[AGENT] Compilation and Testing successful")
            return END
        try:
            parsed = json.loads(content)
            if parsed.get("compilation_has_succeeded") and parsed.get("test_has_succeeded"):
                print("[AGENT] Compilation and Testing successful")
                return END
        except:
            pass
        
        print("[AGENT] Back to Agent")
        return "agent"
    
    # Build graph - copy from langchain-agent.py line 918
    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", call_tools)
    workflow.add_node("compile_agent", compile_agent)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_conditional_edges("compile_agent", should_improve_non_test_diff)
    workflow.add_conditional_edges("tools", should_improve_non_test_diff)
    
    checkpointer = SqliteSaver.from_conn_string(":memory:")
    return workflow.compile(checkpointer=checkpointer)