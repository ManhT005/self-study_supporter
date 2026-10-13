from typing import Protocol
from study_supporter.application.contracts.context import AppContext


class UserRepositoryPort(Protocol):
    def register(self, username: str, password: str) -> int: ...
    def authenticate(self, username: str, password: str) -> int | None: ...


class Authentication:
    def __init__(self, users: UserRepositoryPort):
        self.users = users

    def register(self, username, password) -> AppContext:
        return AppContext(str(self.users.register(username, password)))

    def authenticate(self, username, password) -> AppContext | None:
        user_id = self.users.authenticate(username, password)
        return AppContext(str(user_id)) if user_id is not None else None
