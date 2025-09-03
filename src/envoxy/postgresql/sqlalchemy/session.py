"""Lightweight SQLAlchemy session manager for Envoxy.

Provides a small, explicit API developers can rely on so they don't need to
remember common session lifecycle rules (begin/commit/rollback/close).

Design goals:
- Simple context manager `session_scope()` that commits on success and rolls
  back on error, always closing the session.
- Small decorator factory `transactional()` to wrap functions and inject a
  session parameter named `session`.
- Reasonable engine defaults (pool_pre_ping=True, future=True) but accepts
  a pre-built Engine for advanced setups.
"""
from __future__ import annotations

import logging

from contextlib import contextmanager
from typing import Optional, Callable, Any, Dict

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)


class EnvoxySessionManager:
    """Manage an SQLAlchemy Engine + Session factory for safe usage.

    Example:
        mgr = EnvoxySessionManager(url="postgresql+psycopg2://user@/db")
        with mgr.session_scope() as session:
            session.add(obj)

        # decorator usage
        @mgr.transactional()
        def create_product(sku, session: Session):
            ...
    """

    def __init__(
        self,
        url: Optional[str] = None,
        engine: Optional[Engine] = None,
        engine_kwargs: Optional[Dict[str, Any]] = None,
        session_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        if engine is not None:
            self.engine = engine
        elif url:
            engine_kwargs = engine_kwargs or {}
            # sensible defaults for high-concurrency workloads
            # prefer explicit pool sizing from engine_kwargs or caller config
            engine_kwargs.setdefault("pool_pre_ping", True)
            engine_kwargs.setdefault("future", True)
            # default pool sizing (small sensible defaults — override via engine_kwargs)
            engine_kwargs.setdefault("pool_size", engine_kwargs.get("pool_size", 20))
            engine_kwargs.setdefault("max_overflow", engine_kwargs.get("max_overflow", 10))
            engine_kwargs.setdefault("pool_timeout", engine_kwargs.get("pool_timeout", 30))
            # recycle connections periodically to avoid stale connections
            engine_kwargs.setdefault("pool_recycle", engine_kwargs.get("pool_recycle", 1800))
            # create engine with the given options
            self.engine = create_engine(url, **engine_kwargs)
        else:
            raise ValueError("EnvoxySessionManager requires an engine or a url")

        session_kwargs = session_kwargs or {}
        # don't expire objects on commit by default; makes usage less error-prone
        session_kwargs.setdefault("expire_on_commit", False)
        self._Session = sessionmaker(bind=self.engine, class_=Session, **session_kwargs)

    @contextmanager
    def session_scope(self) -> Session:
        """Provide a transactional scope around a series of operations.

        Commits if the block finishes normally, rolls back and re-raises on
        exception, and always closes the session.
        """
        session: Session = self._Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            logger.debug("Session rolled back due to exception", exc_info=True)
            raise
        finally:
            session.close()

    def transactional(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator factory that runs the wrapped function inside a session.

        The wrapped function will receive a keyword argument named ``session``
        unless a `session` is already provided by the caller. Usage:

            @mgr.transactional()
            def fn(a, b, session: Session):
                ...
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                # if caller provided a session, reuse it
                if "session" in kwargs and isinstance(kwargs["session"], Session):
                    return func(*args, **kwargs)

                with self.session_scope() as session:
                    kwargs.setdefault("session", session)
                    return func(*args, **kwargs)

            # preserve introspection-friendly attributes
            wrapper.__name__ = getattr(func, "__name__", "wrapper")
            wrapper.__doc__ = func.__doc__
            return wrapper

        return decorator

    def dispose(self) -> None:
        """Dispose the underlying Engine's pool and release resources."""
        try:
            self.engine.dispose()
        except Exception:
            logger.exception("Error while disposing engine")
