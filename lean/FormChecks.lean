/-
  Frontier Forms M2: declared per-field constraints, checked in Lean 4 (v4.15.0).

  Run:  lean --run lean/FormChecks.lean data/forms_injected_v1/forms.jsonl > flags.jsonl
  Each output line: {"form_id": ..., "flags": [{"field_key": ..., "rule": ...}, ...]}

  The `example` blocks below are checked by `native_decide` when the file is
  compiled: the stated behaviour is evaluated by compiled code, so these
  checks trust the Lean compiler (they are not pure kernel proofs; string
  functions do not reduce in the kernel). If any example is false the file
  fails to compile and M2 does not count.
-/
import Lean.Data.Json
open Lean

namespace FormChecks

def refDate : String := "2026-11-01"

def isDigitC (c : Char) : Bool := c.isDigit
def allDigits (s : String) : Bool := s.length > 0 && s.all isDigitC

/-- NNNN-NN-NN with month 01-12 and day 01-31, not after the reference date. -/
def isIsoDate (s : String) : Bool :=
  let cs := s.toList
  cs.length == 10 &&
  (cs.get! 4 == '-') && (cs.get! 7 == '-') &&
  allDigits (String.mk (cs.take 4)) &&
  allDigits (String.mk ((cs.drop 5).take 2)) &&
  allDigits (String.mk ((cs.drop 8).take 2)) &&
  (let mo := (String.mk ((cs.drop 5).take 2)).toNat!
   let d := (String.mk ((cs.drop 8).take 2)).toNat!
   1 ≤ mo && mo ≤ 12 && 1 ≤ d && d ≤ 31) &&
  decide (s ≤ refDate)

/-- NNN-NNN-NNNN -/
def isPhone (s : String) : Bool :=
  match s.splitOn "-" with
  | [a, b, c] => a.length == 3 && b.length == 3 && c.length == 4 && allDigits a && allDigits b && allDigits c
  | _ => false

def isZip (s : String) : Bool := s.length == 5 && allDigits s
def isState (s : String) : Bool := s.length == 2 && s.all Char.isUpper

def nameChar (c : Char) : Bool := c.isAlpha || c == ' ' || c == '-' || c == '\'' || c == '.'
def isName (s : String) : Bool := s.trim.length > 0 && s.all nameChar
def noDigits (s : String) : Bool := s.trim.length > 0 && !(s.any isDigitC)

/-- Parse a non-negative decimal "123" or "123.4" into tenths. -/
def tenths? (s : String) : Option Nat :=
  match s.splitOn "." with
  | [w] => if allDigits w then some (w.toNat! * 10) else none
  | [w, f] => if allDigits w && f.length == 1 && allDigits f then some (w.toNat! * 10 + f.toNat!) else none
  | _ => none

def inRange (s : String) (lo hi : Nat) : Bool :=
  match tenths? s with
  | some t => lo ≤ t && t ≤ hi
  | none => false

/-- "S/D" integers with 40 ≤ D < S ≤ 300. -/
def isBP (s : String) : Bool :=
  match s.splitOn "/" with
  | [a, b] => allDigits a && allDigits b &&
      (let sy := a.toNat!; let di := b.toNat!; 40 ≤ di && di < sy && sy ≤ 300)
  | _ => false

/-- Rule for a field key; returns the failed rule name, or none. Blank optional fields pass. -/
def check (key typ value : String) (required : Bool) (options : List String) : Option String :=
  let v := value.trim
  let identity := ["full_name", "patient_name", "surname", "first", "date_of_birth", "dob", "sex",
                   "phone", "street", "city", "state", "zip"]
  if v.isEmpty then
    if required && identity.contains key then some "required_identity_blank" else none
  else if typ == "select" then
    if options.contains v then none else some "select_not_in_options"
  else if ["full_name", "patient_name", "surname", "first"].contains key then
    if isName v then none else some "name_chars"
  else if ["date_of_birth", "dob"].contains key then
    if isIsoDate v then none else some "iso_date"
  else if key == "phone" then (if isPhone v then none else some "phone_format")
  else if key == "zip" then (if isZip v then none else some "zip_format")
  else if key == "state" then (if isState v then none else some "state_format")
  else if ["city", "language", "marital"].contains key then (if noDigits v then none else some "unexpected_digits")
  else if key == "height_cm" then (if inRange v 300 2500 then none else some "height_cm_range")
  else if key == "weight_kg" then (if inRange v 5 3500 then none else some "weight_kg_range")
  else if key == "weight_lb" then (if inRange v 10 8000 then none else some "weight_lb_range")
  else if key == "blood_pressure" then (if isBP v then none else some "bp_format_range")
  else none

-- Compile-time checks of the constraints (native_decide; trusts the compiler).
example : isPhone "555-799-1540" = true := by native_decide
example : isPhone "1990-01-02" = false := by native_decide
example : isZip "02026" = true := by native_decide
example : isZip "0202" = false := by native_decide
example : isState "MA" = true := by native_decide
example : isBP "120/80" = true := by native_decide
example : isBP "80/120" = false := by native_decide
example : inRange "172.9" 300 2500 = true := by native_decide
example : inRange "25.0" 300 2500 = false := by native_decide
example : check "dob" "text" "" true [] = some "required_identity_blank" := by native_decide
example : check "conditions" "textarea" "" true [] = none := by native_decide

def strField (j : Json) (k : String) : String :=
  match j.getObjValAs? String k with
  | .ok s => s
  | .error _ => ""

def flagsFor (form : Json) : Json := Id.run do
  let fid := strField form "form_id"
  let mut out : Array Json := #[]
  match form.getObjVal? "fields" with
  | .ok (.obj kvs) =>
    for ⟨k, f⟩ in kvs.toArray do
      let opts : List String := match f.getObjValAs? (Array String) "options" with
        | .ok a => a.toList
        | .error _ => []
      let req := match f.getObjValAs? Bool "required" with
        | .ok b => b
        | .error _ => false
      match check k (strField f "type") (strField f "value") req opts with
      | some rule => out := out.push (Json.mkObj [("field_key", Json.str k), ("rule", Json.str rule)])
      | none => pure ()
  | _ => pure ()
  return Json.mkObj [("form_id", Json.str fid), ("flags", Json.arr out)]

end FormChecks

def main (args : List String) : IO UInt32 := do
  let path := args.headD "data/forms_injected_v1/forms.jsonl"
  let lines ← IO.FS.lines path
  for line in lines do
    if line.trim.isEmpty then continue
    match Json.parse line with
    | .ok j => IO.println (FormChecks.flagsFor j).compress
    | .error e => do IO.eprintln s!"PARSE_ERROR {e}"; return 1
  return 0
