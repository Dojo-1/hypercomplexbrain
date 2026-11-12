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

#print axioms AionFormal.R6.normChange_split
#print axioms AionFormal.R6.expansionPart_nonneg
#print axioms AionFormal.R6.contractionPart_nonneg
#print axioms AionFormal.R6.one_signed_part_is_zero
#print axioms AionFormal.R6.normChange_comp
#print axioms AionFormal.R6.normChange_zero_of_roundtrip
#print axioms AionFormal.R6.normChange_orthogonalFrame
#print axioms AionFormal.R6.normChange_reframeTransport
#print axioms AionFormal.R6.signed_parts_reframeTransport
#print axioms AionFormal.R6.normChange_filter_nonpos
#print axioms AionFormal.R6.expansionPart_filter_zero
#print axioms AionFormal.R6.boost_expanding_axis_positive
#print axioms AionFormal.R6.boost_contracting_axis_negative
#print axioms AionFormal.R6.boost_reverse_roundtrip
#print axioms AionFormal.R6.closed_boost_loop_hides_local_expansion

#print axioms AionFormal.R6.symForm_eq_of_coordinates
#print axioms AionFormal.R6.formAdd_eval
#print axioms AionFormal.R6.formSub_eval
#print axioms AionFormal.R6.formPullback_eval
#print axioms AionFormal.R6.metricPullbackDefect_eval
#print axioms AionFormal.R6.mapApply_comp
#print axioms AionFormal.R6.formPullback_comp
#print axioms AionFormal.R6.metricPullbackDefect_comp
#print axioms AionFormal.R6.metricPullbackDefect_middle_mismatch
#print axioms AionFormal.R6.metricPullbackDefect_identity
#print axioms AionFormal.R6.euclideanDefect_agrees_normChange
#print axioms AionFormal.R6.anisotropic_zero_on_one_nonzero_input
#print axioms AionFormal.R6.anisotropic_defect_nonzero
#print axioms AionFormal.R6.anisotropic_opposite_axis_defects

#print axioms AionFormal.R6.formPullback_add
#print axioms AionFormal.R6.formPullback_sub
#print axioms AionFormal.R6.formPullback_identity
#print axioms AionFormal.R6.formPullback_zero
#print axioms AionFormal.R6.metricDefect_commuting_square
#print axioms AionFormal.R6.metricDefect_commuting_square_eval
#print axioms AionFormal.R6.metricDefect_zero_of_matched_forms
#print axioms AionFormal.R6.metricDefect_zero_iff_matched_forms
#print axioms AionFormal.R6.pullback_zero_reflect_of_right_inverse
#print axioms AionFormal.R6.metricDefect_zero_covariant_iff
#print axioms AionFormal.R6.realMap_eq_of_coordinates
#print axioms AionFormal.R6.anisotropic_inverse_certified
#print axioms AionFormal.R6.anisotropic_reparametrized_metric
#print axioms AionFormal.R6.anisotropic_matched_vs_unmatched_metrics
#print axioms AionFormal.R6.singular_projection_hides_nonzero_form

#print axioms AionFormal.Heterogeneous.defect_eval
#print axioms AionFormal.Heterogeneous.defect_symmetric
#print axioms AionFormal.Heterogeneous.pullback_add
#print axioms AionFormal.Heterogeneous.pullback_sub
#print axioms AionFormal.Heterogeneous.pullback_comp
#print axioms AionFormal.Heterogeneous.pullback_zero
#print axioms AionFormal.Heterogeneous.zero_tendril_hides_form
#print axioms AionFormal.Heterogeneous.rechart_defect_zero
#print axioms AionFormal.Heterogeneous.defect_zero_iff_compatible
#print axioms AionFormal.Heterogeneous.defect_comp
#print axioms AionFormal.Heterogeneous.defect_middle_mismatch
#print axioms AionFormal.Heterogeneous.defect_commuting_square
#print axioms AionFormal.Heterogeneous.pullback_injective_of_surjective
#print axioms AionFormal.Heterogeneous.defect_zero_under_faithful_chart_iff
#print axioms AionFormal.Heterogeneous.two_three_four_defect_comp

#print axioms AionFormal.Heterogeneous.nonnegative_pullback
#print axioms AionFormal.Heterogeneous.pullback_zero_on_kernel
#print axioms AionFormal.Heterogeneous.strictlyPositive_pullback_of_injective
#print axioms AionFormal.Heterogeneous.injective_of_strictlyPositive_pullback
#print axioms AionFormal.Heterogeneous.strictlyPositive_pullback_iff_injective
#print axioms AionFormal.Heterogeneous.noninjective_pullback_not_strictlyPositive
#print axioms AionFormal.Heterogeneous.positive_rechart_iff_injective
#print axioms AionFormal.Heterogeneous.positiveRechart_defect_zero
#print axioms AionFormal.Heterogeneous.compatible_positive_source_implies_injective
#print axioms AionFormal.Heterogeneous.compatible_positive_source_iff_injective
#print axioms AionFormal.Heterogeneous.oneAxis_nonzero
#print axioms AionFormal.Heterogeneous.zero_tendril_not_strictlyPositive
#print axioms AionFormal.Heterogeneous.identity_zero_target_not_strictlyPositive
#print axioms AionFormal.Heterogeneous.two_three_positive_pullback_iff_injective
#print axioms AionFormal.Heterogeneous.composition_positive_pullback

#print axioms AionFormal.Instrumented.observationRemainder_zero_iff_commutes
#print axioms AionFormal.Instrumented.clockRemainder_zero_iff_commutes
#print axioms AionFormal.Instrumented.metricRemainder_comp
#print axioms AionFormal.Instrumented.observationRemainder_comp
#print axioms AionFormal.Instrumented.clockRemainder_comp
#print axioms AionFormal.Instrumented.jointlyCompatible_comp

#print axioms AionFormal.Units.length_not_time
#print axioms AionFormal.Units.dimProduct_comm
#print axioms AionFormal.Units.dimProduct_assoc
#print axioms AionFormal.Units.dimProduct_dimensionless
#print axioms AionFormal.Units.dimQuotient_self
#print axioms AionFormal.Units.compose_factor_positive
#print axioms AionFormal.Units.convert_comp
#print axioms AionFormal.Units.convert_identity
#print axioms AionFormal.Units.convert_preserves_positive
#print axioms AionFormal.Units.one_metre_is_one_hundred_centimetres

#print axioms AionFormal.Clocks.applyCalibration_comp
#print axioms AionFormal.Clocks.calibrated_order
#print axioms AionFormal.Clocks.residual_zero_iff
#print axioms AionFormal.Clocks.residual_comp
#print axioms AionFormal.Clocks.exact_comp
#print axioms AionFormal.Clocks.target_readout_ordered
#print axioms AionFormal.Clocks.epoch_shift_not_exact

#print axioms AionFormal.Calibrated.geometricRemainder_comp
#print axioms AionFormal.Calibrated.observableRemainder_comp
#print axioms AionFormal.Calibrated.clockRemainder_comp
#print axioms AionFormal.Calibrated.jointlyCompatible_comp
#print axioms AionFormal.Calibrated.jointlyCompatible_requires_injective
#print axioms AionFormal.Calibrated.incompatible_length_time_observation_types
