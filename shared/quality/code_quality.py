"""Code quality assessment system."""

import ast
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
from pathlib import Path

# Optional external tools; fall back gracefully if not installed
try:  # radon for complexity/maintainability
    import radon.complexity as radon_cc  # type: ignore
    import radon.metrics as radon_metrics  # type: ignore
except Exception:  # pragma: no cover - optional dep
    radon_cc = None  # type: ignore
    radon_metrics = None  # type: ignore

try:  # pylint for lint scoring
    from pylint.lint import Run  # type: ignore
    from pylint.reporters import JSONReporter  # type: ignore
except Exception:  # pragma: no cover - optional dep
    Run = None  # type: ignore
    JSONReporter = None  # type: ignore

try:  # black for formatting score
    from black import FileMode, format_str  # type: ignore
except Exception:  # pragma: no cover - optional dep
    FileMode = None  # type: ignore
    format_str = None  # type: ignore

logger = logging.getLogger(__name__)

@dataclass
class QualityMetrics:
    """Holds various code quality metrics."""
    
    cyclomatic_complexity: float
    maintainability_index: float
    code_to_comment_ratio: float
    line_length_score: float
    naming_convention_score: float
    error_handling_score: float
    test_coverage: Optional[float]
    lint_score: float
    formatting_score: float
    overall_score: float

