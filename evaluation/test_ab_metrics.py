from __future__ import annotations
from evaluation.ab_metrics import _file_matches


def test_exact_match():
    assert _file_matches("utils.py", ["utils.py"])
    assert _file_matches("dependencies/utils.py", ["dependencies/utils.py"])


def test_basename_no_path_match():
    # root utils.py should NOT match dependencies/utils.py
    assert _file_matches("utils.py", ["utils.py"])
    assert not _file_matches("utils.py", ["dependencies/utils.py"])
    assert not _file_matches("utils.py", ["openapi/utils.py"])


def test_suffix_match_with_path():
    assert _file_matches("dependencies/utils.py", ["dependencies/utils.py"])
    assert _file_matches("dependencies/utils.py", ["fastapi/dependencies/utils.py"])
    assert _file_matches("_compat/v2.py", ["_compat/v2.py"])


def test_fastapi_prefix_stripped():
    assert _file_matches("utils.py", ["fastapi/utils.py"])
    assert _file_matches("dependencies/utils.py", ["fastapi/dependencies/utils.py"])


def test_no_false_positive_on_nested_basename():
    # _compat/v2.py should not match anything else
    assert _file_matches("_compat/v2.py", ["_compat/v2.py"])
    assert not _file_matches("_compat/v2.py", ["dependencies/v2.py"])
    assert not _file_matches("_compat/v2.py", ["v2.py"])


def test_root_basename_only_matches_root():
    # root utils.py should only match root utils.py, not nested ones
    assert _file_matches("utils.py", ["utils.py"])
    assert not _file_matches("utils.py", ["dependencies/utils.py"])
    assert not _file_matches("utils.py", ["openapi/utils.py"])
    assert not _file_matches("utils.py", ["security/utils.py"])
    # fastapi/ prefix is stripped (fixture prefix), so this IS the root file
    assert _file_matches("utils.py", ["fastapi/utils.py"])


if __name__ == "__main__":
    test_exact_match()
    test_basename_no_path_match()
    test_suffix_match_with_path()
    test_fastapi_prefix_stripped()
    test_no_false_positive_on_nested_basename()
    test_root_basename_only_matches_root()
    print("All tests passed!")
