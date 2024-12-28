"""Code quality analysis using multiple tools."""

import ast
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
import subprocess
import json

import pylint.lint
from pylint.reporters import JSONReporter
import radon.complexity as radon_cc
import radon.metrics as radon_metrics
from bandit.core.config import BanditConfig
from bandit.core import manager as bandit_manager
import black
import mypy.api

from .rules import RuleViolation, CodeQualityRule

@dataclass
class QualityMetrics:
    """Metrics from various code quality tools."""
    # Pylint metrics
    pylint_score: float
    style_issues: List[RuleViolation]
    maintainability_issues: List[RuleViolation]
    
    # Complexity metrics
    cyclomatic_complexity: int
    cognitive_complexity: int
    maintainability_index: float
    
    # Type checking
    type_issues: List[RuleViolation]
    
    # Security issues
    security_issues: List[RuleViolation]
    
    # Code style
    is_black_compliant: bool
    
    # Additional metrics
    loc: int
    comment_ratio: float
    test_coverage: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "pylint_score": self.pylint_score,
            "style_issues": [issue.__dict__ for issue in self.style_issues],
            "maintainability_issues": [issue.__dict__ for issue in self.maintainability_issues],
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "cognitive_complexity": self.cognitive_complexity,
            "maintainability_index": self.maintainability_index,
            "type_issues": [issue.__dict__ for issue in self.type_issues],
            "security_issues": [issue.__dict__ for issue in self.security_issues],
            "is_black_compliant": self.is_black_compliant,
            "loc": self.loc,
            "comment_ratio": self.comment_ratio,
            "test_coverage": self.test_coverage
        }

class CodeQualityAnalyzer:
    """Analyzes code quality using multiple tools."""
    
    def __init__(self, max_complexity: int = 10):
        self.max_complexity = max_complexity
    
    def analyze(self, code: str) -> QualityMetrics:
        """Analyze code quality using multiple tools."""
        # Create temporary file for analysis
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py') as temp_file:
            temp_file.write(code)
            temp_file.flush()
            temp_path = Path(temp_file.name)
            
            return QualityMetrics(
                pylint_score=self._run_pylint(temp_path),
                style_issues=self._get_style_issues(temp_path),
                maintainability_issues=self._get_maintainability_issues(temp_path),
                cyclomatic_complexity=self._get_complexity(code),
                cognitive_complexity=self._get_cognitive_complexity(code),
                maintainability_index=self._get_maintainability_index(code),
                type_issues=self._run_mypy(temp_path),
                security_issues=self._run_bandit(temp_path),
                is_black_compliant=self._check_black_compliance(code),
                loc=self._count_lines(code),
                comment_ratio=self._get_comment_ratio(code)
            )
    
    def _run_pylint(self, file_path: Path) -> float:
        """Run Pylint and return score."""
        reporter = JSONReporter()
        pylint.lint.Run(
            [str(file_path)],
            reporter=reporter,
            do_exit=False
        )
        return reporter.data.get('score', 0.0)
    
    def _get_style_issues(self, file_path: Path) -> List[RuleViolation]:
        """Get style-related issues from Pylint."""
        reporter = JSONReporter()
        pylint.lint.Run(
            [str(file_path)],
            reporter=reporter,
            do_exit=False
        )
        
        style_issues = []
        for message in reporter.data.get('messages', []):
            if message['type'] in ('convention', 'refactor'):
                style_issues.append(RuleViolation(
                    rule=CodeQualityRule.STYLE,
                    message=message['message'],
                    line=message['line'],
                    severity=message['type']
                ))
        return style_issues
    
    def _get_maintainability_issues(self, file_path: Path) -> List[RuleViolation]:
        """Get maintainability issues from Pylint."""
        reporter = JSONReporter()
        pylint.lint.Run(
            [str(file_path)],
            reporter=reporter,
            do_exit=False
        )
        
        issues = []
        for message in reporter.data.get('messages', []):
            if message['type'] in ('warning', 'error'):
                issues.append(RuleViolation(
                    rule=CodeQualityRule.MAINTAINABILITY,
                    message=message['message'],
                    line=message['line'],
                    severity=message['type']
                ))
        return issues
    
    def _get_complexity(self, code: str) -> int:
        """Get cyclomatic complexity using Radon."""
        try:
            complexity = radon_cc.cc_visit(code)
            return max((item.complexity for item in complexity), default=0)
        except:
            return 0
    
    def _get_cognitive_complexity(self, code: str) -> int:
        """Calculate cognitive complexity."""
        try:
            # Simple implementation - could be enhanced
            tree = ast.parse(code)
            complexity = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.Try)):
                    complexity += 1
            return complexity
        except:
            return 0
    
    def _get_maintainability_index(self, code: str) -> float:
        """Get maintainability index using Radon."""
        try:
            return radon_metrics.mi_visit(code, multi=True)
        except:
            return 0.0
    
    def _run_mypy(self, file_path: Path) -> List[RuleViolation]:
        """Run mypy type checker."""
        result = mypy.api.run([str(file_path)])
        
        issues = []
        for line in result[0].split('\n'):
            if line.strip():
                issues.append(RuleViolation(
                    rule=CodeQualityRule.TYPE_CHECK,
                    message=line,
                    line=0,  # Parse line number from message if needed
                    severity='error'
                ))
        return issues
    
    def _run_bandit(self, file_path: Path) -> List[RuleViolation]:
        """Run Bandit security checker."""
        config = BanditConfig()
        manager = bandit_manager.BanditManager(config, 'file')
        
        manager.discover_files([str(file_path)])
        manager.run_tests()
        
        issues = []
        for issue in manager.get_issue_list():
            issues.append(RuleViolation(
                rule=CodeQualityRule.SECURITY,
                message=issue.text,
                line=issue.line_number,
                severity=issue.severity
            ))
        return issues
    
    def _check_black_compliance(self, code: str) -> bool:
        """Check if code complies with Black formatting."""
        try:
            black.format_str(code, mode=black.FileMode())
            return True
        except:
            return False
    
    def _count_lines(self, code: str) -> int:
        """Count lines of code."""
        return len(code.splitlines())
    
    def _get_comment_ratio(self, code: str) -> float:
        """Calculate ratio of comments to code."""
        try:
            tree = ast.parse(code)
            total_lines = self._count_lines(code)
            comment_lines = 0
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
                    comment_lines += len(node.value.s.splitlines())
            
            return comment_lines / total_lines if total_lines > 0 else 0
        except:
            return 0.0
