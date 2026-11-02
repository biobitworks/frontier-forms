-- Proposed source; Lean 4 execution NOT_TESTED.
namespace FrontierForms
structure GateState where
  mcnemarPass : Bool
  bootstrapPass : Bool
  replicationPass : Bool
  heldout : Bool
def admit (g : GateState) : Bool :=
  g.mcnemarPass && g.bootstrapPass && g.replicationPass && g.heldout
theorem no_admit_on_mcnemar_fail (g : GateState) (h : g.mcnemarPass = false) : admit g = false := by
  simp [admit, h]
theorem no_admit_on_bootstrap_fail (g : GateState) (h : g.bootstrapPass = false) : admit g = false := by
  simp [admit, h]
end FrontierForms
