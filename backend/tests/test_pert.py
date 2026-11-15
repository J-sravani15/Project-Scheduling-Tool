import pytest
import math
from app.algorithms.pert import (
    PertTaskEstimate,
    analyze_pert,
    calculate_normal_cdf,
)
from app.algorithms.exceptions import InvalidPertEstimateError


def test_pert_expected_duration_and_variance():
    # O=2, M=5, P=14
    # Expected = (2 + 20 + 14)/6 = 36/6 = 6.0
    # Sigma = (14 - 2)/6 = 12/6 = 2.0
    # Variance = 2.0^2 = 4.0
    est = PertTaskEstimate(id="T1", optimistic=2.0, most_likely=5.0, pessimistic=14.0)
    assert est.expected_duration == 6.0
    assert est.standard_deviation == 2.0
    assert est.variance == 4.0


def test_pert_equal_estimates():
    # If O = M = P = 5, variance should be 0.0
    est = PertTaskEstimate(id="T2", optimistic=5.0, most_likely=5.0, pessimistic=5.0)
    assert est.expected_duration == 5.0
    assert est.variance == 0.0
    assert est.standard_deviation == 0.0


def test_pert_invalid_estimates():
    # O > M
    with pytest.raises(InvalidPertEstimateError):
        PertTaskEstimate(id="E1", optimistic=10.0, most_likely=8.0, pessimistic=12.0)

    # M > P
    with pytest.raises(InvalidPertEstimateError):
        PertTaskEstimate(id="E2", optimistic=4.0, most_likely=10.0, pessimistic=8.0)

    # Negative duration
    with pytest.raises(InvalidPertEstimateError):
        PertTaskEstimate(id="E3", optimistic=-1.0, most_likely=2.0, pessimistic=5.0)


def test_pert_normal_cdf_accuracy():
    # Standard normal distribution landmarks:
    # Z = 0 -> 50%
    assert math.isclose(calculate_normal_cdf(0.0), 0.5, rel_tol=1e-5)
    # Z = 1 -> ~84.13%
    assert math.isclose(calculate_normal_cdf(1.0), 0.84134, rel_tol=1e-3)
    # Z = 1.96 -> ~97.5%
    assert math.isclose(calculate_normal_cdf(1.96), 0.975, rel_tol=1e-3)
    # Z = -1 -> ~15.87%
    assert math.isclose(calculate_normal_cdf(-1.0), 0.15865, rel_tol=1e-3)


def test_pert_project_analysis_with_deadline_probability():
    # Critical path: T1 (expected=6.0, var=4.0) + T2 (expected=4.0, var=1.0)
    # Project expected = 10.0h, variance = 5.0, std_dev = sqrt(5) ≈ 2.2361h
    t1 = PertTaskEstimate(id="T1", optimistic=2.0, most_likely=5.0, pessimistic=14.0)
    t2 = PertTaskEstimate(id="T2", optimistic=1.0, most_likely=4.0, pessimistic=7.0)
    
    # Target deadline = 12.2361 hours (Z ≈ 1.0 -> probability ≈ 84.1%)
    target_dl = 10.0 + math.sqrt(5.0)
    res = analyze_pert(
        task_estimates=[t1, t2],
        critical_path_task_ids=["T1", "T2"],
        target_deadline_hours=target_dl,
    )

    assert res.critical_path_expected_duration == 10.0
    assert res.critical_path_variance == 5.0
    assert math.isclose(res.critical_path_std_dev, 2.2361, rel_tol=1e-3)
    assert res.z_score is not None
    assert math.isclose(res.z_score, 1.0, rel_tol=1e-2)
    assert res.probability_of_meeting_deadline is not None
    assert 0.83 <= res.probability_of_meeting_deadline <= 0.85
    assert len(res.assumptions) > 0


def test_pert_zero_variance_project():
    # If all tasks on CP have zero variance:
    t1 = PertTaskEstimate(id="T1", optimistic=5.0, most_likely=5.0, pessimistic=5.0)
    res_pass = analyze_pert([t1], ["T1"], target_deadline_hours=6.0)
    assert res_pass.probability_of_meeting_deadline == 1.0

    res_fail = analyze_pert([t1], ["T1"], target_deadline_hours=4.0)
    assert res_fail.probability_of_meeting_deadline == 0.0
