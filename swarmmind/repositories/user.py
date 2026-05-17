"""Local user and token repository."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import UserDB, UserTokenDB
from swarmmind.services.auth import hash_api_token, hash_password, normalize_email, verify_password
from swarmmind.time_utils import utc_now


class UserRepository:
    """Repository for local users and bearer tokens."""

    def list_all(self) -> list[UserDB]:
        """List users ordered by creation time."""
        with session_scope() as session:
            rows = session.exec(select(UserDB).order_by(UserDB.created_at.asc())).all()
            for row in rows:
                session.expunge(row)
            return list(rows)

    def get(self, user_id: str) -> UserDB:
        """Get a user by ID or raise 404."""
        with session_scope() as session:
            row = session.get(UserDB, user_id)
            if row is None:
                raise HTTPException(status_code=404, detail="User not found")
            session.expunge(row)
            return row

    def get_by_email(self, email: str) -> UserDB:
        """Get a user by normalized email or raise 404."""
        normalized = normalize_email(email)
        with session_scope() as session:
            row = session.exec(select(UserDB).where(UserDB.email == normalized)).first()
            if row is None:
                raise HTTPException(status_code=404, detail="User not found")
            session.expunge(row)
            return row

    def create(
        self,
        *,
        email: str,
        password: str,
        display_name: str | None = None,
        role: str = "member",
        status: str = "active",
    ) -> UserDB:
        """Create a local user."""
        with session_scope() as session:
            row = UserDB(
                user_id=str(uuid.uuid4()),
                email=normalize_email(email),
                display_name=display_name,
                password_hash=hash_password(password),
                role=role,
                status=status,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise HTTPException(status_code=409, detail="User email already exists") from exc
            session.refresh(row)
            session.expunge(row)
            return row

    def update(
        self,
        user_id: str,
        *,
        email: str | None = None,
        password: str | None = None,
        display_name: str | None = None,
        role: str | None = None,
        status: str | None = None,
    ) -> UserDB:
        """Update a local user."""
        with session_scope() as session:
            row = session.get(UserDB, user_id)
            if row is None:
                raise HTTPException(status_code=404, detail="User not found")
            if email is not None:
                row.email = normalize_email(email)
            if password is not None:
                row.password_hash = hash_password(password)
            if display_name is not None:
                row.display_name = display_name
            if role is not None:
                row.role = role
            if status is not None:
                row.status = status
            row.updated_at = utc_now()
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise HTTPException(status_code=409, detail="User email already exists") from exc
            session.refresh(row)
            session.expunge(row)
            return row

    def disable(self, user_id: str) -> None:
        """Disable a user and revoke all active tokens."""
        with session_scope() as session:
            row = session.get(UserDB, user_id)
            if row is None:
                raise HTTPException(status_code=404, detail="User not found")
            row.status = "disabled"
            row.updated_at = utc_now()
            tokens = session.exec(select(UserTokenDB).where(UserTokenDB.user_id == user_id)).all()
            for token in tokens:
                token.status = "revoked"
            session.commit()

    def authenticate(self, *, email: str, password: str) -> UserDB:
        """Validate user credentials and return the user."""
        normalized = normalize_email(email)
        with session_scope() as session:
            row = session.exec(select(UserDB).where(UserDB.email == normalized)).first()
            if row is None or not verify_password(password, row.password_hash):
                raise HTTPException(status_code=401, detail="Invalid email or password")
            if row.status != "active":
                raise HTTPException(status_code=403, detail="User is disabled")
            row.last_login_at = utc_now()
            row.updated_at = utc_now()
            session.commit()
            session.refresh(row)
            session.expunge(row)
            return row

    def create_token(
        self,
        *,
        user_id: str,
        token_hash: str,
        name: str | None = None,
        expires_at: datetime | None = None,
    ) -> UserTokenDB:
        """Store a hashed bearer token."""
        with session_scope() as session:
            user = session.get(UserDB, user_id)
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")
            row = UserTokenDB(
                token_id=str(uuid.uuid4()),
                user_id=user_id,
                token_hash=token_hash,
                name=name,
                expires_at=expires_at,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            session.expunge(row)
            return row

    def resolve_token(self, token: str) -> tuple[UserDB, UserTokenDB]:
        """Resolve a bearer token into active user and token rows."""
        token_hash = hash_api_token(token)
        with session_scope() as session:
            token_row = session.exec(select(UserTokenDB).where(UserTokenDB.token_hash == token_hash)).first()
            if token_row is None or token_row.status != "active":
                raise HTTPException(status_code=401, detail="Invalid API token")
            if token_row.expires_at is not None and token_row.expires_at <= utc_now():
                token_row.status = "revoked"
                session.commit()
                raise HTTPException(status_code=401, detail="API token expired")
            user = session.get(UserDB, token_row.user_id)
            if user is None or user.status != "active":
                raise HTTPException(status_code=403, detail="User is disabled")
            token_row.last_used_at = utc_now()
            session.commit()
            session.refresh(user)
            session.refresh(token_row)
            session.expunge(user)
            session.expunge(token_row)
            return user, token_row

    def revoke_token(self, token_id: str) -> None:
        """Revoke a token by ID."""
        with session_scope() as session:
            row = session.get(UserTokenDB, token_id)
            if row is None:
                raise HTTPException(status_code=404, detail="User token not found")
            row.status = "revoked"
            session.commit()
