"""
Minimal pytest-fixture-compatible test runner.

This sandbox has no network access, so `pip install pytest` isn't
possible and the project's real test suite (tests/, run via
`pytest -q`) can't be executed here. This script is NOT a replacement
for pytest — it's a stopgap that understands just enough of
tests/conftest.py's plain-function fixtures (`app`, `client`,
`auth_headers`) to actually execute every test function in tests/
and report pass/fail, so the test suite could be verified in this
sandbox rather than merely inspected by eye.

Run: python3 run_tests_manually.py
In a normal dev environment, use `pytest` instead — see README.
"""
import importlib
import inspect
import os
import sys
import traceback
import types

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath(".."))

# tests/conftest.py does `import pytest` and uses `@pytest.fixture()`.
# pytest itself isn't installable in this offline sandbox, so we inject a
# tiny stand-in module that makes `@pytest.fixture()` a no-op decorator
# (returns the original generator function unchanged) before conftest is
# imported.
_pytest_stub = types.ModuleType("pytest")
_pytest_stub.fixture = lambda *a, **kw: (lambda f: f) if (a and callable(a[0])) is False else (a[0] if a and callable(a[0]) else (lambda f: f))
def _fixture(*args, **kwargs):
    if args and callable(args[0]):
        return args[0]
    def decorator(f):
        return f
    return decorator
_pytest_stub.fixture = _fixture
sys.modules["pytest"] = _pytest_stub

import tests.conftest as conftest_module

FIXTURE_FUNCS = {
    "app": conftest_module.app,
    "client": conftest_module.client,
    "auth_headers": conftest_module.auth_headers,
}


def resolve(name, cache):
    if name in cache:
        return cache[name]
    func = FIXTURE_FUNCS[name]
    params = inspect.signature(func).parameters
    kwargs = {p: resolve(p, cache) for p in params}
    if inspect.isgeneratorfunction(func):
        gen = func(**kwargs)
        value = next(gen)
        cache.setdefault("_generators", []).append(gen)
    else:
        value = func(**kwargs)
    cache[name] = value
    return value


TEST_MODULES = [
    "tests.test_accounts",
    "tests.test_borrowers",
    "tests.test_loans",
    "tests.test_documents",
    "tests.test_lending",
    "tests.test_api_versioning",
    "tests.test_migrations_portability",
    "tests.test_database_indexes",
    "tests.test_security_headers",
]

passed, failed = 0, []

for modname in TEST_MODULES:
    mod = importlib.import_module(modname)
    for name, func in inspect.getmembers(mod, inspect.isfunction):
        if not name.startswith("test_"):
            continue
        cache = {}
        try:
            params = inspect.signature(func).parameters
            kwargs = {p: resolve(p, cache) for p in params}
            func(**kwargs)
            passed += 1
            print(f"PASS  {modname}.{name}")
        except Exception:
            failed.append(f"{modname}.{name}")
            print(f"FAIL  {modname}.{name}")
            traceback.print_exc()
        finally:
            for gen in cache.get("_generators", []):
                try:
                    next(gen)
                except StopIteration:
                    pass

print()
print(f"{passed} passed, {len(failed)} failed")
if failed:
    print("Failed tests:")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
