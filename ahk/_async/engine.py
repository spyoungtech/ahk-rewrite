from __future__ import annotations

import asyncio
import time
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List
from typing import Literal
from typing import NoReturn
from typing import Optional
from typing import overload
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import Union

from ..keys import Key
from .transport import AsyncDaemonProcessTransport
from .transport import AsyncFutureResult
from .transport import AsyncTransport
from .window import AsyncControl
from .window import AsyncWindow


async_sleep = asyncio.sleep  # unasync: remove
sleep = time.sleep

CoordModeTargets = Union[Literal['ToolTip'], Literal['Pixel'], Literal['Mouse'], Literal['Caret'], Literal['Menu']]
CoordModeRelativeTo = Union[Literal['Screen'], Literal['Relative'], Literal['Window'], Literal['Client']]
WinGetFunctions = Literal[
    Literal['AHKWinGetID'],
    Literal['AHKWinGetIDLast'],
    Literal['AHKWinGetPID'],
    Literal['AHKWinGetProcessName'],
    Literal['AHKWinGetProcessPath'],
    Literal['AHKWinGetCount'],
    Literal['AHKWinGetList'],
    Literal['AHKWinGetMinMax'],
    Literal['AHKWinGetControlList'],
    Literal['AHKWinGetControlListHwnd'],
    Literal['AHKWinGetTransparent'],
    Literal['AHKWinGetTransColor'],
    Literal['AHKWinGetStyle'],
    Literal['AHKWinGetExStyle'],
]
CoordMode = Union[CoordModeTargets, Tuple[CoordModeTargets, CoordModeRelativeTo]]


