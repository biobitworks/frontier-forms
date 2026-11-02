-- Frontier Forms red-team: field admission gate and its leave-one-mechanism-out (LOMO) counterexamples.
-- Core Lean 4 only (no Mathlib). Every theorem below is checked by `decide` on concrete error vectors, so a
-- successful compile is a machine-checked statement about the GATE LOGIC, not about any model or dataset.
namespace FrontierForms.Gates

/-- Which checks a planted error class defeats when the corresponding mechanism is switched off. -/
structure ErrorVector where
  identityFails    : Bool   -- printed case id ≠ FCO case id (E3 cross-patient)
  ruleFails        : Bool   -- a deterministic rule fails (E1 encounter<birth, E2 gender, E4 missing, E5 date format)
  commitmentFails  : Bool   -- extracted value ≠ committed source value (any E1..E7)
  consistencyFails : Bool   -- two independent extractors disagree (variance / OCR noise)
  deriving DecidableEq, Repr

/-- Which mechanisms are enabled in a harness configuration (one cell of the heat map). -/
structure Config where
  identity    : Bool
  rules       : Bool
  commitment  : Bool
  consistency : Bool
  deriving DecidableEq, Repr

/-- A field is admitted iff every ENABLED mechanism passes. -/
def admit (c : Config) (e : ErrorVector) : Bool :=
  (!c.identity    || !e.identityFails) &&
  (!c.rules       || !e.ruleFails) &&
  (!c.commitment  || !e.commitmentFails) &&
  (!c.consistency || !e.consistencyFails)

def full : Config := ⟨true, true, true, true⟩
def minusIdentity    : Config := ⟨false, true, true, true⟩
def minusRules       : Config := ⟨true, false, true, true⟩
def minusCommitment  : Config := ⟨true, true, false, true⟩
def minusConsistency : Config := ⟨true, true, true, false⟩
def noGates : Config := ⟨false, false, false, false⟩

-- Planted error classes as vectors (which mechanisms can see them).
def E1_encBeforeBirth : ErrorVector := ⟨false, true,  true,  false⟩
def E3_caseIdSwap     : ErrorVector := ⟨true,  false, true,  false⟩
def E6_nameSwap       : ErrorVector := ⟨false, false, true,  false⟩
def E7_digitFlip      : ErrorVector := ⟨false, false, true,  false⟩
def V2_scanNoise      : ErrorVector := ⟨false, false, false, true⟩
def cleanForm         : ErrorVector := ⟨false, false, false, false⟩

/-- The full gate rejects every planted class and admits the clean control. -/
theorem full_rejects_E1 : admit full E1_encBeforeBirth = false := by decide
theorem full_rejects_E3 : admit full E3_caseIdSwap = false := by decide
theorem full_rejects_E6 : admit full E6_nameSwap = false := by decide
theorem full_rejects_E7 : admit full E7_digitFlip = false := by decide
theorem full_rejects_V2 : admit full V2_scanNoise = false := by decide
theorem full_admits_clean : admit full cleanForm = true := by decide

/-- LOMO: removing exactly one mechanism admits a planted error that only that mechanism sees. -/
theorem lomo_identity_admits_E3 : admit minusIdentity E3_caseIdSwap = false := by decide
-- E3 is also caught by the commitment check (the printed case id differs from the committed one), so identity is
-- NOT a sole line of defence; the theorem above records that fact (admit stays false). Its sole-defence class is the
-- cross-patient swap where commitments are absent:
def E3_noCommitments : ErrorVector := ⟨true, false, false, false⟩
theorem lomo_identity_sole_defence : admit minusIdentity E3_noCommitments = true ∧ admit full E3_noCommitments = false := by decide
theorem lomo_commitment_admits_E6 : admit minusCommitment E6_nameSwap = true := by decide
theorem lomo_commitment_admits_E7 : admit minusCommitment E7_digitFlip = true := by decide
theorem lomo_consistency_admits_V2 : admit minusConsistency V2_scanNoise = true := by decide
theorem lomo_rules_still_rejects_E1_via_commitment : admit minusRules E1_encBeforeBirth = false := by decide

/-- No gates admits everything: the baseline of the heat map. -/
theorem nogates_admits_E7 : admit noGates E7_digitFlip = true := by decide

/-- Monotonicity: enabling a mechanism can only remove admissions (never add). Checked for all 16 configs × 16 vectors. -/
def allBools : List Bool := [false, true]
def allConfigs : List Config :=
  allBools.flatMap fun a => allBools.flatMap fun b => allBools.flatMap fun c => allBools.map fun d => (⟨a, b, c, d⟩ : Config)
def allVectors : List ErrorVector :=
  allBools.flatMap fun a => allBools.flatMap fun b => allBools.flatMap fun c => allBools.map fun d => (⟨a, b, c, d⟩ : ErrorVector)
def leq (c₁ c₂ : Config) : Bool :=
  (!c₁.identity || c₂.identity) && (!c₁.rules || c₂.rules) && (!c₁.commitment || c₂.commitment) && (!c₁.consistency || c₂.consistency)
theorem admit_antitone_in_config :
    (allConfigs.all fun c₁ => allConfigs.all fun c₂ => allVectors.all fun e =>
      !(leq c₁ c₂) || !(admit c₂ e) || admit c₁ e) = true := by native_decide

end FrontierForms.Gates
