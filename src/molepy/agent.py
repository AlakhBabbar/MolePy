import json
from pathlib import Path
from typing import Dict, Any, List
from molepy import tools, schemas, prompts, llm

TOOL_MAP = {
    "get_repo_tree": tools.get_repo_tree,
    "read_file": tools.read_file,
    "search_codebase": tools.search_codebase,
    "edit_file_lines": tools.edit_file_lines,
    "run_shell_command": tools.run_shell_command,
    "insert_code": tools.insert_code,
}

def execute_tool_call(tool_name: str, arguments: Dict[str, Any], repo_path: str) -> str:
    func = TOOL_MAP.get(tool_name)
    if not func:
        return f"Error: Tool '{tool_name}' is not recognized."
    
    # Force arguments to be a dictionary if the LLM returns null
    if not isinstance(arguments, dict):
        arguments = {}
    
    arguments["repo_path"] = repo_path
    try:
        return func(**arguments)
    except Exception as e:
        return f"Error executing tool '{tool_name}': {e}"

def prune_history(messages: List[Any], max_output_length: int = 800) -> List[Any]:
    """Truncates old tool execution outputs in history to preserve context window."""
    pruned = []
    total = len(messages)
    
    for idx, msg in enumerate(messages):
        if idx < 2 or idx >= total - 6:
            pruned.append(msg)
            continue
        
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
        content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
        
        if role == "tool" and content and len(content) > max_output_length:
            tool_id = msg.get("tool_call_id") if isinstance(msg, dict) else getattr(msg, "tool_call_id", None)
            tool_name = msg.get("name") if isinstance(msg, dict) else getattr(msg, "name", None)
            
            pruned.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "name": tool_name,
                "content": content[:250] + "\n... [Previous tool output truncated to save context window]"
            })
        else:
            pruned.append(msg)
            
    return pruned

def run_agent(product_request: str, repo_path: str, max_iterations: int = 25):
    print(f"\n🚀 [molepy] Starting agent for request: '{product_request}'")
    print(f"📁 Target Repository: {repo_path}\n" + "-" * 60)

    messages: List[Any] = [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {"role": "user", "content": product_request}
    ]

    # --- NEW: LONG-TERM MEMORY STATE ---
    read_files_registry = set()
    agent_scratchpad = ""

    for iteration in range(1, max_iterations + 1):
        print(f"\n🔄 [Iteration {iteration}/{max_iterations}] Querying LLM...")
        
        active_history = prune_history(messages)
        
        # --- NEW: DYNAMIC BOTTOM-ANCHORED CONTEXT ---
        reminder_content = (
            "REMINDER: You MUST call `read_file` to inspect line numbers before modifying a file.\n"
            "If you read a file, immediately use `update_scratchpad` to save the line numbers you need before they are lost from memory.\n\n"
        )
        
        if read_files_registry:
            reminder_content += f"📂 Files you have already inspected: {', '.join(read_files_registry)}\n"
            
        if agent_scratchpad:
            reminder_content += f"🧠 YOUR SCRATCHPAD (Permanent Memory):\n{agent_scratchpad}\n"

        temp_messages = list(active_history)
        temp_messages.append({
            "role": "system",
            "content": reminder_content
        })

        try:
            # Note: Ensure parallel_tool_calls=False is still set in llm.py!
            response_message = llm.call_llm(temp_messages, tools=schemas.TOOLS_SCHEMA)
        except Exception as e:
            error_str = str(e)
            if "tool_use_failed" in error_str or "400" in error_str:
                print(f"\n⚠️ [molepy] LLM JSON formatting error caught. Forcing self-correction...")
                messages.append({
                    "role": "user",
                    "content": f"Tool validation error: {error_str}. Fix your JSON formatting (do not escape dollar signs) and try again."
                })
                continue
            else:
                print(f"\n❌ [molepy] Fatal LLM API Call Error: {e}")
                break

        messages.append(response_message)

        if getattr(response_message, "content", None):
            print("\n🤖 [Agent Thought / Plan]:")
            print(response_message.content)

        tool_calls = getattr(response_message, "tool_calls", None)
        if not tool_calls:
            print("\n✅ [molepy] Task completed successfully!")
            break

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            if "<|" in function_name:
                function_name = function_name.split("<|")[0].strip()

            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                args = {}

            print(f"\n🛠️  [Tool Call]: {function_name}({json.dumps(args)})")
            
            # --- GUARDRAILS & MEMORY MANAGEMENT ---
            if function_name == "read_file" and "file_path" in args:
                target_file = (Path(repo_path) / args["file_path"]).resolve()
                read_files_registry.add(str(target_file))

            # Handle Scratchpad logic in-memory without a separate tools.py function
            if function_name == "update_scratchpad":
                new_note = args.get("notes", "")
                agent_scratchpad += f"- {new_note}\n"
                tool_result = "Note successfully saved to permanent scratchpad."
                print(f"📋 [Tool Result]: {tool_result}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": tool_result
                })
                continue # Skip standard execute_tool_call

            if function_name in ["edit_file_lines", "insert_code"] and "file_path" in args:
                target_file = (Path(repo_path) / args["file_path"]).resolve()
                if target_file.exists() and str(target_file) not in read_files_registry:
                    tool_result = (
                        f"❌ Error: Edit rejected. You MUST call 'read_file' on '{args['file_path']}' "
                        "first to inspect its exact line numbers before editing."
                    )
                    print(f"📋 [Tool Result]: {tool_result}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": tool_result
                    })
                    continue 

            # Standard Tool Execution
            tool_result = execute_tool_call(function_name, args, repo_path)
            logged_result = tool_result if len(tool_result) < 300 else tool_result[:300] + "... (truncated)"
            print(f"📋 [Tool Result]: {logged_result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": tool_result
            })
    else:
        print(f"\n⚠️ [molepy] Reached maximum iteration limit ({max_iterations}). Stopping.")