
from typing import Any, Dict, List, Union

from langchain_core.messages.tool import ToolCall
from langchain.load import loads, load


inverse_lm_mapping = {v: k for k, v in lm_mapping.items()}

# print(short_to_full_hash)

unique_test = commit_df_short[commit_df_short['Type'] == 'Test']
# unique_test = unique_test[unique_test['Count'] == 1]

# unique_test['Hash'] = unique_test['Hash'].apply(lambda x: short_to_full_hash.get(x, None))

unique_test['Model'] = unique_test['Hash'].apply(lambda x: list(test_intersections.get(x, None))[0])

# claude_unique_test = unique_test[unique_test['Model'].str.contains("claude-3.5-sonnet")]

hashes = list(unique_test['Hash'])

def extract_tool_call_info(tool_message: ToolMessage, ai_message: AIMessage) -> ToolCall:
    # Extract tool call information from the ToolMessage
    # Adjust this function based on the actual structure of your ToolMessage
    # content = json.loads(tool_message)
    return ToolCall(
        id=tool_message.tool_call_id,
        name=tool_message.name,
        args={"diff": ai_message.content}
    )


# .venv/lib/python3.12/site-packages/langchain_community/adapters/openai.py
# elif isinstance(message, AIMessage):
#         message_dict = {"role": "assistant", "content": message.content}
#         if message.tool_calls and len(message.tool_calls) > 0:
#             message_dict["content"] = None
#             message_dict["tool_calls"] = [{"id": tc["id"], "function": {"arguments":json.dumps(tc["args"]), "name":tc["name"] }, "type":"function"} for tc in message.tool_calls]
#             # If tool calls only, content is None not empty string
#             if message_dict["content"] == "":
#                 message_dict["content"] = None


def process_messages(messages: List[Union[AIMessage, ToolMessage]]) -> List[Union[AIMessage, ToolMessage]]:
    processed_messages = []
    i = 0
    while i < len(messages):
        message = messages[i]
        if isinstance(message, AIMessage):
            # Check if the next message is a tool message
            if i + 1 < len(messages) and isinstance(messages[i + 1], ToolMessage):
                next_message = messages[i + 1]
                if "Failed to prepare diffs" in next_message.content:
                    # print("Skipping failed diff")
                    # Skip both current and next message
                    i += 2
                    continue
                else:
                    print("Processing tool call", next_message.tool_call_id)
                    # If it's a valid tool message, include both messages
                    processed_messages.append(message)
                    processed_messages.append(next_message)
                    i += 2
                    continue
        # If not an AIMessage followed by a ToolMessage, just add the current message
        processed_messages.append(message)
        i += 1
    return processed_messages


examples = defaultdict(dict)
final_tuning_messages = list()
for hash_value in hashes:
    out_path = Path(f"dataset/{hash_value}/out/{inverse_lm_mapping.get(model.replace('agent_', ''))}_augmented_prompt")
    with open(os.path.join(out_path,"chat_log.jsonl"), "r", encoding="utf-8") as f:
        messages = [loads(line) for line in f]
        if isinstance(messages[-1], ToolMessage):
            messages.append(AIMessage("Done."))
        messages = process_messages(messages)
        if len(messages) == 3:
            print("Weirrd")
            continue
        examples[hash_value] = {"messages": messages}
        final_tuning_messages.append({"messages": messages})
        

from langchain.adapters import openai as openai_adapter


finetuning_messages = openai_adapter.convert_messages_for_finetuning(final_tuning_messages)

with open("finetuning_messages.jsonl", "w") as f:
    for group in finetuning_messages:
        f.write((json.dumps({"messages": group}) + "\n"))
unique_test