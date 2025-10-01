import re
from copy import deepcopy
from pathlib import Path

import pytest
from baseconv import BASE62_ALPHABET

from clue.common import forge
from clue.common.classification import InvalidClassification
from clue.common.dict_utils import (
    flatten,
    get_recursive_delta,
    recursive_update,
    unflatten,
)
from clue.common.regex import DOMAIN_REGEX
from clue.common.str_utils import safe_str
from clue.common.uid import LONG, MEDIUM, SHORT, TINY, get_id_from_data, get_random_id


def test_classification():
    yml_config = Path(__file__).parent.parent.parent / "classification.yml"

    cl_engine = forge.get_classification(yml_config=str(yml_config))

    u = "U//REL DEPTS"
    r = "R//GOD//G1"

    assert cl_engine.normalize_classification(r, long_format=True) == "RESTRICTED//ADMIN//ANY/GROUP 1"
    assert cl_engine.is_accessible(r, u)
    assert cl_engine.is_accessible(u, u)
    assert not cl_engine.is_accessible(u, r)
    assert cl_engine.min_classification(u, r) == "UNRESTRICTED//REL TO DEPARTMENT 1, DEPARTMENT 2"
    assert cl_engine.max_classification(u, r) == "RESTRICTED//ADMIN//ANY/GROUP 1"
    assert cl_engine.intersect_user_classification(u, r) == "UNRESTRICTED//ANY"
    assert cl_engine.normalize_classification("UNRESTRICTED//REL TO DEPARTMENT 2", long_format=False) == "U//REL D2"
    with pytest.raises(InvalidClassification):
        cl_engine.normalize_classification("D//BOB//REL TO SOUP")

    c1 = "U//REL D1"
    c2 = "U//REL D2"
    assert cl_engine.min_classification(c1, c2) == "UNRESTRICTED//REL TO DEPARTMENT 1, DEPARTMENT 2"
    assert cl_engine.intersect_user_classification(c1, c2) == "UNRESTRICTED"
    with pytest.raises(InvalidClassification):
        cl_engine.max_classification(c1, c2)

    dyn1 = "U//TEST"
    dyn2 = "U//GOD//TEST"
    dyn3 = "U//TEST2"
    assert not cl_engine.is_valid(dyn1)
    assert not cl_engine.is_valid(dyn2)
    assert not cl_engine.is_valid(dyn3)
    with pytest.raises(InvalidClassification):
        cl_engine.normalize_classification(dyn1, long_format=False)
    with pytest.raises(InvalidClassification):
        cl_engine.normalize_classification(dyn2, long_format=False)
    with pytest.raises(InvalidClassification):
        cl_engine.normalize_classification(dyn3, long_format=False)

    cl_engine.dynamic_groups = True
    assert not cl_engine.is_valid(dyn1)
    assert not cl_engine.is_valid(dyn2)
    assert not cl_engine.is_valid(dyn3)
    with pytest.raises(InvalidClassification):
        cl_engine.normalize_classification(dyn1, long_format=False)
    with pytest.raises(InvalidClassification):
        cl_engine.normalize_classification(dyn2, long_format=False)
    with pytest.raises(InvalidClassification):
        cl_engine.normalize_classification(dyn3, long_format=False)
    with pytest.raises(InvalidClassification):
        cl_engine.is_accessible(dyn2, dyn1)
    with pytest.raises(InvalidClassification):
        cl_engine.is_accessible(dyn1, dyn2)
    with pytest.raises(InvalidClassification):
        cl_engine.is_accessible(dyn3, dyn1)
    with pytest.raises(InvalidClassification):
        cl_engine.is_accessible(dyn1, dyn3)
    with pytest.raises(InvalidClassification):
        cl_engine.intersect_user_classification(dyn1, dyn1)
    with pytest.raises(InvalidClassification):
        cl_engine.max_classification(dyn1, dyn2)

    cl_engine.dynamic_groups = False
    dyn1 = "U//REL TEST"
    dyn2 = "U//GOD//REL TEST"
    dyn3 = "U//REL TEST2"
    assert not cl_engine.is_valid(dyn1)
    assert not cl_engine.is_valid(dyn2)
    with pytest.raises(InvalidClassification):
        assert cl_engine.normalize_classification(dyn1, long_format=False)
    with pytest.raises(InvalidClassification):
        assert cl_engine.normalize_classification(dyn2, long_format=False)
    cl_engine.dynamic_groups = True
    assert cl_engine.is_valid(dyn1)
    assert cl_engine.is_valid(dyn2)
    assert cl_engine.is_valid(dyn3)
    assert cl_engine.is_accessible(dyn2, dyn1)
    assert not cl_engine.is_accessible(dyn1, dyn2)
    assert not cl_engine.is_accessible(dyn3, dyn1)
    assert not cl_engine.is_accessible(dyn1, dyn3)
    assert cl_engine.intersect_user_classification(dyn1, dyn1) == "UNRESTRICTED//REL TO TEST"
    assert cl_engine.max_classification(dyn1, dyn2) == "UNRESTRICTED//ADMIN//REL TO TEST"
    assert cl_engine.normalize_classification(dyn1, long_format=True) == "UNRESTRICTED//REL TO TEST"
    assert cl_engine.normalize_classification(dyn1, long_format=False) == "U//REL TEST"


def test_dict_flatten():
    src = {"a": {"b": {"c": 1}}, "b": {"d": {2}}}

    flat_src = flatten(src)
    assert src == unflatten(flat_src)
    assert list(flat_src.keys()) == ["a.b.c", "b.d"]


def test_dict_recursive():
    src = {"a": {"b": {"c": 1}}, "b": {"d": 2}}
    add = {"a": {"d": 3, "b": {"c": 4}}}
    dest = recursive_update(deepcopy(src), add)
    assert dest["a"]["b"]["c"] == 4
    assert dest["a"]["d"] == 3
    assert dest["b"]["d"] == 2

    delta = get_recursive_delta(src, dest)
    assert add == delta


def test_safe_str():
    assert safe_str("hello") == "hello"
    assert safe_str("hello\x00") == "hello\\x00"
    assert safe_str("\xf1\x90\x80\x80") == "\xf1\x90\x80\x80"
    assert safe_str("\xc2\x90") == "\xc2\x90"
    assert safe_str("\xc1\x90") == "\xc1\x90"


def test_uid():
    test_data = "test" * 1000
    rid = get_random_id()
    id_test = get_id_from_data(test_data)
    id_test_l = get_id_from_data(test_data, length=LONG)
    id_test_m = get_id_from_data(test_data, length=MEDIUM)
    id_test_s = get_id_from_data(test_data, length=SHORT)
    id_test_t = get_id_from_data(test_data, length=TINY)
    assert 23 > len(rid) >= 20
    assert 23 > len(id_test) >= 20
    assert 44 > len(id_test_l) >= 41
    assert 23 > len(id_test_m) >= 20
    assert 13 > len(id_test_s) >= 10
    assert 8 > len(id_test_t) >= 5
    assert id_test == id_test_m
    for c_id in [rid, id_test, id_test_l, id_test_m, id_test_s, id_test_t]:
        for x in c_id:
            assert x in BASE62_ALPHABET


def test_domain_regex():
    test_domain_root = "my--domain.com"

    test_domain_subdomain = "my-----subdomain.domain.com"

    assert re.match(DOMAIN_REGEX, test_domain_root)

    assert re.match(DOMAIN_REGEX, test_domain_subdomain)
