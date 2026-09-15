"""Shared test doubles for unit tests.

Extracted from test_product_service.py / test_store_service.py (DRY):
FakeSession was duplicated verbatim. Domain repository fakes stay in their
test modules — their contracts differ per domain.
"""


class FakeSession:
    """Session double: counts commits/rollbacks, can simulate a flush conflict."""

    def __init__(self, flush_error: Exception | None = None) -> None:
        self._flush_error = flush_error
        self.commits = 0
        self.rollbacks = 0

    def flush(self) -> None:
        if self._flush_error is not None:
            raise self._flush_error

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1
