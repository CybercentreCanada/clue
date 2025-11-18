import logging

from clue.plugin.helpers.trino import __prepare_query


def test_prepare_query_success():
    assert __prepare_query("select * from table", "row_id = ?", 5, ["1"]) == (
        "select * from table WHERE (row_id = ?) LIMIT 5",
        ["1"],
    )

    assert __prepare_query("select * from table", "row_id = ? or ?", 5, [["1", "2"]]) == (
        "select * from table WHERE (row_id = ? or ?) LIMIT 5",
        ["1", "2"],
    )

    assert __prepare_query("select * from table", "row_id = ?", 5, ["1", "2"]) == (
        "select * from table WHERE (row_id = ?) OR (row_id = ?) LIMIT 5",
        ["1", "2"],
    )


def test_prepare_query_error(caplog):
    with caplog.at_level(logging.ERROR):
        __prepare_query("select * from table", "row_id = ?", 5, [["1"]])

        assert "but you provided a list of arguments" in caplog.text

    caplog.clear()

    with caplog.at_level(logging.ERROR):
        __prepare_query("select * from table", "row_id = ? or ?", 5, ["1"])

        assert "but you did not provide a list of arguments" in caplog.text

    caplog.clear()

    with caplog.at_level(logging.ERROR):
        __prepare_query("select * from table", "row_id = ? or ?", 5, [["1"]])

        assert "list of arguments of length 1." in caplog.text

    caplog.clear()
