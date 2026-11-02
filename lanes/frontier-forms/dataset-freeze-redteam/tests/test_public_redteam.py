"""Regression tests for the frontier-forms freeze red-team lane (synthetic data only)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import fixture_attacks as fa  # noqa: E402
import freezelib as fl  # noqa: E402
import public_redteam as pr  # noqa: E402

FX = fa.make_fixture()
RAW = fa.serialize(FX)


def test_fixture_matches_committed_bytes():
    assert (Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_pseudobulk_v1.bin").read_bytes() == RAW


@pytest.mark.parametrize("kind,incumbent_detects", [
    ("byte_flip_same_size", False), ("row_reorder_within_batch", False), ("gene_reorder", False),
    ("gene_rename", False), ("holdout_row_copied_into_train", False), ("label_switch", False),
    ("sample_id_swap_train_holdout", True), ("duplicate_record", True), ("missing_record", True),
    ("batch_in_two_partitions", True)])
def test_incumbent_vs_successor(kind, incumbent_detects):
    raw = fa.serialize(fa.mutate(FX, kind))
    assert fa.incumbent_check(raw, fa.incumbent_expected(RAW))[0] is (not incumbent_detects)
    assert fa.v2_check(raw, fa.v2_expected(RAW))[0] is False


def test_merkle_proofs_bind_index_and_size():
    leaves = [fl.sha256_hex(bytes([i])) for i in range(7)]
    root = fl.merkle_root(leaves)
    for i in range(7):
        assert fl.verify_inclusion(leaves[i], i, 7, fl.inclusion_proof(leaves, i), root)
    assert not fl.verify_inclusion(leaves[0], 1, 7, fl.inclusion_proof(leaves, 0), root)
    assert not fl.verify_inclusion(leaves[0], 0, 4, fl.inclusion_proof(leaves, 0), root)
    # Observed limitation: a wrong tree size whose audit-path shape matches (7 vs 8 for index 0)
    # still verifies.  The size is bound only through the root; pin leaf_count with the root.
    assert fl.verify_inclusion(leaves[0], 0, 8, fl.inclusion_proof(leaves, 0), root)


def test_full_run_is_deterministic(tmp_path):
    a = pr.run(tmp_path / "a")
    b = pr.run(tmp_path / "b")
    assert a["synthetic_freeze_root"] == b["synthetic_freeze_root"] == "a10240801c05e0121bf6ec6f3ad07cae4073e2a3f7d0e88205a8ef67986ce4a5"
    by = {t["attack_id"]: t for t in a["tests"]}
    assert by["MK00"]["incumbent"] == "ACCEPT"
    assert all(by[k]["incumbent"].startswith("REJECT") for k in ("MK01", "MK02", "MK03", "MK05", "MK06", "MK07", "MK08", "MK09", "MK10"))
    assert by["MK12"]["incumbent"] == "unpinned: ACCEPT" and by["MK12"]["successor"] == "pinned root: REJECT"
