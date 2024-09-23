import pytest
import logging
from argparse import ArgumentParser
from fixattiosync.logger import add_args, setup_logger, get_fix_logger, FixLogger, setLoggerClass


@pytest.fixture(autouse=True)
def set_custom_logger_class():
    # Ensure FixLogger is used globally for all loggers
    setLoggerClass(FixLogger)


@pytest.fixture
def arg_parser():
    return ArgumentParser()


def test_add_args_verbose(arg_parser):
    add_args(arg_parser)
    args = arg_parser.parse_args(["--verbose"])
    assert args.verbose is True
    assert args.trace is False
    assert args.quiet is False


def test_add_args_trace(arg_parser):
    add_args(arg_parser)
    args = arg_parser.parse_args(["--trace"])
    assert args.trace is True
    assert args.verbose is False
    assert args.quiet is False


def test_add_args_quiet(arg_parser):
    add_args(arg_parser)
    args = arg_parser.parse_args(["--quiet"])
    assert args.quiet is True
    assert args.verbose is False
    assert args.trace is False


def test_setup_logger_verbose(monkeypatch):
    monkeypatch.setattr("sys.argv", ["test", "--verbose"])
    setup_logger("fix", force=True)
    logger = get_fix_logger("fix")
    assert logger.level == logging.DEBUG


def test_setup_logger_trace_env(monkeypatch):
    monkeypatch.setenv("FIX_TRACE", "true")
    setup_logger("fix", force=True)
    logger = get_fix_logger("fix")
    assert logger.level == logging.DEBUG - 5  # TRACE level


def test_setup_logger_quiet(monkeypatch):
    monkeypatch.setattr("sys.argv", ["test", "--quiet"])
    setup_logger("fix", force=True)
    logger = get_fix_logger("fix")
    assert logger.level == logging.CRITICAL


@pytest.mark.parametrize(
    "env_var,expected_level",
    [
        ({"FIX_TRACE": "true"}, logging.DEBUG - 5),  # TRACE level
        ({"FIX_VERBOSE": "true"}, logging.DEBUG),
        ({"FIX_QUIET": "true"}, logging.CRITICAL),
    ],
)
def test_setup_logger_with_env_vars(monkeypatch, env_var, expected_level):
    monkeypatch.setenv(list(env_var.keys())[0], list(env_var.values())[0])
    setup_logger("fix", force=True)
    logger = get_fix_logger("fix")
    assert logger.level == expected_level
