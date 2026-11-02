-- Lean4 structural examples only. NOT_TESTED until lean/lake executes.
-- These do NOT prove cryptographic SHA256 or clinical correctness.
structure TurnLeaf where
  payloadId : Nat
  sourceId : Nat
  occurrenceId : Nat
deriving DecidableEq

structure Transition where
  input : Nat
  output : Nat
  parent : Nat
deriving DecidableEq

def links (a b : Transition) : Prop := a.output = b.parent

theorem admitted_link_requires_equality (a b : Transition)
    (h : a.output = b.parent) : links a b := h

theorem each_leaf_has_its_source (leaf : TurnLeaf) :
    leaf.sourceId = leaf.sourceId := rfl
