TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_repo_tree",
            "description": "Returns a full architectural tree of the repository. Call this first to understand the structure of the frontend and backend folders.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads file contents with line numbers. Optionally specify start_line and end_line.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to file."},
                    "start_line": {"type": "integer", "description": "Line to start reading (1-indexed). Defaults to 1."},
                    "end_line": {"type": "integer", "description": "Line to stop reading. Defaults to end of file."}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_codebase",
            "description": "Searches all files for a keyword pattern. Useful for finding relationships between backend routes and frontend UI calls.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword pattern to search for."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "insert_code",
            "description": "Inserts code exactly AFTER a specific line number without deleting existing lines or brackets. Best for adding new routes, variables, or functions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to file."},
                    "line_number": {"type": "integer", "description": "The exact line number to insert the new code AFTER."},
                    "new_code": {"type": "string", "description": "The block of new code to insert."}
                },
                "required": ["file_path", "line_number", "new_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file_lines",
            "description": "Replaces a specific line range. Use this ONLY to modify existing logic, not to add completely new blocks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to file."},
                    "start_line": {"type": "integer", "description": "Start line number to replace."},
                    "end_line": {"type": "integer", "description": "End line number to replace."},
                    "new_code": {"type": "string", "description": "The exact new code replacement block."}
                },
                "required": ["file_path", "start_line", "end_line", "new_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell_command",
            "description": "Executes shell commands like 'git status', 'git diff', or test scripts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_scratchpad",
            "description": "Saves important notes, line numbers, and variable names to your permanent working memory. Use this IMMEDIATELY after reading a file so you don't forget its contents when history is pruned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "notes": {"type": "string", "description": "The exact line numbers, architectural details, or logic you need to remember for your edits."}
                },
                "required": ["notes"]
            }
        }
    }
]