import asyncio.subprocess
import atexit
import io
import os
import subprocess
import typing
import warnings
from abc import ABC
from abc import abstractmethod
from io import BytesIO
from shutil import which
from typing import Any
from typing import Literal
from typing import Optional
from typing import Protocol
from typing import runtime_checkable

from ahk.message import BooleanResponseMessage
from ahk.message import CoordinateResponseMessage
from ahk.message import IntegerResponseMessage
from ahk.message import NoValueResponseMessage
from ahk.message import RequestMessage
from ahk.message import ResponseMessage
from ahk.message import StringResponseMessage
from ahk.message import TupleResponseMessage
from ahk.message import WindowIDListResponseMessage

DEFAULT_EXECUTABLE_PATH = r'C:\Program Files\AutoHotkey\AutoHotkey.exe'



SyncIOProcess = subprocess.Popen[bytes]


@runtime_checkable
class Killable(Protocol):
    def kill(self) -> None:
        ...


def kill(proc: Killable) -> None:
    proc.kill()


class SyncAHKProcess:
    def __init__(self, runargs: list[str]):
        self.runargs = runargs
        self._proc: Optional[SyncIOProcess] = None

    def start(self) -> None:
        self._proc = sync_create_process(self.runargs)
        return None


    def drain_stdin(self) -> None:
        assert isinstance(self._proc, subprocess.Popen)
        self._proc.stdin.flush()
        return None

    def write(self, content: bytes) -> None:
        assert self._proc is not None
        assert self._proc.stdin is not None
        self._proc.stdin.write(content)

    def readline(self) -> bytes:
        assert self._proc is not None
        assert self._proc.stdout is not None
        return self._proc.stdout.readline()




