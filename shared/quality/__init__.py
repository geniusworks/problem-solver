"""Code quality evaluation package."""

# code_quality is the implementation the solver actually uses. A second, unused
# CodeQualityAnalyzer lived in analyzer.py and was removed; its "security scanning"
# and error counts were hardcoded zeros.
from .code_quality import CodeQualityAnalyzer, QualityMetrics
from .rules import RuleViolation, CodeQualityRule

__all__ = ["CodeQualityAnalyzer", "QualityMetrics", "RuleViolation", "CodeQualityRule"]
