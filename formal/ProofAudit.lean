import AionFormal

/-!
CI prints the kernel dependency list of each exported proof. The CI workflow
refuses `sorryAx`; reviewers must also inspect any unexpected axioms.
This file is NOT a replacement for a successful Lake build or semantic review.
-/

#print axioms OhniumObservatory.AUMPhase.next_three
#print axioms OhniumObservatory.r40_frame_count
#print axioms OhniumObservatory.signal_crosstalk_dimension_count
#print axioms OhniumObservatory.exact_return_and_accounting_of_hypotheses
#print axioms RecognitionChamber.loopDefect_nonneg
#print axioms RecognitionChamber.loopDefect_eq_zero_of_leftInverse
#print axioms RecognitionChamber.leftInverse_of_loopDefect_eq_zero_metric
#print axioms RecognitionChamber.loopDefect_conjugate_of_isometry
#print axioms RecognitionChamber.level_eq
#print axioms RecognitionChamber.finite_depletion_of_draw_gt_refill
#print axioms RecognitionChamber.not_mayPromote_of_authorized_within_closure
#print axioms AionFormal.R6.radial_stretch_sq_eq_one_iff_zero
#print axioms AionFormal.R6.boost_preserves_sqNorm_iff_zero
#print axioms AionFormal.R6.boost_nonzero_not_isometric

#print axioms AionFormal.R6.contraction_pos
#print axioms AionFormal.R6.contraction_le_one
#print axioms AionFormal.R6.contraction_sq_le_one
#print axioms AionFormal.R6.leakage_sq_add_contraction_sq
#print axioms AionFormal.R6.filter_eq_scaled_boost
#print axioms AionFormal.R6.dilation_preserves_combined_sqNorm
#print axioms AionFormal.R6.dilation_zero_ancilla_block
#print axioms AionFormal.R6.filter_weight_bounds
#print axioms AionFormal.R6.filter_contracting_axis_weight
#print axioms AionFormal.R6.filter_uncontracted_axis_weight
#print axioms AionFormal.R6.contraction_sq_eq_exp
#print axioms AionFormal.R6.filter_weight_bounds_exp
#print axioms AionFormal.R6.filter_zero_depth

#print axioms AionFormal.R6.OrthogonalFrame.inverse_preserves_sqNorm
#print axioms AionFormal.R6.frameFilter_sqNorm
#print axioms AionFormal.R6.frameFilter_pullback
#print axioms AionFormal.R6.frameFilter_weight_bounds_exp
#print axioms AionFormal.R6.frameFilter_contracting_axis_weight
#print axioms AionFormal.R6.frameFilter_uncontracted_axis_weight
#print axioms AionFormal.R6.frameFilter_joint_change
#print axioms AionFormal.R6.frameFilter_joint_change_sqNorm
#print axioms AionFormal.R6.frameFilter_identity
#print axioms AionFormal.R6.nonzero_boost_is_not_an_orthogonal_frame
