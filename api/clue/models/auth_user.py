from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class UserRole(StrEnum):
    """Roles understood by Clue after mapping trusted identity-provider claims."""

    USER = "user"
    ADMIN = "admin"


class Privilege(StrEnum):
    """Operations granted to an authenticated principal."""

    READ = "R"
    WRITE = "W"


class APIKeyConf(BaseModel):
    """Server-side API key and its access policy."""

    model_config = ConfigDict(extra="forbid")

    roles: set[UserRole] = Field(default_factory=lambda: {UserRole.USER})
    privileges: set[Privilege] = Field(
        default_factory=lambda: {
            Privilege.READ,
            Privilege.WRITE,
        }
    )
    secret: str


class AuthUser(BaseModel):
    """Normalized identity used after successful authentication."""

    model_config = ConfigDict(extra="forbid")

    uname: str
    name: str | None = None
    email: str | None = None
    classification: str
    groups: list[str] = Field(default_factory=list)
    roles: set[UserRole] = Field(default_factory=lambda: {UserRole.USER})
    avatar: str | None = None


class AuthResult(BaseModel):
    """Normalized identity and effective privileges from authentication."""

    user: AuthUser
    privileges: set[Privilege]
