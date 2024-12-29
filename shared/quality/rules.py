"""Code quality rules and violations."""

from dataclasses import dataclass
from enum import Enum


class CodeQualityRule(Enum):
    """Types of code quality rules."""

    STYLE = "style"  # PEP 8 and style conventions
    MAINTAINABILITY = "maintainability"  # Code maintainability issues
    COMPLEXITY = "complexity"  # Cyclomatic/cognitive complexity
    TYPE_CHECK = "type_check"  # Type checking issues
    SECURITY = "security"  # Security vulnerabilities
    PERFORMANCE = "performance"  # Performance concerns


@dataclass
class RuleViolation:
    """A violation of a code quality rule."""

    rule: CodeQualityRule
    message: str
    line: int
    severity: str  # 'convention', 'warning', 'error', etc.