class AsyncAHK:
    def __init__(
        self,
        *,
        TransportClass: Optional[Type[AsyncTransport]] = None,
        transport_options: Optional[Dict[str, Any]] = None,
    ):
        if transport_options is None:
            transport_options = {}
        if TransportClass is None:
            TransportClass = AsyncDaemonProcessTransport
        assert TransportClass is not None
        transport = TransportClass(**transport_options)
        self._transport: AsyncTransport = transport

    def add_hotkey(
        self, hotkey: str, callback: Callable[[], Any], ex_handler: Optional[Callable[[str, Exception], Any]] = None
    ) -> None:
        return self._transport.add_hotkey(hotkey=hotkey, callback=callback, ex_handler=ex_handler)

    def add_hotstring(self, trigger_string: str, replacement: str) -> None:
        return self._transport.add_hotstring(trigger_string=trigger_string, replacement=replacement)

    def start_hotkeys(self) -> None:
        return self._transport.start_hotkeys()

    def stop_hotkeys(self) -> None:
        return self._transport.stop_hotkeys()

    # fmt: off
    @overload
    async def list_windows(self) -> List[AsyncWindow]: ...
    @overload
    async def list_windows(self, *, blocking: Literal[False]) -> Union[List[AsyncWindow], AsyncFutureResult[List[AsyncWindow]]]: ...
    @overload
    async def list_windows(self, *, blocking: Literal[True]) -> List[AsyncWindow]: ...
    # fmt: on
    async def list_windows(
        self, blocking: bool = True
    ) -> Union[List[AsyncWindow], AsyncFutureResult[List[AsyncWindow]]]:
        resp = await self._transport.function_call('WindowList', engine=self, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def get_mouse_position(self, *, blocking: Literal[True]) -> Tuple[int, int]: ...
    @overload
    async def get_mouse_position(self, *, blocking: Literal[False]) -> AsyncFutureResult[Tuple[int, int]]: ...
    @overload
    async def get_mouse_position(self) -> Tuple[int, int]: ...
    # fmt: on
    async def get_mouse_position(
        self, *, blocking: bool = True
    ) -> Union[Tuple[int, int], AsyncFutureResult[Tuple[int, int]]]:
        resp = await self._transport.function_call('MouseGetPos', blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def mouse_move(self, x: Optional[Union[str, int]] = None, y: Optional[Union[str, int]] = None, *, speed: Optional[int] = None, relative: bool = False) -> None: ...
    @overload
    async def mouse_move(self, x: Optional[Union[str, int]] = None, y: Optional[Union[str, int]] = None, *, blocking: Literal[True], speed: Optional[int] = None, relative: bool = False) -> None: ...
    @overload
    async def mouse_move(self, x: Optional[Union[str, int]] = None, y: Optional[Union[str, int]] = None, *, blocking: Literal[False], speed: Optional[int] = None, relative: bool = False, ) -> AsyncFutureResult[None]: ...
    # fmt: on
    async def mouse_move(
        self,
        x: Optional[Union[str, int]] = None,
        y: Optional[Union[str, int]] = None,
        *,
        speed: Optional[int] = None,
        relative: bool = False,
        blocking: bool = True,
    ) -> Union[None, AsyncFutureResult[None]]:
        if relative and (x is None or y is None):
            x = x or 0
            y = y or 0
        elif not relative and (x is None or y is None):
            posx, posy = await self.get_mouse_position()
            x = x or posx
            y = y or posy

        if speed is None:
            speed = 2
        args = [str(x), str(y), str(speed)]
        if relative:
            args.append('R')
        resp = await self._transport.function_call('MouseMove', args, blocking=blocking)
        return resp

    async def a_run_script(self, script_text: str, decode: bool = True, blocking: bool = True, **runkwargs: Any) -> str:
        raise NotImplementedError()

    async def get_active_window(self) -> Union[AsyncWindow, None]:
        raise NotImplementedError()

    async def find_windows(
        self, func: Optional[Callable[[AsyncWindow], bool]] = None, **kwargs: Any
    ) -> Iterable[AsyncWindow]:
        raise NotImplementedError()

    async def find_windows_by_class(self, class_name: str, exact: bool = False) -> Iterable[AsyncWindow]:
        raise NotImplementedError()

    async def find_windows_by_text(self, text: str, exact: bool = False) -> Iterable[AsyncWindow]:
        raise NotImplementedError()

    async def find_windows_by_title(self, title: str, exact: bool = False) -> Iterable[AsyncWindow]:
        raise NotImplementedError()

    async def get_volume(self, device_number: int = 1) -> float:
        raise NotImplementedError()

    # fmt: off
    @overload
    async def key_down(self, key: Union[str, Key]) -> None: ...
    @overload
    async def key_down(self, key: Union[str, Key], *, blocking: Literal[True]) -> None: ...
    @overload
    async def key_down(self, key: Union[str, Key], *, blocking: Literal[False]) -> AsyncFutureResult[None]: ...
    # fmt: on
    async def key_down(self, key: Union[str, Key], *, blocking: bool = True) -> Union[None, AsyncFutureResult[None]]:
        if isinstance(key, str):
            key = Key(key_name=key)
        if blocking:
            return await self.send_input(key.DOWN, blocking=True)
        else:
            return await self.send_input(key.DOWN, blocking=False)

    # fmt: off
    @overload
    async def key_press(self, key: Union[str, Key], *, release: bool = True) -> None: ...
    @overload
    async def key_press(self, key: Union[str, Key], *, blocking: Literal[True], release: bool = True) -> None: ...
    @overload
    async def key_press(self, key: Union[str, Key], *, blocking: Literal[False], release: bool = True) -> AsyncFutureResult[None]: ...
    # fmt: on
    async def key_press(
        self, key: Union[str, Key], *, release: bool = True, blocking: bool = True
    ) -> Union[None, AsyncFutureResult[None]]:
        if blocking:
            if release:
                return await self.key_up(key, blocking=True)
            else:
                return None
        else:
            d = await self.key_down(key, blocking=False)
            if release:
                return await self.key_up(key, blocking=False)
            return d

    # fmt: off
    @overload
    async def key_release(self, key: Union[str, Key]) -> None: ...
    @overload
    async def key_release(self, key: Union[str, Key], *, blocking: Literal[True]) -> None: ...
    @overload
    async def key_release(self, key: Union[str, Key], *, blocking: Literal[False]) -> AsyncFutureResult[None]: ...
    # fmt: on
    async def key_release(self, key: Union[str, Key], *, blocking: bool = True) -> Union[None, AsyncFutureResult[None]]:
        if blocking:
            return await self.key_up(key=key, blocking=True)
        else:
            return await self.key_up(key=key, blocking=False)

    async def key_state(self, key_name: str, mode: Optional[Union[Literal['P'], Literal['T']]] = None) -> bool:
        raise NotImplementedError()

    # fmt: off
    @overload
    async def key_up(self, key: Union[str, Key]) -> None: ...
    @overload
    async def key_up(self, key: Union[str, Key], *, blocking: Literal[True]) -> None: ...
    @overload
    async def key_up(self, key: Union[str, Key], *, blocking: Literal[False]) -> AsyncFutureResult[None]: ...
    # fmt: on
    async def key_up(self, key: Union[str, Key], blocking: bool = True) -> Union[None, AsyncFutureResult[None]]:
        if isinstance(key, str):
            key = Key(key_name=key)
        if blocking:
            return await self.send_input(key.UP, blocking=True)
        else:
            return await self.send_input(key.UP, blocking=False)

    # fmt: off
    @overload
    async def key_wait(self, key_name: str, *, timeout: Optional[int] = None, logical_state: bool = False, released: bool = False) -> int: ...
    @overload
    async def key_wait(self, key_name: str, *, blocking: Literal[True], timeout: Optional[int] = None, logical_state: bool = False, released: bool = False) -> int: ...
    @overload
    async def key_wait(self, key_name: str, *, blocking: Literal[False], timeout: Optional[int] = None, logical_state: bool = False, released: bool = False) -> AsyncFutureResult[int]: ...
    # fmt: on
    async def key_wait(
        self,
        key_name: str,
        *,
        timeout: Optional[int] = None,
        logical_state: bool = False,
        released: bool = False,
        blocking: bool = True,
    ) -> Union[int, AsyncFutureResult[int]]:
        options = ''
        if not released:
            options += 'D'
        if logical_state:
            options += 'L'
        if timeout:
            options += f'T{timeout}'
        args = [key_name]
        if options:
            args.append(options)

        resp = await self._transport.function_call('KeyWait', args)
        return resp

    # async def mouse_position(self):
    #     raise NotImplementedError()

    async def mouse_wheel(
        self,
        direction: Union[
            Literal['up'], Literal['down'], Literal['UP'], Literal['DOWN'], Literal['Up'], Literal['Down']
        ],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        raise NotImplementedError()

    # async def reg_delete(self, key_name: str, value_name: str = '') -> None:
    #     raise NotImplementedError()
    #
    # async def reg_loop(self, reg: str, key_name: str, mode=''):
    #     raise NotImplementedError()
    #
    # async def reg_read(self, key_name: str, value_name='') -> str:
    #     raise NotImplementedError()
    #
    # async def reg_set_view(self, reg_view: int) -> None:
    #     raise NotImplementedError()
    #
    # async def reg_write(self, value_type: str, key_name: str, value_name='') -> None:
    #     raise NotImplementedError()

    async def run_script(self, script_text: str, decode: bool = True, blocking: bool = True, **runkwargs: Any) -> str:
        raise NotImplementedError()

    # fmt: off
    @overload
    async def send(self, s: str) -> None: ...
    @overload
    async def send(self, s: str, *, blocking: Literal[True]) -> None: ...
    @overload
    async def send(self, s: str, *, blocking: Literal[False]) -> AsyncFutureResult[None]: ...
    # fmt: on
    async def send(
        self, s: str, raw: bool = False, delay: Optional[int] = None, blocking: bool = True
    ) -> Union[None, AsyncFutureResult[None]]:
        args = [s]
        if raw:
            raw_resp = await self._transport.function_call('SendRaw', args=args, blocking=blocking)
            return raw_resp
        else:
            resp = await self._transport.function_call('Send', args=args, blocking=blocking)
            return resp

    async def send_event(self, s: str, delay: Optional[int] = None) -> None:
        raise NotImplementedError()

    # fmt: off
    @overload
    async def send_input(self, s: str) -> None: ...
    @overload
    async def send_input(self, s: str, *, blocking: Literal[True]) -> None: ...
    @overload
    async def send_input(self, s: str, *, blocking: Literal[False]) -> AsyncFutureResult[None]: ...
    # fmt: on
    async def send_input(self, s: str, *, blocking: bool = True) -> Union[None, AsyncFutureResult[None]]:
        args = [s]
        resp = await self._transport.function_call('SendInput', args, blocking=blocking)
        return resp

    async def send_play(self, s: str) -> None:
        raise NotImplementedError()

    async def send_raw(self, s: str, delay: Optional[int] = None) -> None:
        raise NotImplementedError()

    async def set_capslock_state(
        self, state: Optional[Union[Literal['On'], Literal['Off'], Literal['AlwaysOn'], Literal['AlwaysOff']]] = None
    ) -> None:
        raise NotImplementedError()

    async def set_volume(self, value: int, device_number: int = 1) -> None:
        raise NotImplementedError()

    async def show_error_traytip(
        self,
        title: str,
        text: str,
        second: float = 1.0,
        slient: bool = False,
        large_icon: bool = False,
        blocking: bool = True,
    ) -> None:
        raise NotImplementedError()

    async def show_info_traytip(
        self,
        title: str,
        text: str,
        second: float = 1.0,
        slient: bool = False,
        large_icon: bool = False,
        blocking: bool = True,
    ) -> None:
        raise NotImplementedError()

    async def show_tooltip(
        self,
        text: str,
        x: Optional[int] = None,
        y: Optional[int] = None,
        *,
        second: float = 1.0,
        id: Optional[str] = None,
        blocking: bool = True,
    ) -> None:
        raise NotImplementedError()

    async def show_warning_traytip(
        self,
        title: str,
        text: str,
        second: float = 1.0,
        slient: bool = False,
        large_icon: bool = False,
        blocking: bool = True,
    ) -> None:
        raise NotImplementedError()

    async def sound_beep(self, frequency: int = 523, duration: int = 150) -> None:
        raise NotImplementedError()

    async def sound_get(
        self, device_number: int = 1, component_type: str = 'MASTER', control_type: str = 'VOLUME'
    ) -> None:
        raise NotImplementedError()

    async def sound_play(self, filename: str, blocking: bool = True) -> None:
        raise NotImplementedError()

    async def sound_set(
        self,
        value: Union[str, int, float],
        device_number: int = 1,
        component_type: str = 'MASTER',
        control_type: str = 'VOLUME',
    ) -> None:
        raise NotImplementedError()

    async def type(self, s: str, blocking: bool = True) -> None:
        raise NotImplementedError()

    # fmt: off
    @overload
    async def win_get(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> Union[AsyncWindow, None]: ...
    @overload
    async def win_get(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[Union[AsyncWindow, None]]: ...
    @overload
    async def win_get(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> Union[AsyncWindow, None]: ...
    # fmt: on
    async def win_get(
        self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: bool = True
    ) -> Union[AsyncWindow, None, AsyncFutureResult[Union[None, AsyncWindow]]]:
        args = [title, text, exclude_title, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinGetID', args, blocking=blocking, engine=self)
        return resp

    # fmt: off
    @overload
    async def win_get_idlast(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> Union[AsyncWindow, None]: ...
    @overload
    async def win_get_idlast(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[Union[AsyncWindow, None]]: ...
    @overload
    async def win_get_idlast(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> Union[AsyncWindow, None]: ...
    # fmt: on
    async def win_get_idlast(
        self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', blocking: bool = True
    ) -> Union[AsyncWindow, None, AsyncFutureResult[Union[AsyncWindow, None]]]:
        args = [title, text, exclude_title, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinGetIDLast', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_get_pid(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> Union[int, None]: ...
    @overload
    async def win_get_pid(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[Union[int, None]]: ...
    @overload
    async def win_get_pid(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> Union[int, None]: ...
    # fmt: on
    async def win_get_pid(
        self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', blocking: bool = True
    ) -> Union[int, None, AsyncFutureResult[Union[int, None]]]:
        args = [title, text, exclude_title, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinGetPID', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_get_process_name(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> Union[str, None]: ...
    @overload
    async def win_get_process_name(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[Union[str, None]]: ...
    @overload
    async def win_get_process_name(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> Union[str, None]: ...
    # fmt: on
    async def win_get_process_name(
        self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', blocking: bool = True
    ) -> Union[None, str, AsyncFutureResult[Optional[str]]]:
        args = [title, text, exclude_title, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinGetProcessName', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_get_process_path(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> Union[str, None]: ...
    @overload
    async def win_get_process_path(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[Union[str, None]]: ...
    @overload
    async def win_get_process_path(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> Union[str, None]: ...
    # fmt: on
    async def win_get_process_path(
        self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', blocking: bool = True
    ) -> Union[str, None, Union[None, str, AsyncFutureResult[Optional[str]]]]:
        args = [title, text, exclude_title, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinGetProcessPath', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_get_count(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> int: ...
    @overload
    async def win_get_count(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[int]: ...
    @overload
    async def win_get_count(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> int: ...
    # fmt: on
    async def win_get_count(
        self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', blocking: bool = True
    ) -> Union[int, AsyncFutureResult[int]]:
        args = [title, text, exclude_title, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinGetCount', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_get_minmax(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> Union[int, None]: ...
    @overload
    async def win_get_minmax(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[Union[int, None]]: ...
    @overload
    async def win_get_minmax(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> Union[int, None]: ...
    # fmt: on
    async def win_get_minmax(
        self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', blocking: bool = True
    ) -> Union[None, int, AsyncFutureResult[Optional[int]]]:
        args = [title, text, exclude_title, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinGetMinMax', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_get_control_list(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> Union[List[AsyncControl], None]: ...
    @overload
    async def win_get_control_list(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[Union[List[AsyncControl], None]]: ...
    @overload
    async def win_get_control_list(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> Union[List[AsyncControl], None]: ...
    # fmt: on
    async def win_get_control_list(
        self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', blocking: bool = True
    ) -> Union[List[AsyncControl], None, AsyncFutureResult[Optional[List[AsyncControl]]]]:
        args = [title, text, exclude_title, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinGetControlList', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_get_from_mouse_position(self) -> Union[AsyncWindow, None]: ...
    @overload
    async def win_get_from_mouse_position(self, *, blocking: Literal[False]) -> AsyncFutureResult[Union[AsyncWindow, None]]: ...
    @overload
    async def win_get_from_mouse_position(self, *, blocking: Literal[True]) -> Union[AsyncWindow, None]: ...
    # fmt: on
    async def win_get_from_mouse_position(
        self, *, blocking: bool = True
    ) -> Union[Optional[AsyncWindow], AsyncFutureResult[Optional[AsyncWindow]]]:
        raise NotImplementedError()

    # fmt: off
    @overload
    async def win_exists(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> bool: ...
    @overload
    async def win_exists(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[bool]: ...
    @overload
    async def win_exists(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> bool: ...
    # fmt: on
    async def win_exists(
        self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: bool = True
    ) -> Union[bool, AsyncFutureResult[bool]]:
        args = [title, text, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinExist', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_set_title(self, new_title: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> None: ...
    @overload
    async def win_set_title(self, new_title: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> None: ...
    @overload
    async def win_set_title(self, new_title: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[None]: ...
    # fmt: on
    async def win_set_title(
        self,
        new_title: str,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        blocking: bool = True,
    ) -> Union[None, AsyncFutureResult[None]]:
        raise NotImplementedError()

    # fmt: off
    @overload
    async def win_set_always_on_top(self, toggle: Literal['On', 'Off', 'Toggle', 1, -1, 0], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> None: ...
    @overload
    async def win_set_always_on_top(self, toggle: Literal['On', 'Off', 'Toggle', 1, -1, 0], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[None]: ...
    @overload
    async def win_set_always_on_top(self, toggle: Literal['On', 'Off', 'Toggle', 1, -1, 0], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> None: ...
    # fmt: on
    async def win_set_always_on_top(
        self,
        toggle: Literal['On', 'Off', 'Toggle', 1, -1, 0],
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        blocking: bool = True,
    ) -> Union[None, AsyncFutureResult[None]]:
        args = [str(toggle), title, text, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinSetAlwaysOnTop', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_set_bottom(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> None: ...
    @overload
    async def win_set_bottom(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[None]: ...
    @overload
    async def win_set_bottom(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> None: ...
    # fmt: on
    async def win_set_bottom(
        self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: bool = True
    ) -> Union[None, AsyncFutureResult[None]]:
        args = [title, text, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinSetBottom', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_set_top(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> None: ...
    @overload
    async def win_set_top(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[None]: ...
    @overload
    async def win_set_top(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> None: ...
    # fmt: on
    async def win_set_top(
        self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: bool = True
    ) -> Union[None, AsyncFutureResult[None]]:
        args = [title, text, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinSetTop', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_set_disable(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> None: ...
    @overload
    async def win_set_disable(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[None]: ...
    @overload
    async def win_set_disable(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> None: ...
    # fmt: on
    async def win_set_disable(
        self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: bool = True
    ) -> Union[None, AsyncFutureResult[None]]:
        args = [title, text, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinSetDisable', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_set_enable(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> None: ...
    @overload
    async def win_set_enable(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[None]: ...
    @overload
    async def win_set_enable(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> None: ...
    # fmt: on
    async def win_set_enable(
        self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: bool = True
    ) -> Union[None, AsyncFutureResult[None]]:
        args = [title, text, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinSetEnable', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_set_redraw(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> None: ...
    @overload
    async def win_set_redraw(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[None]: ...
    @overload
    async def win_set_redraw(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> None: ...
    # fmt: on
    async def win_set_redraw(
        self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: bool = True
    ) -> Union[None, AsyncFutureResult[None]]:
        args = [title, text, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinSetRedraw', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_set_style(self, style: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> bool: ...
    @overload
    async def win_set_style(self, style: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[bool]: ...
    @overload
    async def win_set_style(self, style: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> bool: ...
    # fmt: on
    async def win_set_style(
        self,
        style: str,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        blocking: bool = True,
    ) -> Union[bool, AsyncFutureResult[bool]]:
        args = [style, title, text, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinSetStyle', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_set_ex_style(self, style: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> bool: ...
    @overload
    async def win_set_ex_style(self, style: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[bool]: ...
    @overload
    async def win_set_ex_style(self, style: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> bool: ...
    # fmt: on
    async def win_set_ex_style(
        self,
        style: str,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        blocking: bool = True,
    ) -> Union[bool, AsyncFutureResult[bool]]:
        args = [style, title, text, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinSetExStyle', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_set_region(self, options: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> bool: ...
    @overload
    async def win_set_region(self, options: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[bool]: ...
    @overload
    async def win_set_region(self, options: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> bool: ...
    # fmt: on
    async def win_set_region(
        self,
        options: str,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        blocking: bool = True,
    ) -> Union[bool, AsyncFutureResult[bool]]:
        raise NotImplementedError()

    # fmt: off
    @overload
    async def win_set_transparent(self, transparency: Union[int, Literal['Off']], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> None: ...
    @overload
    async def win_set_transparent(self, transparency: Union[int, Literal['Off']], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[None]: ...
    @overload
    async def win_set_transparent(self, transparency: Union[int, Literal['Off']], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> None: ...
    # fmt: on
    async def win_set_transparent(
        self,
        transparency: Union[int, Literal['Off']],
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        blocking: bool = True,
    ) -> Union[None, AsyncFutureResult[None]]:
        args = [str(transparency), title, text, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinSetTransparent', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    async def win_set_trans_color(self, color: Union[int, str], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '') -> None: ...
    @overload
    async def win_set_trans_color(self, color: Union[int, str], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[False]) -> AsyncFutureResult[None]: ...
    @overload
    async def win_set_trans_color(self, color: Union[int, str], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, blocking: Literal[True]) -> None: ...
    # fmt: on
    async def win_set_trans_color(
        self,
        color: Union[int, str],
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        blocking: bool = True,
    ) -> Union[None, AsyncFutureResult[None]]:
        args = [str(color), title, text, exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinSetTransColor', args, blocking=blocking)
        return resp

    # alias for backwards compatibility
    windows = list_windows

    async def click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        *,
        button: Optional[str] = None,
        n: Optional[int] = None,
        direction: Optional[str] = None,
        relative: Optional[bool] = None,
        blocking: bool = True,
        mode: Optional[CoordMode] = None,
    ) -> None:
        raise NotImplementedError()

    # fmt: off
    @overload
    async def image_search(self, image_path: str, upper_bound: Tuple[Union[int, str], Union[int, str]] = (0, 0), lower_bound: Optional[Tuple[Union[int, str], Union[int, str]]] = None, *, color_variation: Optional[int] = None, coord_mode: str = 'Screen', scale_height: Optional[int] = None, scale_width: Optional[int] = None, transparent: Optional[str] = None, icon: Optional[int] = None) -> Optional[Tuple[int, int]]: ...
    @overload
    async def image_search(self, image_path: str, upper_bound: Tuple[Union[int, str], Union[int, str]] = (0, 0), lower_bound: Optional[Tuple[Union[int, str], Union[int, str]]] = None, *, color_variation: Optional[int] = None, coord_mode: str = 'Screen', scale_height: Optional[int] = None, scale_width: Optional[int] = None, transparent: Optional[str] = None, icon: Optional[int] = None, blocking: Literal[False]) -> AsyncFutureResult[Optional[Tuple[int, int]]]: ...
    @overload
    async def image_search(self, image_path: str, upper_bound: Tuple[Union[int, str], Union[int, str]] = (0, 0), lower_bound: Optional[Tuple[Union[int, str], Union[int, str]]] = None, *, color_variation: Optional[int] = None, coord_mode: str = 'Screen', scale_height: Optional[int] = None, scale_width: Optional[int] = None, transparent: Optional[str] = None, icon: Optional[int] = None, blocking: Literal[True]) -> Optional[Tuple[int, int]]: ...
    # fmt: on
    async def image_search(
        self,
        image_path: str,
        upper_bound: Tuple[Union[int, str], Union[int, str]] = (0, 0),
        lower_bound: Optional[Tuple[Union[int, str], Union[int, str]]] = None,
        *,
        color_variation: Optional[int] = None,
        coord_mode: str = 'Screen',
        scale_height: Optional[int] = None,
        scale_width: Optional[int] = None,
        transparent: Optional[str] = None,
        icon: Optional[int] = None,
        blocking: bool = True,
    ) -> Union[Tuple[int, int], None, AsyncFutureResult[Optional[Tuple[int, int]]]]:
        """
        https://www.autohotkey.com/docs/commands/ImageSearch.htm
        """

        if scale_height and not scale_width:
            scale_width = -1
        elif scale_width and not scale_height:
            scale_height = -1

        options: List[Union[str, int]] = []
        if icon:
            options.append(f'Icon{icon}')
        if color_variation is not None:
            options.append(color_variation)
        if transparent is not None:
            options.append(f'Trans{transparent}')
        if scale_width:
            options.append(f'w{scale_width}')
            options.append(f'h{scale_height}')

        x1, y1 = upper_bound
        if lower_bound:
            x2, y2 = lower_bound
        else:
            x2, y2 = ('A_ScreenWidth', 'A_ScreenHeight')

        args = [
            str(x1),
            str(y1),
            str(x2),
            str(y2),
        ]
        if options:
            s = ''
            for opt in options:
                s += f'*{opt} '
            s += image_path
            args.append(s)
        else:
            args.append(image_path)
        resp = await self._transport.function_call('ImageSearch', args)
        return resp

    async def mouse_drag(
        self,
        x: int,
        y: Optional[int] = None,
        *,
        from_position: Optional[Tuple[int, int]] = None,
        speed: Optional[int] = None,
        button: Union[str, int] = 1,
        relative: Optional[bool] = None,
        blocking: bool = True,
        mode: Optional[CoordMode] = None,
    ) -> None:
        raise NotImplementedError()

    async def pixel_get_color(
        self, x: int, y: int, coord_mode: str = 'Screen', alt: bool = False, slow: bool = False, rgb: bool = True
    ) -> str:
        raise NotImplementedError()

    async def pixel_search(
        self,
        color: Union[str, int],
        variation: int = 0,
        upper_bound: Tuple[int, int] = (0, 0),
        lower_bound: Optional[Tuple[int, int]] = None,
        coord_mode: str = 'Screen',
        fast: bool = True,
        rgb: bool = True,
    ) -> Union[Tuple[int, int], None]:
        raise NotImplementedError()

    async def show_traytip(
        self,
        title: str,
        text: str,
        second: float = 1.0,
        type_id: int = 1,
        slient: bool = False,
        large_icon: bool = False,
        blocking: bool = True,
    ) -> None:
        raise NotImplementedError()

    # fmt: off
    @overload
    async def win_close(self, title: str = '', *, text: str = '', seconds_to_wait: Optional[int] = None, exclude_title: str = '', exclude_text: str = '') -> None: ...
    @overload
    async def win_close(self, title: str = '', *, text: str = '', seconds_to_wait: Optional[int] = None, exclude_title: str = '', exclude_text: str = '', blocking: Literal[True]) -> None: ...
    @overload
    async def win_close(self, title: str = '', *, text: str = '', seconds_to_wait: Optional[int] = None, exclude_title: str = '', exclude_text: str = '', blocking: Literal[False]) -> AsyncFutureResult[None]: ...
    # fmt: on
    async def win_close(
        self,
        title: str = '',
        *,
        text: str = '',
        seconds_to_wait: Optional[int] = None,
        exclude_title: str = '',
        exclude_text: str = '',
        blocking: bool = True,
    ) -> Union[None, AsyncFutureResult[None]]:
        args: List[str]
        args = [title, text, str(seconds_to_wait) if seconds_to_wait is not None else '', exclude_title, exclude_text]
        resp = await self._transport.function_call('AHKWinClose', args=args, blocking=blocking)
        return resp

    async def block_forever(self) -> NoReturn:
        while True:
            await async_sleep(1)
