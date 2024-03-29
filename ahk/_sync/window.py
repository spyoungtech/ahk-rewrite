from __future__ import annotations

import sys
import warnings
from typing import Any
from typing import Coroutine
from typing import Literal
from typing import Optional
from typing import overload
from typing import Sequence
from typing import Tuple
from typing import TYPE_CHECKING
from typing import Union

from ahk.message import Position

if sys.version_info < (3, 10):
    from typing_extensions import TypeAlias
else:
    from typing import TypeAlias

if TYPE_CHECKING:
    from .engine import AHK
    from .transport import FutureResult


class WindowNotFoundException(Exception):
    ...


SyncPropertyReturnStr: TypeAlias = str

SyncPropertyReturnInt: TypeAlias = int

SyncPropertyReturnTupleIntInt: TypeAlias = Tuple[int, int]

SyncPropertyReturnBool: TypeAlias = bool

_PROPERTY_DEPRECATION_WARNING_MESSAGE = 'Use of the {0} property is not recommended (in the async API only) and may be removed in a future version. Use the get_{0} method instead.'
_SETTERS_REMOVED_ERROR_MESSAGE = (
    'Use of the {0} property setter is not supported in the async API. Use the set_{0} instead.'
)


class Window:
    def __init__(self, engine: AHK, ahk_id: str):
        self._engine: AHK = engine
        if not ahk_id:
            raise ValueError(f'Invalid ahk_id: {ahk_id!r}')
        self._ahk_id: str = ahk_id

    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__} ahk_id={self._ahk_id}>'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Window):
            return NotImplemented
        return self._ahk_id == other._ahk_id

    def __hash__(self) -> int:
        return hash(self._ahk_id)

    def close(self) -> None:
        self._engine.win_close(
            title=f'ahk_id {self._ahk_id}', detect_hidden_windows=True, title_match_mode=(1, 'Fast')
        )
        return None

    def exists(self) -> bool:
        return self._engine.win_exists(
            title=f'ahk_id {self._ahk_id}', detect_hidden_windows=True, title_match_mode=(1, 'Fast')
        )

    @property
    def id(self) -> str:
        return self._ahk_id

    @property
    def exist(self) -> SyncPropertyReturnBool:
        return self.exists()

    def get_pid(self) -> int:
        pid = self._engine.win_get_pid(
            title=f'ahk_id {self._ahk_id}', detect_hidden_windows=True, title_match_mode=(1, 'Fast')
        )
        if pid is None:
            raise WindowNotFoundException(
                f'Error when trying to get PID of window {self._ahk_id!r}. The window may have been closed before the operation could be completed'
            )
        return pid

    @property
    def pid(self) -> SyncPropertyReturnInt:
        return self.get_pid()

    def get_process_name(self) -> str:
        name = self._engine.win_get_process_name(
            title=f'ahk_id {self._ahk_id}', detect_hidden_windows=True, title_match_mode=(1, 'Fast')
        )
        if name is None:
            raise WindowNotFoundException(
                f'Error when trying to get process name of window {self._ahk_id!r}. The window may have been closed before the operation could be completed'
            )
        return name

    @property
    def process_name(self) -> SyncPropertyReturnStr:
        return self.get_process_name()

    def get_process_path(self) -> str:
        path = self._engine.win_get_process_path(
            title=f'ahk_id {self._ahk_id}', detect_hidden_windows=True, title_match_mode=(1, 'Fast')
        )
        if path is None:
            raise WindowNotFoundException(
                f'Error when trying to get process path of window {self._ahk_id!r}. The window may have been closed before the operation could be completed'
            )
        return path

    @property
    def process_path(self) -> SyncPropertyReturnStr:
        return self.get_process_path()

    def get_minmax(self) -> int:
        minmax = self._engine.win_get_minmax(
            title=f'ahk_id {self._ahk_id}', detect_hidden_windows=True, title_match_mode=(1, 'Fast')
        )
        if minmax is None:
            raise WindowNotFoundException(
                f'Error when trying to get minmax state of window {self._ahk_id}. The window may have been closed before the operation could be completed'
            )
        return minmax

    def get_title(self) -> str:
        title = self._engine.win_get_title(
            title=f'ahk_id {self._ahk_id}', detect_hidden_windows=True, title_match_mode=(1, 'Fast')
        )
        return title

    @property
    def title(self) -> SyncPropertyReturnStr:
        return self.get_title()

    @title.setter
    def title(self, value: str) -> Any:
        self.set_title(value)

    def set_title(self, new_title: str) -> None:
        self._engine.win_set_title(
            title=f'ahk_id {self._ahk_id}',
            detect_hidden_windows=True,
            new_title=new_title,
            title_match_mode=(1, 'Fast'),
        )
        return None

    def list_controls(self) -> Sequence['Control']:
        controls = self._engine.win_get_control_list(
            title=f'ahk_id {self._ahk_id}', detect_hidden_windows=True, title_match_mode=(1, 'Fast')
        )
        if controls is None:
            raise WindowNotFoundException(
                f'Error when trying to enumerate controls for window {self._ahk_id}. The window may have been closed before the operation could be completed'
            )
        return controls

    # fmt: off
    @overload
    def set_always_on_top(self, toggle: Literal['On', 'Off', 'Toggle', 1, -1, 0]) -> None: ...
    @overload
    def set_always_on_top(self, toggle: Literal['On', 'Off', 'Toggle', 1, -1, 0], *, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def set_always_on_top(self, toggle: Literal['On', 'Off', 'Toggle', 1, -1, 0], *, blocking: Literal[True]) -> None: ...
    @overload
    def set_always_on_top(self, toggle: Literal['On', 'Off', 'Toggle', 1, -1, 0], *, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def set_always_on_top(
        self, toggle: Literal['On', 'Off', 'Toggle', 1, -1, 0], *, blocking: bool = True
    ) -> Union[None, FutureResult[None]]:
        return self._engine.win_set_always_on_top(
            toggle=toggle,
            title=f'ahk_id {self._ahk_id}',
            blocking=blocking,
            detect_hidden_windows=True,
            title_match_mode=(1, 'Fast'),
        )

    # fmt: off
    @overload
    def is_always_on_top(self) -> bool: ...
    @overload
    def is_always_on_top(self, *, blocking: Literal[False]) -> FutureResult[Optional[bool]]: ...
    @overload
    def is_always_on_top(self, *, blocking: Literal[True]) -> bool: ...
    @overload
    def is_always_on_top(self, *, blocking: bool = True) -> Union[bool, FutureResult[Optional[bool]]]: ...
    # fmt: on
    def is_always_on_top(self, *, blocking: bool = True) -> Union[bool, FutureResult[Optional[bool]]]:
        args = [f'ahk_id {self._ahk_id}']
        resp = self._engine._transport.function_call(
            'AHKWinIsAlwaysOnTop', args, blocking=blocking
        )  # XXX: maybe shouldn't access transport directly?
        if resp is None:
            raise WindowNotFoundException(
                f'Error when trying to get always on top style for window {self._ahk_id}. The window may have been closed before the operation could be completed'
            )
        return resp

    @property
    def always_on_top(self) -> SyncPropertyReturnBool:
        return self.is_always_on_top()

    @always_on_top.setter
    def always_on_top(self, toggle: Literal['On', 'Off', 'Toggle', 1, -1, 0]) -> Any:
        self.set_always_on_top(toggle)

    # fmt: off
    @overload
    def send(self, keys: str) -> None: ...
    @overload
    def send(self, keys: str, *, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def send(self, keys: str, *, blocking: Literal[True]) -> None: ...
    @overload
    def send(self, keys: str, *, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def send(self, keys: str, *, blocking: bool = True) -> Union[None, FutureResult[None]]:
        return self._engine.control_send(
            keys=keys,
            title=f'ahk_id {self._ahk_id}',
            blocking=blocking,
            detect_hidden_windows=True,
            title_match_mode=(1, 'Fast'),
        )

    # fmt: off
    @overload
    def get_text(self) -> str: ...
    @overload
    def get_text(self, *, blocking: Literal[False]) -> FutureResult[str]: ...
    @overload
    def get_text(self, *, blocking: Literal[True]) -> str: ...
    @overload
    def get_text(self, *, blocking: bool = True) -> Union[str, FutureResult[str]]: ...
    # fmt: on
    def get_text(self, *, blocking: bool = True) -> Union[str, FutureResult[str]]:
        return self._engine.win_get_text(
            title=f'ahk_id {self._ahk_id}', blocking=blocking, detect_hidden_windows=True, title_match_mode=(1, 'Fast')
        )

    @property
    def text(self) -> SyncPropertyReturnStr:
        return self.get_text()

    # fmt: off
    @overload
    def get_position(self) -> Position: ...
    @overload
    def get_position(self, blocking: Literal[False]) -> FutureResult[Optional[Position]]: ...
    @overload
    def get_position(self, blocking: Literal[True]) -> Position: ...
    @overload
    def get_position(self, blocking: bool = True) -> Union[Position, FutureResult[Optional[Position]]]: ...
    # fmt: on
    def get_position(self, blocking: bool = True) -> Union[Position, FutureResult[Optional[Position]]]:
        resp = self._engine.win_get_position(
            title=f'ahk_id {self._ahk_id}',
            blocking=blocking,
            detect_hidden_windows=True,
            title_match_mode=(1, 'Fast'),
        )
        if resp is None:
            raise WindowNotFoundException(
                f'Error when trying to get position for window {self._ahk_id}. The window may have been closed before the operation could be completed'
            )
        return resp


class Control:
    def __init__(self, window: Window, hwnd: str, control_class: str):
        self.window: Window = window
        self.hwnd: str = hwnd
        self.control_class: str = control_class
        self._engine = window._engine

    # fmt: off
    @overload
    def click(self, *, button: Literal['L', 'R', 'M', 'LEFT', 'RIGHT', 'MIDDLE'] = 'L', click_count: int = 1, options: str = '') -> None: ...
    @overload
    def click(self, *, button: Literal['L', 'R', 'M', 'LEFT', 'RIGHT', 'MIDDLE'] = 'L', click_count: int = 1, options: str = '', blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def click(self, *, button: Literal['L', 'R', 'M', 'LEFT', 'RIGHT', 'MIDDLE'] = 'L', click_count: int = 1, options: str = '', blocking: Literal[True]) -> None: ...
    @overload
    def click(self, *, button: Literal['L', 'R', 'M', 'LEFT', 'RIGHT', 'MIDDLE'] = 'L', click_count: int = 1, options: str = '', blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def click(
        self,
        *,
        button: Literal['L', 'R', 'M', 'LEFT', 'RIGHT', 'MIDDLE'] = 'L',
        click_count: int = 1,
        options: str = '',
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        return self._engine.control_click(
            button=button,
            control=self.control_class,
            click_count=click_count,
            options=options,
            title=f'ahk_id {self.window._ahk_id}',
            title_match_mode=(1, 'Fast'),
            detect_hidden_windows=True,
            blocking=blocking,
        )

    # fmt: off
    @overload
    def send(self, keys: str) -> None: ...
    @overload
    def send(self, keys: str, *, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def send(self, keys: str, *, blocking: Literal[True]) -> None: ...
    @overload
    def send(self, keys: str, *, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def send(self, keys: str, *, blocking: bool = True) -> Union[None, FutureResult[None]]:
        return self._engine.control_send(
            keys=keys,
            control=self.control_class,
            title=f'ahk_id {self.window._ahk_id}',
            blocking=blocking,
            detect_hidden_windows=True,
            title_match_mode=(1, 'Fast'),
        )

    def get_text(self, blocking: bool = True) -> Union[str, FutureResult[str]]:
        return self._engine.control_get_text(
            control=self.control_class,
            title=f'ahk_id {self.window._ahk_id}',
            blocking=blocking,
            detect_hidden_windows=True,
            title_match_mode=(1, 'Fast'),
        )

    # fmt: off
    @overload
    def get_position(self) -> Position: ...
    @overload
    def get_position(self, blocking: Literal[False]) -> FutureResult[Position]: ...
    @overload
    def get_position(self, blocking: Literal[True]) -> Position: ...
    @overload
    def get_position(self, blocking: bool = True) -> Union[Position, FutureResult[Position]]: ...
    # fmt: on
    def get_position(self, blocking: bool = True) -> Union[Position, FutureResult[Position]]:
        return self._engine.control_get_position(
            control=self.control_class,
            title=f'ahk_id {self.window._ahk_id}',
            blocking=blocking,
            detect_hidden_windows=True,
            title_match_mode=(1, 'Fast'),
        )

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} window={self.window!r}, control_hwnd={self.hwnd!r}, control_class={self.control_class!r}>'
