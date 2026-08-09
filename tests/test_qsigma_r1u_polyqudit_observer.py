import numpy as np

from run_qsigma_r1u_polyqudit_observer import (
    DS,
    NS,
    SEEDS,
    frame_spread,
    generalized_weyl_features,
    plant_instance,
    saliencies,
    select,
)


def test_weyl_unit_norm():
    for d in DS:
        features = generalized_weyl_features(np.arange(d), d)
        assert np.allclose(np.sum(features * features, axis=1), 1.0)


def test_planted_relations_exact_and_disjoint():
    for d in DS:
        for n in NS:
            for seed in SEEDS:
                x, targets, secret = plant_instance(d, n, seed)
                assert len(set(targets) & set(targets + 1)) == 0
                assert np.all(((x[targets + 1] - x[targets]) % d) == secret)


def test_algebra_and_alignment_rank_exact_relations_identically():
    for d in DS:
        x, targets, secret = plant_instance(d, 16, 0)
        scores = saliencies(x, d, secret, 0)
        m = len(targets)
        assert np.array_equal(
            select(scores["algebra"], m),
            select(scores["alignment"], m),
        )


def test_frame_invariance_exact():
    for d in DS:
        x, targets, secret = plant_instance(d, 16, 1)
        assert frame_spread(x, d, secret, targets, 1) <= 1e-12
