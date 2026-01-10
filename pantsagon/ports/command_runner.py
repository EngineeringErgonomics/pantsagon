from typing import Protocol
from dataclasses import dataclass


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


class CommandRunnerPort(Protocol):
    def run(self, args: list[str]) -> CommandResult: ...