def sync_create_process(runargs: list[str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(runargs, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE)


class AhkExecutableNotFoundError(EnvironmentError):
    pass


def _resolve_executable_path(executable_path: str = '') -> str:
    if not executable_path:
        executable_path = (
            os.environ.get('AHK_PATH', '')
            or which('AutoHotkey.exe')
            or which('AutoHotkeyU64.exe')
            or which('AutoHotkeyU32.exe')
            or which('AutoHotkeyA32.exe')
            or ''
        )

    if not executable_path:
        if os.path.exists(DEFAULT_EXECUTABLE_PATH):
            executable_path = DEFAULT_EXECUTABLE_PATH

    if not executable_path:
        raise AhkExecutableNotFoundError(
            'Could not find AutoHotkey.exe on PATH. '
            'Provide the absolute path with the `executable_path` keyword argument '
            'or in the AHK_PATH environment variable. '
            'You may be able to resolve this error by installing the binary extra: pip install "ahk[binary]"'
        )

    if not os.path.exists(executable_path):
        raise AhkExecutableNotFoundError(f"executable_path does not seems to exist: '{executable_path}' not found")

    if os.path.isdir(executable_path):
        raise AhkExecutableNotFoundError(
            f'The path {executable_path} appears to be a directory, but should be a file.'
            ' Please specify the *full path* to the autohotkey.exe executable file'
        )

    if not executable_path.endswith('.exe'):
        warnings.warn(
            'executable_path does not appear to have a .exe extension. This may be the result of a misconfiguration.'
        )

    return executable_path


class Transport(ABC):
    _started: bool = False

    def init(self) -> None:
        self._started = True
        return None

    @typing.overload
    def function_call(
        self, function_name: Literal['ImageSearch'], args: Optional[list[str]] = None
    ) -> TupleResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['PixelGetColor'], args: Optional[list[str]] = None
    ) -> StringResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['PixelSearch'], args: Optional[list[str]] = None
    ) -> CoordinateResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['MouseGetPos'], args: Optional[list[str]] = None
    ) -> CoordinateResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['AHKKeyState'], args: Optional[list[str]] = None
    ) -> BooleanResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['MouseMove'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['CoordMode'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['Click'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['MouseClickDrag'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    # @typing.overload
    # async def function_call(self, function_name: Literal['RegRead'], args: Optional[list[str]] = None) -> :
    #     ...
    #
    # @typing.overload
    # async def function_call(self, function_name: Literal['SetRegView'], args: Optional[list[str]] = None):
    #     ...
    #
    # @typing.overload
    # async def function_call(self, function_name: Literal['RegWrite'], args: Optional[list[str]] = None):
    #     ...
    #
    # @typing.overload
    # async def function_call(self, function_name: Literal['RegDelete'], args: Optional[list[str]] = None):
    #     ...

    @typing.overload
    def function_call(
        self, function_name: Literal['KeyWait'], args: Optional[list[str]] = None
    ) -> IntegerResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['SetKeyDelay'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['Send'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['SendRaw'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['SendInput'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['SendEvent'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['SendPlay'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['SetCapsLockState'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    # @typing.overload
    # async def function_call(self, function_name: Literal['HideTrayTip'], args: Optional[list[str]] = None) -> NoValueResponseMessage:
    #     ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinGetTitle'], args: Optional[list[str]] = None
    ) -> StringResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinGetClass'], args: Optional[list[str]] = None
    ) -> StringResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinGetText'], args: Optional[list[str]] = None
    ) -> StringResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinActivate'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinActivateBottom'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinClose'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinHide'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinKill'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinMaximize'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinMinimize'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinRestore'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinShow'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    #
    # @typing.overload
    # async def function_call(self, function_name: Literal['WinWait'], args: Optional[list[str]] = None) -> StringResponseMessage:
    #     ...
    #
    # @typing.overload
    # async def function_call(self, function_name: Literal['WinWaitActive'], args: Optional[list[str]] = None) -> StringResponseMessage:
    #     ...
    #
    # @typing.overload
    # async def function_call(self, function_name: Literal['WinWaitNotActive'], args: Optional[list[str]] = None) -> StringResponseMessage:
    #     ...
    #
    # @typing.overload
    # async def function_call(self, function_name: Literal['WinWaitClose'], args: Optional[list[str]] = None) -> :
    #     ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WindowList'], args: Optional[list[str]] = None
    ) -> WindowIDListResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinSend'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinSendRaw'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['ControlSend'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    # @typing.overload
    # async def function_call(self, function_name: Literal['BaseCheck'], args: Optional[list[str]] = None) -> :
    #     ...

    @typing.overload
    def function_call(
        self, function_name: Literal['FromMouse'], args: Optional[list[str]] = None
    ) -> StringResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinGet'], args: Optional[list[str]] = None
    ) -> StringResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinSet'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinSetTitle'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinIsAlwaysOnTop'], args: Optional[list[str]] = None
    ) -> BooleanResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['WinClick'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['AHKWinMove'], args: Optional[list[str]] = None
    ) -> NoValueResponseMessage:
        ...

    @typing.overload
    def function_call(
        self, function_name: Literal['AHKWinGetPos'], args: Optional[list[str]] = None
    ) -> TupleResponseMessage:
        ...

    def function_call(self, function_name: str, args: Optional[list[str]] = None) -> ResponseMessage:
        if not self._started:
            self.init()
        request = RequestMessage(function_name=function_name, args=args)
        return self.send(request)

    @abstractmethod
    def send(self, request: RequestMessage) -> ResponseMessage:
        return NotImplemented


class DaemonProcessTransport(Transport):
    def __init__(self, executable_path: str = ''):
        self._proc: Optional[SyncAHKProcess]
        self._proc = None
        self._executable_path: str = _resolve_executable_path(executable_path=executable_path)

    def init(self) -> None:
        self.start()
        super().init()
        return None

    def start(self) -> None:
        assert self._proc is None, 'cannot start a process twice'
        runargs = [self._executable_path, '/CP65001', '/ErrorStdOut', 'ahk\\daemon.ahk']  # TODO: build this dynamically
        self._proc = SyncAHKProcess(runargs=runargs)
        self._proc.start()

    def send(self, request: RequestMessage) -> ResponseMessage:
        newline = '\n'

        msg = f"{request.function_name}{',' if request.args else ''}{','.join(arg.replace(newline, '`n') for arg in request.args)}\n".encode(
            'utf-8'
        )
        assert self._proc is not None
        self._proc.write(msg)
        self._proc.drain_stdin()
        tom = self._proc.readline()
        num_lines = self._proc.readline()
        content_buffer = BytesIO()
        content_buffer.write(tom)
        content_buffer.write(num_lines)
        for _ in range(int(num_lines) + 1):
            part = self._proc.readline()
            content_buffer.write(part)
        content = content_buffer.getvalue()[:-1]
        response = ResponseMessage.from_bytes(content)
        return response