class CodeQualityAnalyzer:
    """Analyzes Python code for various quality metrics."""

    def __init__(self):
        """Initialize the analyzer."""
        self.logger = logging.getLogger(__name__)

    def analyze(self, code: str) -> QualityMetrics:
        """Analyze code and return quality metrics.
        
        Args:
            code: Python source code to analyze
            
        Returns:
            QualityMetrics object with various scores
        """
        try:
            # Parse the code
            tree = ast.parse(code)
            
            # Get individual metrics
            cc_score = self._get_complexity_score(code)
            mi_score = self._get_maintainability_score(code)
            comment_score = self._get_comment_ratio_score(tree)
            length_score = self._get_line_length_score(code)
            naming_score = self._get_naming_score(tree)
            error_score = self._get_error_handling_score(tree)
            lint_score = self._get_lint_score(code)
            format_score = self._get_formatting_score(code)
            
            # Calculate overall score (weighted average)
            weights = {
                'complexity': 0.2,
                'maintainability': 0.2,
                'comments': 0.1,
                'line_length': 0.1,
                'naming': 0.1,
                'error_handling': 0.1,
                'lint': 0.1,
                'formatting': 0.1
            }
            
            scores = {
                'complexity': cc_score,
                'maintainability': mi_score,
                'comments': comment_score,
                'line_length': length_score,
                'naming': naming_score,
                'error_handling': error_score,
                'lint': lint_score,
                'formatting': format_score
            }
            
            overall = sum(score * weights[metric] for metric, score in scores.items())
            
            return QualityMetrics(
                cyclomatic_complexity=cc_score,
                maintainability_index=mi_score,
                code_to_comment_ratio=comment_score,
                line_length_score=length_score,
                naming_convention_score=naming_score,
                error_handling_score=error_score,
                test_coverage=None,  # Would require running tests
                lint_score=lint_score,
                formatting_score=format_score,
                overall_score=overall
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing code quality: {e}")
            # Return minimum scores if analysis fails
            return QualityMetrics(
                cyclomatic_complexity=0.0,
                maintainability_index=0.0,
                code_to_comment_ratio=0.0,
                line_length_score=0.0,
                naming_convention_score=0.0,
                error_handling_score=0.0,
                test_coverage=None,
                lint_score=0.0,
                formatting_score=0.0,
                overall_score=0.0
            )

    def _get_complexity_score(self, code: str) -> float:
        """Calculate complexity score (0-1) based on cyclomatic complexity."""
        try:
            if radon_cc is None:
                return 0.0
            # Get average complexity across functions
            complexity = radon_cc.cc_visit(code)
            if not complexity:
                return 1.0  # Perfect score for very simple code
                
            avg_cc = sum(item.complexity for item in complexity) / len(complexity)
            
            # Convert to 0-1 score (lower complexity is better)
            # Using a sigmoid-like curve centered at CC=10
            # Score = 1 for CC <= 5
            # Score = 0.5 for CC = 10
            # Score approaches 0 for CC > 15
            if avg_cc <= 5:
                return 1.0
            elif avg_cc >= 15:
                return 0.0
            else:
                return 1 - ((avg_cc - 5) / 10)
                
        except Exception as e:
            self.logger.error(f"Error calculating complexity score: {e}")
            return 0.0

    def _get_maintainability_score(self, code: str) -> float:
        """Calculate maintainability score (0-1) based on Halstead metrics."""
        try:
            if radon_metrics is None:
                return 0.0
            # Get maintainability index
            mi_score = radon_metrics.mi_visit(code, multi=True)
            if not mi_score:
                return 1.0
                
            # Convert 0-100 score to 0-1
            return min(max(mi_score / 100.0, 0.0), 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating maintainability score: {e}")
            return 0.0

    def _get_comment_ratio_score(self, tree: ast.AST) -> float:
        """Calculate comment ratio score (0-1)."""
        try:
            # Count number of docstrings and inline comments
            comment_count = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                    if ast.get_docstring(node):
                        comment_count += 1
                        
            # Count total number of functions and classes
            func_class_count = len([n for n in ast.walk(tree) 
                                  if isinstance(n, (ast.FunctionDef, ast.ClassDef))])
            
            if func_class_count == 0:
                return 1.0  # Perfect score for very simple code
                
            # Calculate ratio of documented to total
            ratio = comment_count / func_class_count
            
            # Convert to score (0.8 ratio = perfect score)
            return min(ratio / 0.8, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating comment ratio score: {e}")
            return 0.0

    def _get_line_length_score(self, code: str) -> float:
        """Calculate line length score (0-1)."""
        try:
            lines = code.splitlines()
            if not lines:
                return 1.0
                
            # Count lines exceeding PEP 8 limit (79 chars)
            long_lines = sum(1 for line in lines if len(line.strip()) > 79)
            
            # Convert to score (no long lines = perfect score)
            ratio = 1 - (long_lines / len(lines))
            return max(ratio, 0.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating line length score: {e}")
            return 0.0

    def _get_naming_score(self, tree: ast.AST) -> float:
        """Calculate naming convention score (0-1)."""
        try:
            violations = 0
            total = 0
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Name)):
                    total += 1
                    # Safely derive the identifier name for different node types
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        name = getattr(node, "name", None)
                    elif isinstance(node, ast.Name):
                        name = getattr(node, "id", None)
                    else:
                        name = None
                    if not isinstance(name, str):
                        # If name is not a string, skip checks for this node
                        # but keep it counted in total to avoid bias
                        continue
                    
                    # Check naming conventions
                    if isinstance(node, ast.ClassDef):
                        if not name[0].isupper() or '_' in name:
                            violations += 1
                    elif isinstance(node, ast.FunctionDef):
                        if not name.islower() or not re.match(r'^[a-z_][a-z0-9_]*$', name):
                            violations += 1
                    elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                        if not re.match(r'^[a-z_][a-z0-9_]*$', name):
                            violations += 1
            
            if total == 0:
                return 1.0
                
            # Convert to score
            ratio = 1 - (violations / total)
            return max(ratio, 0.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating naming score: {e}")
            return 0.0

    def _get_error_handling_score(self, tree: ast.AST) -> float:
        """Calculate error handling score (0-1)."""
        try:
            # Count try blocks and potential error sources
            try_blocks = len([n for n in ast.walk(tree) if isinstance(n, ast.Try)])
            
            # Count operations that should have error handling
            risky_ops = len([n for n in ast.walk(tree) if isinstance(n, (
                ast.Call, ast.Attribute, ast.Subscript, ast.Index,
                ast.Div, ast.FloorDiv
            ))])
            
            if risky_ops == 0:
                return 1.0
                
            # Calculate ideal number of try blocks (1 per 5 risky operations)
            ideal_try_blocks = risky_ops / 5
            
            # Score based on how close to ideal
            ratio = min(try_blocks / ideal_try_blocks, 1.0) if ideal_try_blocks > 0 else 1.0
            return max(ratio, 0.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating error handling score: {e}")
            return 0.0

    def _get_lint_score(self, code: str) -> float:
        """Calculate lint score (0-1) using pylint."""
        try:
            if Run is None or JSONReporter is None:
                return 0.0
            # Create temporary file for pylint
            tmp_path = Path("temp_code.py")
            tmp_path.write_text(code)
            
            # Run pylint
            reporter = JSONReporter()
            Run(['temp_code.py'], reporter=reporter, exit=False)
            
            # Clean up
            tmp_path.unlink()
            
            # Convert pylint score (0-10) to 0-1
            if hasattr(reporter, 'score'):
                return max(getattr(reporter, 'score', 0.0) / 10.0, 0.0)
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating lint score: {e}")
            return 0.0

    def _get_formatting_score(self, code: str) -> float:
        """Calculate formatting score (0-1) using black."""
        try:
            # Try to format with black
            try:
                if format_str is None or FileMode is None:
                    return 0.0
                formatted = format_str(code, mode=FileMode())
                
                # Compare original to formatted
                if formatted.strip() == code.strip():
                    return 1.0
                    
                # Calculate similarity ratio
                orig_lines = set(code.splitlines())
                formatted_lines = set(formatted.splitlines())
                
                if not orig_lines:
                    return 1.0
                    
                # Score based on how many lines needed changing
                unchanged = len(orig_lines.intersection(formatted_lines))
                ratio = unchanged / len(orig_lines)
                return max(ratio, 0.0)
                
            except Exception:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error calculating formatting score: {e}")
            return 0.0
