import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.main import readiness


class _ScalarRows:
    def __init__(self, values: list[str]) -> None:
        self.values = values

    def scalars(self) -> "_ScalarRows":
        return self

    def all(self) -> list[str]:
        return self.values


class _FakeSession:
    def __init__(self, results: list[object]) -> None:
        self.results = results

    async def execute(self, _statement):
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class ReadinessTests(unittest.IsolatedAsyncioTestCase):
    @patch(
        "app.main._get_expected_alembic_heads",
        return_value=frozenset({"current-head"}),
    )
    async def test_ready_when_database_is_connected_and_schema_is_current(
        self,
        _expected_heads,
    ) -> None:
        session = _FakeSession([object(), _ScalarRows(["current-head"])])

        response = await readiness(session)

        self.assertEqual(
            response,
            {
                "status": "ready",
                "database": "connected",
                "schema": "current",
            },
        )

    @patch(
        "app.main._get_expected_alembic_heads",
        return_value=frozenset({"current-head"}),
    )
    async def test_returns_503_when_schema_is_not_current(
        self,
        _expected_heads,
    ) -> None:
        session = _FakeSession([object(), _ScalarRows(["old-head"])])

        with self.assertRaises(HTTPException) as raised:
            await readiness(session)

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail["database"], "connected")
        self.assertEqual(raised.exception.detail["schema"], "out_of_date")

    async def test_returns_503_when_database_is_unavailable(self) -> None:
        session = _FakeSession([SQLAlchemyError("connection failed")])

        with self.assertRaises(HTTPException) as raised:
            await readiness(session)

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail["database"], "unavailable")
        self.assertEqual(raised.exception.detail["schema"], "unknown")

    async def test_returns_503_when_schema_metadata_is_unavailable(self) -> None:
        session = _FakeSession(
            [
                object(),
                SQLAlchemyError("alembic_version is unavailable"),
            ]
        )

        with self.assertRaises(HTTPException) as raised:
            await readiness(session)

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail["database"], "connected")
        self.assertEqual(raised.exception.detail["schema"], "unavailable")


if __name__ == "__main__":
    unittest.main()
