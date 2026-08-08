import numpy as np
from aionq.projected_partition import *

SECRET=1

def test_projection_and_pair_symmetry():
    for seed in range(8):
        w=projection_weights(seed)
        a=projected_state_explicit(SECRET,w); b=projected_state_direct(SECRET,w)
        assert np.linalg.norm(a-b) <= 1e-12
        assert max(abs(a[x]-a[x^SECRET]) for x in range(16)) <= 1e-12

def test_scaled_gf4_subspaces_and_alignment():
    hs=gf4_scaled_subspaces()
    assert len(hs)==5
    assert sum(SECRET in h for h in hs)==1
    for h in hs:
        p=additive_coset_partition(h)
        assert len(p)==4 and all(len(c)==4 for c in p)

def test_aligned_and_transverse_known_answers():
    state=projected_state_direct(SECRET,projection_weights(0))
    aligned_h=next(h for h in gf4_scaled_subspaces() if SECRET in h)
    m=evaluate_partition(state,additive_coset_partition(aligned_h),SECRET)
    assert m.pair_cut_fraction==0.0
    assert m.sector_forbidden_mass <= 1e-12
    p=random_aligned_partition(SECRET,7)
    m=evaluate_partition(state,p,SECRET)
    assert m.pair_cut_fraction==0.0 and m.sector_forbidden_mass <= 1e-12
    p=random_transverse_partition(SECRET,7)
    m=evaluate_partition(state,p,SECRET)
    assert m.pair_cut_fraction==1.0
    assert m.sector_forbidden_mass > 1e-8
    assert m.offdiag_forbidden_real < 0.0
    assert m.closure_defect <= 1e-12

def test_metamorphic_cell_order_and_phase():
    state=projected_state_direct(SECRET,projection_weights(3))
    p=random_transverse_partition(SECRET,11)
    m1=evaluate_partition(state,p,SECRET)
    m2=evaluate_partition(state,tuple(reversed(p)),SECRET)
    phase=np.exp(1j*0.731)
    m3=evaluate_partition(phase*state,p,SECRET)
    for field in m1.__dict__:
        assert abs(getattr(m1,field)-getattr(m2,field)) <= 1e-12
        assert abs(getattr(m1,field)-getattr(m3,field)) <= 1e-12
