"""Narrow mongomock gap shim; this does NOT certify real MongoDB execution."""
from datetime import datetime
from unittest.mock import patch
import mongomock.aggregate as aggregate


def install_type_operator(case):
    original = aggregate._Parser._handle_type_operator

    def handle(parser, operator, value):
        if operator != "$type":
            return original(parser, operator, value)
        try:
            result = parser.parse(value)
        except KeyError:
            return "missing"
        if result is None:
            return "null"
        if isinstance(result, datetime):
            return "date"
        return "non-date"  # The production expression tests only equality to date.

    operators = patch.object(aggregate, "type_operators", [*aggregate.type_operators, "$type"])
    handler = patch.object(aggregate._Parser, "_handle_type_operator", handle)
    operators.start()
    handler.start()
    case.addCleanup(operators.stop)
    case.addCleanup(handler.stop)
