from __future__ import annotations

import re
from typing import Any, Literal


def _tokenize(expr: str) -> list[str]:
    """Tokenize expression into identifiers, operators, literals."""
    tokens = []
    i = 0
    while i < len(expr):
        if expr[i].isspace():
            i += 1
            continue
        # Operators
        if expr[i : i + 2] in ("==", "!=", "<=", ">=", "in", "not"):
            if expr[i : i + 5] == "not in":
                tokens.append("not in")
                i += 5
            elif expr[i : i + 2] in ("==", "!=", "<=", ">="):
                tokens.append(expr[i : i + 2])
                i += 2
            else:
                tokens.append(expr[i])
                i += 1
        elif expr[i] in ("=", "<", ">", "(", ")", "&", "|"):
            tokens.append(expr[i])
            i += 1
        # String literal
        elif expr[i] in ("'", '"'):
            quote = expr[i]
            i += 1
            start = i
            while i < len(expr) and expr[i] != quote:
                if expr[i] == "\\":
                    i += 1
                i += 1
            tokens.append(expr[start - 1 : i + 1])
            i += 1
        # Number or identifier
        else:
            start = i
            while i < len(expr) and (expr[i].isalnum() or expr[i] in "._"):
                i += 1
            tokens.append(expr[start:i])
    return tokens


def _parse_value(token: str, context: dict[str, Any], step: dict[str, Any]) -> Any:
    """Parse token as identifier or literal."""
    # String literal
    if token.startswith(("'", '"')):
        return token[1:-1]
    # Number
    if token.replace(".", "").replace("-", "").isdigit():
        if "." in token:
            return float(token)
        return int(token)
    # Boolean
    if token.lower() in ("true", "false"):
        return token.lower() == "true"
    # Identifier: context.xxx or step.xxx
    parts = token.split(".")
    if len(parts) == 2:
        namespace, key = parts
        if namespace == "context":
            return context.get(key)
        elif namespace == "step":
            return step.get(key)
    elif len(parts) == 1:
        # Try context first, then step
        if token in context:
            return context[token]
        return step.get(token)
    return None


def _eval_expr(tokens: list[str], context: dict[str, Any], step: dict[str, Any]) -> bool:
    """Evaluate expression tokens with precedence: () > == != in not in > and > or."""
    if not tokens:
        return False

    # Handle parentheses
    paren_level = 0
    paren_start = -1
    for i, tok in enumerate(tokens):
        if tok == "(":
            if paren_level == 0:
                paren_start = i
            paren_level += 1
        elif tok == ")":
            paren_level -= 1
            if paren_level == 0:
                inner = tokens[paren_start + 1 : i]
                inner_result = _eval_expr(inner, context, step)
                new_tokens = tokens[:paren_start] + [str(inner_result)] + tokens[i + 1 :]
                return _eval_expr(new_tokens, context, step)

    if paren_level != 0:
        return False

    # Handle == != in not in
    i = 0
    while i < len(tokens):
        if tokens[i] in ("==", "!="):
            if i == 0 or i == len(tokens) - 1:
                return False
            left = _parse_value(tokens[i - 1], context, step)
            right = _parse_value(tokens[i + 1], context, step)
            op = tokens[i]
            result = left == right if op == "==" else left != right
            tokens = tokens[: i - 1] + [str(result)] + tokens[i + 2 :]
            i = 0
            continue
        elif i < len(tokens) - 1 and tokens[i : i + 2] == ["not", "in"]:
            if i == 0 or i >= len(tokens) - 2:
                return False
            left = _parse_value(tokens[i - 1], context, step)
            right = _parse_value(tokens[i + 2], context, step)
            if isinstance(right, (list, tuple)):
                result = left not in right
            else:
                result = str(left) not in str(right)
            tokens = tokens[: i - 1] + [str(result)] + tokens[i + 3 :]
            i = 0
            continue
        elif i < len(tokens) - 1 and tokens[i] == "in":
            if i == 0 or i == len(tokens) - 1:
                return False
            left = _parse_value(tokens[i - 1], context, step)
            right = _parse_value(tokens[i + 1], context, step)
            if isinstance(right, (list, tuple)):
                result = left in right
            else:
                result = str(left) in str(right)
            tokens = tokens[: i - 1] + [str(result)] + tokens[i + 2 :]
            i = 0
            continue
        i += 1

    # Handle and
    if "and" in tokens:
        idx = tokens.index("and")
        left = _parse_value(tokens[idx - 1], context, step)
        right = _parse_value(tokens[idx + 1], context, step)
        return bool(left) and bool(right)

    # Handle or
    if "or" in tokens:
        idx = tokens.index("or")
        left = _parse_value(tokens[idx - 1], context, step)
        right = _parse_value(tokens[idx + 1], context, step)
        return bool(left) or bool(right)

    # Single value
    if len(tokens) == 1:
        val = _parse_value(tokens[0], context, step)
        return bool(val)

    return False


def decide(
    preconditions: list[dict[str, Any]], step: dict[str, Any], context: dict[str, Any]
) -> Literal["allow", "block", "require_approval"] | None:
    """
    Evaluate preconditions and return decision.
    Returns None if no precondition matches, or the first matching 'then' value.
    """
    step_name = step.get("name", "")
    for prec in preconditions:
        when = prec.get("when", "")
        then = prec.get("then", "")
        prec_step = prec.get("step")
        
        # If step is specified, only match that step
        if prec_step and prec_step != step_name:
            continue
        
        try:
            tokens = _tokenize(when)
            if _eval_expr(tokens, context, step):
                return then  # type: ignore
        except Exception:
            # On any error, skip this precondition
            continue
    
    return None

