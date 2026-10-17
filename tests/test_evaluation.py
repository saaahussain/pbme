from pbme.evaluation import run_evaluation


def test_evaluation_scenarios_pass():
    result = run_evaluation()
    assert result["passed"] == result["scenario_count"]
    assert result["exposure_reduction_percent"] > 0
