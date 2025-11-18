from clue.common.list_utils import flatten_list


def test_flatten_list():
    assert flatten_list([["a"], ["b"], ["c", "d"]]) == ["a", "b", "c", "d"]
