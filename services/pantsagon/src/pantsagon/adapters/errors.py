from dataclasses import dataclass

from pantsagon.domain.json_types import JsonDict


@dataclass
class AdapterError(Exception):
    message: str
    details: JsonDict | None = None
    hint: str | None = None
    cause: Exception | None = None

    def __str__(self) -> str:
        return self.message


class PackFetchError(AdapterError):
    pass


class PackReadError(AdapterError):
    pass


class PackParseError(AdapterError):
    pass


class RendererTemplateError(AdapterError):
    pass


class RendererExecutionError(AdapterError):
    pass


class WorkspaceTransactionError(AdapterError):
    pass


class WorkspaceCommitError(AdapterError):
    pass


class CommandNotFound(AdapterError):
    pass


class CommandFailed(AdapterError):
    pass


class CommandTimeout(AdapterError):
    pass
