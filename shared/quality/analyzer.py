"""Code quality analysis module."""

# Standard library imports
import ast
import logging
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

# Third-party imports
import pylint.lint
from pylint.reporters import JSONReporter

logger = logging.getLogger(__name__)


@dataclass
class StyleMetrics:
    """Style-related code quality metrics."""

    style_violations: int = 0
    naming_violations: int = 0
    whitespace_violations: int = 0
    black_compliant: bool = False
    comment_ratio: float = 0.0


@dataclass
class QualityMetrics:
    """Code quality metrics."""

    style_metrics: StyleMetrics = StyleMetrics()
    complexity_metrics: Dict[str, float] = None
    error_count: int = 0
    warning_count: int = 0
    type_issues: int = 0
    security_issues: int = 0
    loc: int = 0

    def __post_init__(self):
        if self.complexity_metrics is None:
            self.complexity_metrics = {
                "cyclomatic": 0.0,
                "cognitive": 0.0,
                "maintainability": 0.0,
            }


class CodeQualityAnalyzer:
    """Analyzes code quality using multiple tools."""

    def analyze(self, code: str) -> QualityMetrics:
        """Analyze code quality and return metrics."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py") as temp_file:
            temp_file.write(code)
            temp_file.flush()

            style_metrics = self._get_style_metrics(temp_file.name)
            complexity_metrics = self._get_complexity_metrics(code)

            return QualityMetrics(
                style_metrics=style_metrics,
                complexity_metrics=complexity_metrics,
                error_count=0,  # TODO: Implement error counting
                warning_count=0,  # TODO: Implement warning counting
                type_issues=0,  # TODO: Implement type issue detection
                security_issues=0,  # TODO: Implement security scanning
                loc=len(code.splitlines()),
            )

    def _run_pylint(self, code: str) -> List[Dict[str, Any]]:
        """Run pylint on code and return issues."""
        try:
            reporter = JSONReporter()
            args = ["--output-format=json", code]
            pylint.lint.Run(args, reporter=reporter)
            return reporter.messages
        except Exception as e:
            logger.error("Error running pylint: %s", str(e))
            return []

    def _get_style_issues(self, code: str) -> List[Dict[str, Any]]:
        """Get style-related issues from pylint."""
        try:
            reporter = JSONReporter()
            args = ["--disable=all", "--enable=C,R", "--output-format=json", code]
            pylint.lint.Run(args, reporter=reporter)
            return reporter.messages
        except Exception as e:
            logger.error("Error getting style issues: %s", str(e))
            return []

    def _get_maintainability_issues(self, file_path: str) -> List[Dict[str, Any]]:
        """Get maintainability issues from pylint."""
        try:
            reporter = JSONReporter()
            args = [file_path, "--output-format=json"]
            pylint.lint.Run(args, reporter=reporter)
            return [
                msg for msg in reporter.messages if msg["type"] in ("error", "warning")
            ]
        except Exception as e:
            logger.error("Error getting maintainability issues: %s", str(e))
            return []

    def _get_style_metrics(self, file_path: str) -> StyleMetrics:
        """Get style metrics."""
        style_issues = self._get_style_issues(file_path)
        black_compliant = self._check_black_compliance(open(file_path).read())
        comment_ratio = self._get_comment_ratio(open(file_path).read())

        return StyleMetrics(
            style_violations=len(style_issues),
            naming_violations=len(
                [
                    issue
                    for issue in style_issues
                    if "invalid name" in issue["message"].lower()
                ]
            ),
            whitespace_violations=len(
                [
                    issue
                    for issue in style_issues
                    if "trailing whitespace" in issue["message"].lower()
                ]
            ),
            black_compliant=black_compliant,
            comment_ratio=comment_ratio,
        )

    def _get_complexity_metrics(self, code: str) -> Dict[str, float]:
        """Calculate code complexity metrics."""
        try:
            tree = ast.parse(code)
            return {
                "cyclomatic": self._get_complexity(tree),
                "cognitive": self._get_cognitive_complexity(tree),
                "maintainability": self._get_maintainability_index(code),
            }
        except Exception as e:
            logger.error("Error calculating complexity metrics: %s", str(e))
            return {
                "cyclomatic": 0.0,
                "cognitive": 0.0,
                "maintainability": 0.0,
            }

    def _get_complexity(self, tree: ast.AST) -> float:
        """Calculate cyclomatic complexity."""
        try:
            complexity = 1  # Base complexity
            for node in ast.walk(tree):
                if isinstance(
                    node, (ast.If, ast.While, ast.For, ast.Try, ast.ExceptHandler)
                ):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
            return float(complexity)
        except Exception as e:
            logger.error("Error calculating cyclomatic complexity: %s", str(e))
            return 0.0

    def _get_cognitive_complexity(self, tree: ast.AST) -> float:
        """Calculate cognitive complexity."""
        try:
            complexity = 0
            nesting_level = 0

            def visit_node(node: ast.AST, level: int) -> None:
                nonlocal complexity
                if isinstance(node, (ast.If, ast.While, ast.For)):
                    complexity += level + 1
                for child in ast.iter_child_nodes(node):
                    visit_node(child, level + 1)

            visit_node(tree, nesting_level)
            return float(complexity)
        except Exception as e:
            logger.error("Error calculating cognitive complexity: %s", str(e))
            return 0.0

    def _get_maintainability_index(self, code: str) -> float:
        """Calculate maintainability index."""
        try:
            # Simplified maintainability index calculation
            loc = len(code.splitlines())
            cc = self._get_complexity(ast.parse(code))
            return 100.0 - (cc * 0.25 + loc * 0.05)
        except Exception as e:
            logger.error("Error calculating maintainability index: %s", str(e))
            return 0.0

    def _check_black_compliance(self, code: str) -> bool:
        """Check if code complies with black formatting."""
        try:
            import black

            mode = black.Mode()
            try:
                black.format_str(code, mode=mode)
                return True
            except black.InvalidInput:
                return False
        except Exception as e:
            logger.error("Error checking black compliance: %s", str(e))
            return False

    def _get_comment_ratio(self, code: str) -> float:
        """Calculate ratio of comments to code."""
        try:
            total_lines = len(code.splitlines())
            comment_lines = sum(
                1 for line in code.splitlines() if line.strip().startswith("#")
            )
            return float(comment_lines) / total_lines if total_lines > 0 else 0.0
        except Exception as e:
            logger.error("Error calculating comment ratio: %s", str(e))
            return 0.0
