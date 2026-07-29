import os
import subprocess
import ast
import json
from pathlib import Path

def check_syntax(file_path: Path) -> str | None:
    """
    Checks syntax based on file extension. 
    Returns the error message if invalid, or None if the syntax is valid.
    """
    ext = file_path.suffix.lower()
    
    try:
        if ext == '.py':
            # Python can check its own syntax using the built-in ast module
            source = file_path.read_text(encoding='utf-8')
            ast.parse(source)
            return None
            
        elif ext == '.json':
            # Built-in JSON validation
            source = file_path.read_text(encoding='utf-8')
            json.loads(source)
            return None
            
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            # For JavaScript/TypeScript, we use Node's built-in syntax checker flag (-c)
            result = subprocess.run(
                ['node', '--check', str(file_path)], 
                capture_output=True, 
                text=True
            )
            if result.returncode != 0:
                # Node returns the syntax error in stderr
                return result.stderr.strip()
            return None
            
        else:
            # If it's HTML, CSS, or an unknown language, we skip checking 
            # to avoid false positives and assume it's valid.
            return None
            
    except SyntaxError as e:
        return f"Python Syntax Error: {e}"
    except json.JSONDecodeError as e:
        return f"JSON Format Error: {e}"
    except Exception as e:
        # If node isn't installed or something else fails, fail gracefully
        return None

def get_repo_tree(repo_path: str) -> str:
    """Returns a full tree map of the repository architecture."""
    repo = Path(repo_path).resolve()
    tree_str = f"📦 {repo.name}\n"
    
    for root, dirs, files in os.walk(repo):
        # Exclude noisy directories to save context
        dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', 'dist', 'build']]
        
        level = str(root).replace(str(repo), '').count(os.sep)
        indent = ' ' * 4 * level
        folder_name = Path(root).name
        
        if root != str(repo):
            tree_str += f"{indent}📂 {folder_name}/\n"
            
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            tree_str += f"{subindent}📜 {f}\n"
            
    return tree_str

def read_file(repo_path: str, file_path: str, start_line: int = 1, end_line: int = None) -> str:
    """Reads a file and returns its content with explicit line numbers."""
    target_file = (Path(repo_path) / file_path).resolve()
    
    if not target_file.exists() or not target_file.is_file():
        return f"Error: File {file_path} does not exist."
        
    try:
        lines = target_file.read_text(encoding="utf-8").splitlines()
        total_lines = len(lines)
        
        if start_line < 1:
            start_line = 1
        if end_line is None or end_line > total_lines:
            end_line = total_lines
            
        numbered_lines = [
            f"{i:4d} | {lines[i-1]}" 
            for i in range(start_line, end_line + 1)
        ]
        header = f"--- {file_path} (Lines {start_line}-{end_line} of {total_lines}) ---\n"
        return header + "\n".join(numbered_lines)
    except Exception as e:
        return f"Error reading file: {e}"

def search_codebase(repo_path: str, query: str) -> str:
    """Searches all files for a keyword pattern."""
    results = []
    repo = Path(repo_path).resolve()
    
    for filepath in repo.rglob("*"):
        if any(part in filepath.parts for part in [".git", "node_modules", "__pycache__", "dist", "build"]):
            continue
            
        if filepath.is_file():
            try:
                lines = filepath.read_text(encoding="utf-8").splitlines()
                for i, line in enumerate(lines):
                    if query in line:
                        rel_path = filepath.relative_to(repo)
                        results.append(f"{rel_path}:{i+1}: {line.strip()}")
            except UnicodeDecodeError:
                pass
                
    if not results:
        return f"No results found for '{query}'."
    
    if len(results) > 50:
        return "\n".join(results[:50]) + f"\n...and {len(results) - 50} more results."
    return "\n".join(results)

def insert_code(repo_path: str, file_path: str, line_number: int, new_code: str) -> str:
    target_file = (Path(repo_path) / file_path).resolve()
    if not target_file.exists():
        return f"Error: File {file_path} does not exist."

    try:
        content = target_file.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
        
        replacement = new_code if new_code.endswith("\n") else new_code + "\n"
        idx = max(0, min(len(lines), line_number))
        
        lines.insert(idx, replacement)
        
        # 1. Write the new code
        target_file.write_text("".join(lines), encoding="utf-8")
        
        # 2. Check for syntax errors
        syntax_error = check_syntax(target_file)
        
        # 3. If it broke the code, REVERT and yell at the AI
        if syntax_error:
            target_file.write_text(content, encoding="utf-8") # Revert!
            return (
                f"❌ Edit REJECTED: Your changes introduced a syntax error.\n"
                f"The file has been reverted to its previous state.\n"
                f"Error Details:\n{syntax_error}"
            )
            
        return f"Successfully inserted code after line {line_number} in {file_path}."
    except Exception as e:
        return f"Error inserting code: {e}"

def edit_file_lines(repo_path: str, file_path: str, start_line: int, end_line: int, new_code: str) -> str:
    """Replaces lines start_line through end_line (inclusive) in file_path with new_code."""
    target_file = (Path(repo_path) / file_path).resolve()
    
    if not target_file.exists():
        if start_line <= 1:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(new_code, encoding="utf-8")
            return f"Successfully created new file {file_path}."
        return f"Error: File {file_path} does not exist."

    try:
        content = target_file.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
        
        new_code_lines = new_code.splitlines()
        if len(new_code_lines) > 250:
            return "Error: Edit rejected. Replaced block exceeds 250 lines. Make smaller, surgical edits."

        idx_start = max(0, start_line - 1)
        idx_end = min(len(lines), end_line)
        
        replacement = new_code if new_code.endswith("\n") else new_code + "\n"
        lines[idx_start:idx_end] = [replacement]
        
        target_file.write_text("".join(lines), encoding="utf-8")

        #check syntax error
        syntax_error = check_syntax(target_file)
                
        # If it broke the code, REVERT and yell at the AI
        if syntax_error:
            target_file.write_text(content, encoding="utf-8") # Revert!
            return (
                f"❌ Edit REJECTED: Your changes introduced a syntax error.\n"
                f"The file has been reverted to its previous state.\n"
                f"Error Details:\n{syntax_error}"
            )
        
        return f"Successfully updated lines {start_line}-{end_line} in {file_path}."
    except Exception as e:
        return f"Error editing file: {e}"

def run_shell_command(repo_path: str, command: str) -> str:
    """Runs a shell command inside repo directory."""
    try:
        result = subprocess.run(
            command, shell=True, cwd=repo_path, text=True, capture_output=True
        )
        output = result.stdout + result.stderr
        return output.strip() if output else "Command executed successfully with no output."
    except Exception as e:
        return f"Error running command: {e}"