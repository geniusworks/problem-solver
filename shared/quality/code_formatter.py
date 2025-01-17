"""Code formatting utilities."""

import logging
import re
from typing import Tuple

import autopep8
import black

logger = logging.getLogger(__name__)


def extract_code_block(text: str) -> str:
    """Extract Python code block from text, handling various formats."""
    # Try to find a Python code block
    if match := re.search(r"```(?:python)?\n(.*?)\n```", text, re.DOTALL):
        return match.group(1).strip()

    # If no code block markers, look for Python-like content
    lines = text.strip().split("\n")

    # Find the first line that looks like Python code
    start = 0
    for i, line in enumerate(lines):
        if re.match(r"^(import\s+|from\s+|def\s+|class\s+|#)", line):
            start = i
            break

    # Find the last line that looks like Python code
    end = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if line and not line.startswith(("```", '"""', "'''", "#")):
            end = i + 1
            break

    return "\n".join(lines[start:end])


def format_code(source_code: str) -> Tuple[str, bool]:
    """Format Python code using black and autopep8.

    Args:
        source_code: Python source code to format

    Returns:
        Tuple of (formatted_code, success)
    """
    try:
        # First extract actual code if needed
        code = extract_code_block(source_code)

        # Fix common issues
        code = code.replace("\\n", "\n")  # Fix escaped newlines
        code = code.replace('\\"', '"')  # Fix escaped quotes
        
        # Remove debug prints
        code_lines = code.split('\n')
        filtered_lines = []
        in_solve_function = False
        debug_print = False
        
        for line in code_lines:
            # Track if we're in the solve function
            if line.startswith('def solve('):
                in_solve_function = True
            elif in_solve_function and line and not line[0].isspace():
                in_solve_function = False
                
            # Skip debug prints inside solve function
            if in_solve_function and 'print(' in line and 'return' not in line:
                debug_print = True
                continue
                
            # If this was a multi-line debug print block, skip until we're out
            if debug_print:
                if line.strip() and not line.strip().startswith(('print', 'for', 'if')):
                    debug_print = False
                else:
                    continue
                    
            filtered_lines.append(line)
            
        code = '\n'.join(filtered_lines)
        
        # Fix f-strings with assignment expressions
        def fix_fstring_assignments(match):
            """Fix f-string that contains assignment expressions."""
            content = match.group(1)
            # Replace value=var with str(var)
            content = re.sub(r'value=(\w+)', r'str(\1)', content)
            return f"f'{content}'"
            
        code = re.sub(r'f"([^"]*)"', fix_fstring_assignments, code)
        code = re.sub(r"f'([^']*)'", fix_fstring_assignments, code)

        # Try to fix basic syntax with autopep8
        try:
            fixed_code = autopep8.fix_code(code, options={"aggressive": 1})
        except Exception as e:
            logger.warning("autopep8 failed: %s", str(e))
            fixed_code = code

        # Validate syntax before black formatting
        try:
            compile(fixed_code, '<string>', 'exec')
        except SyntaxError as e:
            logger.warning("Syntax error in code: %s", str(e))
            return code, False

        try:
            # Then try to format with black
            mode = black.Mode(
                target_versions={black.TargetVersion.PY39},
                line_length=88,
                string_normalization=True,
                is_pyi=False,
            )
            formatted_code = black.format_str(fixed_code, mode=mode)
            return formatted_code, True
        except Exception as e:
            logger.warning("black formatting failed: %s", str(e))
            # If black fails, return the autopep8 result
            return fixed_code, True

    except Exception as e:
        logger.warning("Code formatting failed: %s", str(e))
        return source_code, False
