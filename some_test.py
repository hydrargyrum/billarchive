#!/usr/bin/env pytest

import billarchive.billarchive


def test_formatter():
    formatter = billarchive.billarchive.FilenameFormatter()

    assert formatter.format("{}/{}", 1, 2) == "1/2"
    assert formatter.format("{}/{}", "1", "2") == "1/2"
    assert formatter.format("{}/{}", "foo", "bar") == "foo/bar"
    assert formatter.format("{}/{}", "foo-foo_foo", "bar") == "foo-foo_foo/bar"

    assert formatter.format("{}/{}", "foo/foo", "bar") == "foo_slash_foo/bar"
    assert formatter.format("{!u}/{}", "foo/foo", "bar") == "foo/foo/bar"

    assert formatter.format("{}/{}", "foo.foo", "bar") == "foo.foo/bar"
    assert formatter.format("{}/{}", ".foo.foo", "bar") == "dot_foo.foo/bar"
    assert formatter.format("{!u}/{}", ".foo.foo", "bar") == ".foo.foo/bar"
