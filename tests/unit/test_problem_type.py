import shared.solver as solver_module


def _make_solver() -> solver_module.BaseSolver:
    # Create a BaseSolver instance without running __init__
    return solver_module.BaseSolver.__new__(solver_module.BaseSolver)  # type: ignore[arg-type]


def test_problem_type_defaults_to_general_when_no_signals():
    solver = _make_solver()
    characteristics = {}
    assert solver._get_problem_type(characteristics) == "general"


def test_problem_type_prefers_grid_when_grid_operations_present():
    solver = _make_solver()
    characteristics = {"grid_operations": 1.0}
    assert solver._get_problem_type(characteristics) == "grid"


def test_problem_type_graph_when_graph_complexity_present():
    solver = _make_solver()
    characteristics = {"graph_complexity": 1.0}
    assert solver._get_problem_type(characteristics) == "graph"


def test_problem_type_math_when_math_complexity_present():
    solver = _make_solver()
    characteristics = {"math_complexity": 1.0}
    assert solver._get_problem_type(characteristics) == "math"


def test_problem_type_string_when_string_processing_present():
    solver = _make_solver()
    characteristics = {"string_processing": 1.0}
    assert solver._get_problem_type(characteristics) == "string"


def test_problem_type_optimization_when_only_optimization_required_present():
    solver = _make_solver()
    characteristics = {"optimization_required": 1.0}
    assert solver._get_problem_type(characteristics) == "optimization"


def test_problem_type_uses_priority_order_when_multiple_signals_present():
    solver = _make_solver()
    characteristics = {
        "grid_operations": 1.0,
        "graph_complexity": 1.0,
        "math_complexity": 1.0,
        "string_processing": 1.0,
        "optimization_required": 1.0,
    }
    # Grid should win because it is checked first
    assert solver._get_problem_type(characteristics) == "grid"
