namespace FrontierForms

/-- Formalized status of one deliberately corrupted synthetic field. 
    A correction module is enabled independently of the byte-level source gate. -/
def correctAfter (faultPresent moduleEnabled : Bool) : Bool :=
  (!faultPresent) || moduleEnabled

/-- A clean field stays correct, irrespective of modules. -/
theorem clean_stays_correct (enabled : Bool) :
    correctAfter false enabled = true := by
  cases enabled <;> rfl

/-- An enabled matching module repairs its isolated synthetic fault. -/
theorem module_fixes_its_fault :
    correctAfter true true = true := by rfl

/-- With its only matching module absent, a synthetic fault persists. -/
theorem isolated_fault_survives_lomo :
    correctAfter true false = false := by rfl

/-- Four simultaneously present *independent* faults require four modules
    under this Boolean fixture model. This is not a measured model gain. -/
def allFourRepaired (a b c d : Bool) : Bool := a && b && c && d

theorem full_four_repaired :
    allFourRepaired true true true true = true := by rfl

theorem lomo_a_fails :
    allFourRepaired false true true true = false := by rfl

theorem lomo_b_fails :
    allFourRepaired true false true true = false := by rfl

theorem lomo_c_fails :
    allFourRepaired true true false true = false := by rfl

theorem lomo_d_fails :
    allFourRepaired true true true false = false := by rfl

/-- Source admission requires actual byte identity and independent readback. -/
def admitted (bytesEqual readbackOk : Bool) : Bool :=
  bytesEqual && readbackOk

theorem reject_unverified_bytes (readbackOk : Bool) :
    admitted false readbackOk = false := by
  cases readbackOk <;> rfl

theorem reject_failed_readback (bytesEqual : Bool) :
    admitted bytesEqual false = false := by
  cases bytesEqual <;> rfl

end FrontierForms
