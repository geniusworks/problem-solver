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


def _parses(code: str) -> bool:
    """Whether the code is already syntactically valid Python."""
    try:
        compile(code, "<string>", "exec")
        return True
    except SyntaxError:
        return False


def _format_valid(code: str) -> Tuple[str, bool]:
    """Cosmetically format code that is already valid.

    black and autopep8 are parser-based, so unlike the regex repairs they
    cannot corrupt the program. If either fails, the original valid code is
    returned rather than treating it as a formatting failure -- style is not
    worth discarding a working solution over.
    """
    try:
        formatted = autopep8.fix_code(code, options={"aggressive": 1})
        if not _parses(formatted):
            formatted = code
    except Exception as e:
        logger.warning("autopep8 failed: %s", e)
        formatted = code

    try:
        mode = black.Mode(target_versions={black.TargetVersion.PY39}, line_length=88)
        blacked = black.format_str(formatted, mode=mode)
        if _parses(blacked):
            return blacked, True
    except Exception as e:
        logger.debug("black formatting skipped: %s", e)

    return formatted, True


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

        # Only attempt the heuristic repairs below when the code does not
        # already parse.
        #
        # Those repairs are regex and string substitutions that cannot tell
        # context from content, so on valid input they corrupt more than they
        # fix: unescaping turns a literal "\n" inside a string into a real
        # newline, and the f-string rewrite below rewraps f"..." as f'...',
        # which breaks any f-string containing an apostrophe. The harness then
        # blamed the model for the resulting SyntaxError.
        #
        # Repairing malformed output is worth attempting. Repairing
        # well-formed output is pure downside.
        if _parses(code):
            return _format_valid(code)

        # Debug-print stripping was removed here, and must not come back in a
        # line-based form.
        #
        # It deleted any line containing "print(" inside solve(), which silently
        # destroys valid Python whenever the print is the only statement in its
        # block -- `if cond:\n    print(x)` becomes `if cond:` with no body -- or
        # whenever the call spans several lines. The result was a SyntaxError
        # attributed to the model: the harness corrupted correct output and then
        # scored the model as having failed, systematically understating it.
        #
        # Nothing needs stripping anyway. The answer is read from the last
        # non-empty line of stdout (see _last_nonempty_line in shared/execution),
        # so debug output printed before the answer is already harmless.

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
