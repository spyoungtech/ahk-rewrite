from __future__ import annotations

import asyncio
import sys
import time
import warnings
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Coroutine
from typing import Dict
from typing import List
from typing import Literal
from typing import NoReturn
from typing import Optional
from typing import overload
from typing import Tuple
from typing import Type
from typing import Union

from ..hotkey import Hotkey
from ..hotkey import Hotstring

if sys.version_info < (3, 10):
    from typing_extensions import TypeAlias
else:
    from typing import TypeAlias

from ..keys import Key
from .transport import DaemonProcessTransport
from .transport import FutureResult
from .transport import Transport
from .window import Control
from .window import Window
from ahk.message import Position

sleep = time.sleep

SyncFilterFunc: TypeAlias = Callable[[Window], bool]

CoordModeTargets: TypeAlias = Union[
    Literal['ToolTip'], Literal['Pixel'], Literal['Mouse'], Literal['Caret'], Literal['Menu']
]
CoordModeRelativeTo: TypeAlias = Union[Literal['Screen', 'Relative', 'Window', 'Client', '']]

CoordMode: TypeAlias = Union[CoordModeTargets, Tuple[CoordModeTargets, CoordModeRelativeTo]]

MatchModes: TypeAlias = Literal[1, 2, 3, 'RegEx', '']
MatchSpeeds: TypeAlias = Literal['Fast', 'Slow', '']

TitleMatchMode: TypeAlias = Optional[
    Union[MatchModes, MatchSpeeds, Tuple[Union[MatchModes, MatchSpeeds], Union[MatchSpeeds, MatchModes]]]
]

_BUTTONS: dict[Union[str, int], str] = {
    1: 'L',
    2: 'R',
    3: 'M',
    'left': 'L',
    'right': 'R',
    'middle': 'M',
    'wheelup': 'WU',
    'wheeldown': 'WD',
    'wheelleft': 'WL',
    'wheelright': 'WR',
}

MouseButton: TypeAlias = Union[
    int,
    Literal[
        'L',
        'R',
        'M',
        'left',
        'right',
        'middle',
        'wheelup',
        'WU',
        'wheeldown',
        'WD',
        'wheelleft',
        'WL',
        'wheelright',
        'WR',
    ],
]

SyncPropertyReturnTupleIntInt: TypeAlias = Tuple[int, int]

SyncPropertyReturnOptionalAsyncWindow: TypeAlias = Optional[Window]

_PROPERTY_DEPRECATION_WARNING_MESSAGE = 'Use of the {0} property is not recommended (in the async API only) and may be removed in a future version. Use the get_{0} method instead'


def resolve_button(button: Union[str, int]) -> str:
    """
    Resolve a string of a button name to a canonical name used for AHK script
    :param button:
    :type button: str
    :return:
    """
    if isinstance(button, str):
        button = button.lower()

    if button in _BUTTONS:
        resolved_button = _BUTTONS[button]
    elif isinstance(button, int) and button > 3:
        #  for addtional mouse buttons
        resolved_button = f'X{button-3}'
    else:
        assert isinstance(button, str)
        resolved_button = button
    return resolved_button


class AHK:
    def __init__(
        self,
        *,
        TransportClass: Optional[Type[Transport]] = None,
        transport_options: Optional[Dict[str, Any]] = None,
    ):
        if transport_options is None:
            transport_options = {}
        if TransportClass is None:
            TransportClass = DaemonProcessTransport
        assert TransportClass is not None
        transport = TransportClass(**transport_options)
        self._transport: Transport = transport

    def __getattr__(self, item: Any) -> Any:
        deprecation_replacements: Dict[str, Any] = {'type': self.send_input}
        if item in deprecation_replacements:
            func = deprecation_replacements[item]
            warnings.warn(
                f'{item!r} is deprecated and will be removed in a future version. Use {func.__name__!r} instead.',
                DeprecationWarning,
                stacklevel=2,
            )
            return deprecation_replacements[item]
        raise AttributeError(f'{self.__class__.__qualname__!r} object has no attribute {item!r}')

    def add_hotkey(self, hotkey: Hotkey) -> None:
        """
        Register a function to be called when a hotkey is pressed.

        Key notes:

        - You must call the `start_hotkeys` method for the hotkeys to be active
        - All hotkeys run in a single AHK process instance (but Python callbacks also get their own thread and can run simultaneously)
        - If you add a hotkey after the hotkey thread/instance is active, it will be restarted automatically
        - `async` functions are not directly supported as callbacks, however you may write a synchronous function that calls `asyncio.run`/`loop.create_task` etc.

        :param hotkey: an instance of ahk.hotkey.Hotkey
        """
        with warnings.catch_warnings(record=True) as caught_warnings:
            self._transport.add_hotkey(hotkey=hotkey)
        if caught_warnings:
            for warning in caught_warnings:
                warnings.warn(warning.message, warning.category, stacklevel=2)
        return None

    def add_hotstring(self, hotstring: Hotstring) -> None:
        """
        Register a hotstring, e.g., `::btw::by the way`

        Key notes:

        - You must call the `start_hotkeys` method for registered hotstrings to be active
        - All hotstrings (and hotkeys) run in a single AHK process instance separate from other AHK processes.

        :param hotstring: an instance of ahk.hotkey.Hotstring
        """
        with warnings.catch_warnings(record=True) as caught_warnings:
            self._transport.add_hotstring(hotstring=hotstring)
        if caught_warnings:
            for warning in caught_warnings:
                warnings.warn(warning.message, warning.category, stacklevel=2)
        return None

    def set_title_match_mode(self, title_match_mode: TitleMatchMode, /) -> None:
        """
        Sets the default title match mode

        Has no effect for `Window`/`Control` instance methods (these always use hwnd)

        Does not affect methods called with `blocking=True` (because these run in a separate AHK process)

        Reference: https://www.autohotkey.com/docs/commands/SetTitleMatchMode.htm

        :param title_match_mode: the match mode (and/or match speed) to set as the default title match mode. Can be 1, 2, 3, 'Regex', 'Fast', 'Slow' or a tuple of these.
        :return: None
        """

        args = []
        if isinstance(title_match_mode, tuple):
            (match_mode, match_speed) = title_match_mode
        elif title_match_mode in (1, 2, 3, 'RegEx'):
            match_mode = title_match_mode
            match_speed = ''
        elif title_match_mode in ('Fast', 'Slow'):
            match_mode = ''
            match_speed = title_match_mode
        else:
            raise ValueError(
                f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
            )
        args.append(str(match_mode))
        args.append(str(match_speed))
        self._transport.function_call('AHKSetTitleMatchMode', args)
        return None

    def get_title_match_mode(self) -> str:
        """
        Get the title match mode.

        I.E. the current value of `A_TitleMatchMode`

        """
        resp = self._transport.function_call('AHKGetTitleMatchMode')
        return resp

    def get_title_match_speed(self) -> str:
        """
        Get the title match mode speed.

        I.E. the current value of `A_TitleMatchModeSpeed`

        """
        resp = self._transport.function_call('AHKGetTitleMatchSpeed')
        return resp

    def set_coord_mode(self, target: CoordModeTargets, relative_to: CoordModeRelativeTo = 'Screen') -> None:
        args = [str(target), str(relative_to)]
        self._transport.function_call('AHKSetCoordMode', args)
        return None

    def get_coord_mode(self, target: CoordModeTargets) -> str:
        args = [str(target)]
        resp = self._transport.function_call('AHKGetCoordMode', args)
        return resp

    # fmt: off
    @overload
    def control_click(self, *, button: Literal['L', 'R', 'M', 'LEFT', 'RIGHT', 'MIDDLE'] = 'L', click_count: int = 1, options: str = '', control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> None: ...
    @overload
    def control_click(self, *, button: Literal['L', 'R', 'M', 'LEFT', 'RIGHT', 'MIDDLE'] = 'L', click_count: int = 1, options: str = '', control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def control_click(self, *, button: Literal['L', 'R', 'M', 'LEFT', 'RIGHT', 'MIDDLE'] = 'L', click_count: int = 1, options: str = '', control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> None: ...
    @overload
    def control_click(self, *, button: Literal['L', 'R', 'M', 'LEFT', 'RIGHT', 'MIDDLE'] = 'L', click_count: int = 1, options: str = '', control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def control_click(
        self,
        *,
        button: Literal['L', 'R', 'M', 'LEFT', 'RIGHT', 'MIDDLE'] = 'L',
        click_count: int = 1,
        options: str = '',
        control: str = '',
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        args = [control, title, text, str(button), str(click_count), options, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKControlClick', args=args, blocking=blocking)

        return resp

    # fmt: off
    @overload
    def control_get_text(self, *, control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> str: ...
    @overload
    def control_get_text(self, *, control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[str]: ...
    @overload
    def control_get_text(self, *, control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> str: ...
    @overload
    def control_get_text(self, *, control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[str, FutureResult[str]]: ...
    # fmt: on
    def control_get_text(
        self,
        *,
        control: str = '',
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[str, FutureResult[str]]:
        args = [control, title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKControlGetText', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def control_get_position(self, control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> Position: ...
    @overload
    def control_get_position(self, control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[Position]: ...
    @overload
    def control_get_position(self, control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> Position: ...
    @overload
    def control_get_position(self, control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[Position, FutureResult[Position]]: ...
    # fmt: on
    def control_get_position(
        self,
        control: str = '',
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[Position, FutureResult[Position]]:
        args = [control, title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')

        resp = self._transport.function_call('AHKControlGetPos', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def control_send(self, keys: str, control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> None: ...
    @overload
    def control_send(self, keys: str, control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def control_send(self, keys: str, control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> None: ...
    @overload
    def control_send(self, keys: str, control: str = '', title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def control_send(
        self,
        keys: str,
        control: str = '',
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        """
        Analog for ControlSend

        Reference: https://www.autohotkey.com/docs/commands/ControlSend.htm

        :param keys:
        :param control:
        :param title:
        :param text:
        :param exclude_title:
        :param exclude_text:
        :param title_match_mode:
        :param detect_hidden_windows:
        :param blocking:
        :return:
        """
        args = [control, keys, title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKControlSend', args, blocking=blocking)
        return resp

    def start_hotkeys(self) -> None:
        """
        Start the Autohotkey process for triggering hotkeys

        """
        return self._transport.start_hotkeys()

    def stop_hotkeys(self) -> None:
        """
        Stop the Autohotkey process for triggering hotkeys

        """
        return self._transport.stop_hotkeys()

    def set_detect_hidden_windows(self, value: bool) -> None:
        """
        Analog for AutoHotkey's `DetectHiddenWindows`

        :param value: The setting value. `True` to turn on hidden window detection, `False` to turn it off.

        """

        if value not in (True, False):
            raise TypeError(f'detect hidden windows must be a boolean, got object of type {type(value)}')
        args = []
        if value is True:
            args.append('On')
        else:
            args.append('Off')
        self._transport.function_call('AHKSetDetectHiddenWindows', args=args)
        return None

    # fmt: off
    @overload
    def list_windows(self, *, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> List[Window]: ...
    @overload
    def list_windows(self, *, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> Union[List[Window], FutureResult[List[Window]]]: ...
    @overload
    def list_windows(self, *, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> List[Window]: ...
    @overload
    def list_windows(self, *, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True,) -> Union[List[Window], FutureResult[List[Window]]]: ...
    # fmt: on
    def list_windows(
        self,
        *,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[List[Window], FutureResult[List[Window]]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWindowList', args, engine=self, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def get_mouse_position(self, *, blocking: Literal[True]) -> Tuple[int, int]: ...
    @overload
    def get_mouse_position(self, *, blocking: Literal[False]) -> FutureResult[Tuple[int, int]]: ...
    @overload
    def get_mouse_position(self) -> Tuple[int, int]: ...
    @overload
    def get_mouse_position(self, *, blocking: bool = True) -> Union[Tuple[int, int], FutureResult[Tuple[int, int]]]: ...
    # fmt: on
    def get_mouse_position(
        self, *, blocking: bool = True
    ) -> Union[Tuple[int, int], FutureResult[Tuple[int, int]]]:
        resp = self._transport.function_call('AHKMouseGetPos', blocking=blocking)
        return resp

    @property
    def mouse_position(self) -> SyncPropertyReturnTupleIntInt:
        return self.get_mouse_position()

    # fmt: off
    @overload
    def mouse_move(self, x: Optional[Union[str, int]] = None, y: Optional[Union[str, int]] = None, *, speed: Optional[int] = None, relative: bool = False) -> None: ...
    @overload
    def mouse_move(self, x: Optional[Union[str, int]] = None, y: Optional[Union[str, int]] = None, *, blocking: Literal[True], speed: Optional[int] = None, relative: bool = False) -> None: ...
    @overload
    def mouse_move(self, x: Optional[Union[str, int]] = None, y: Optional[Union[str, int]] = None, *, blocking: Literal[False], speed: Optional[int] = None, relative: bool = False, ) -> FutureResult[None]: ...
    @overload
    def mouse_move(self, x: Optional[Union[str, int]] = None, y: Optional[Union[str, int]] = None, *, speed: Optional[int] = None, relative: bool = False, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def mouse_move(
        self,
        x: Optional[Union[str, int]] = None,
        y: Optional[Union[str, int]] = None,
        *,
        speed: Optional[int] = None,
        relative: bool = False,
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        if relative and (x is None or y is None):
            x = x or 0
            y = y or 0
        elif not relative and (x is None or y is None):
            posx, posy = self.get_mouse_position()
            x = x or posx
            y = y or posy

        if speed is None:
            speed = 2
        args = [str(x), str(y), str(speed)]
        if relative:
            args.append('R')
        resp = self._transport.function_call('AHKMouseMove', args, blocking=blocking)
        return resp

    def a_run_script(self, script_text: str, decode: bool = True, blocking: bool = True, **runkwargs: Any) -> str:
        raise NotImplementedError()

    # fmt: off
    @overload
    def get_active_window(self) -> Optional[Window]: ...
    @overload
    def get_active_window(self, blocking: Literal[True]) -> Optional[Window]: ...
    @overload
    def get_active_window(self, blocking: Literal[False]) -> FutureResult[Optional[Window]]: ...
    @overload
    def get_active_window(self, blocking: bool = True) -> Union[Optional[Window], FutureResult[Optional[Window]]]: ...
    # fmt: on
    def get_active_window(
        self, blocking: bool = True
    ) -> Union[Optional[Window], FutureResult[Optional[Window]]]:
        return self.win_get(
            title='A', detect_hidden_windows=False, title_match_mode=(1, 'Fast'), blocking=blocking
        )

    @property
    def active_window(self) -> SyncPropertyReturnOptionalAsyncWindow:
        return self.get_active_window()

    def find_windows(
        self,
        func: Optional[SyncFilterFunc] = None,
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        exact: Optional[bool] = None,
    ) -> List[Window]:
        if exact is not None and title_match_mode is not None:
            raise TypeError('exact and match_mode parameters are mutually exclusive')
        if exact is not None:
            warnings.warn('exact parameter is deprecated. Use match_mode=3 instead', stacklevel=2)
            if exact:
                title_match_mode = (3, 'Fast')
            else:
                title_match_mode = (1, 'Fast')
        elif title_match_mode is None:
            title_match_mode = (1, 'Fast')

        windows = self.list_windows(
            title=title,
            text=text,
            exclude_title=exclude_title,
            exclude_text=exclude_text,
            title_match_mode=title_match_mode,
        )
        if func is None:
            return windows
        else:
            ret: List[Window] = []
            for win in windows:
                match = func(win)
                if match:
                    ret.append(win)
            return ret

    def find_windows_by_class(
        self, class_name: str, *, exact: Optional[bool] = None, title_match_mode: Optional[TitleMatchMode] = None
    ) -> List[Window]:
        with warnings.catch_warnings(record=True) as caught_warnings:
            ret = self.find_windows(
                title=f'ahk_class {class_name}', title_match_mode=title_match_mode, exact=exact
            )
        if caught_warnings:
            for warning in caught_warnings:
                warnings.warn(warning.message, warning.category, stacklevel=2)
        return ret

    def find_windows_by_text(
        self, text: str, exact: Optional[bool] = None, title_match_mode: Optional[TitleMatchMode] = None
    ) -> List[Window]:
        with warnings.catch_warnings(record=True) as caught_warnings:
            ret = self.find_windows(text=text, exact=exact, title_match_mode=title_match_mode)
        if caught_warnings:
            for warning in caught_warnings:
                warnings.warn(warning.message, warning.category, stacklevel=2)
        return ret

    def find_windows_by_title(
        self, title: str, exact: Optional[bool] = None, title_match_mode: Optional[TitleMatchMode] = None
    ) -> List[Window]:
        with warnings.catch_warnings(record=True) as caught_warnings:
            ret = self.find_windows(title=title, exact=exact, title_match_mode=title_match_mode)
        if caught_warnings:
            for warning in caught_warnings:
                warnings.warn(warning.message, warning.category, stacklevel=2)
        return ret

    def find_window(
        self,
        func: Optional[SyncFilterFunc] = None,
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        exact: Optional[bool] = None,
    ) -> Optional[Window]:
        with warnings.catch_warnings(record=True) as caught_warnings:
            windows = self.find_windows(
                func,
                title=title,
                text=text,
                exclude_title=exclude_title,
                exclude_text=exclude_text,
                exact=exact,
                title_match_mode=title_match_mode,
            )
        if caught_warnings:
            for warning in caught_warnings:
                warnings.warn(warning.message, warning.category, stacklevel=2)
        return windows[0] if windows else None

    def find_window_by_class(
        self, class_name: str, exact: Optional[bool] = None, title_match_mode: Optional[TitleMatchMode] = None
    ) -> Optional[Window]:
        with warnings.catch_warnings(record=True) as caught_warnings:
            windows = self.find_windows_by_class(
                class_name=class_name, exact=exact, title_match_mode=title_match_mode
            )
        if caught_warnings:
            for warning in caught_warnings:
                warnings.warn(warning.message, warning.category, stacklevel=2)
        return windows[0] if windows else None

    def find_window_by_text(
        self, text: str, exact: Optional[bool] = None, title_match_mode: Optional[TitleMatchMode] = None
    ) -> Optional[Window]:
        with warnings.catch_warnings(record=True) as caught_warnings:
            windows = self.find_windows_by_text(text=text, exact=exact, title_match_mode=title_match_mode)
        if caught_warnings:
            for warning in caught_warnings:
                warnings.warn(warning.message, warning.category, stacklevel=2)
        return windows[0] if windows else None

    def find_window_by_title(
        self, title: str, exact: Optional[bool] = None, title_match_mode: Optional[TitleMatchMode] = None
    ) -> Optional[Window]:
        with warnings.catch_warnings(record=True) as caught_warnings:
            windows = self.find_windows_by_title(title=title, exact=exact, title_match_mode=title_match_mode)
        if caught_warnings:
            for warning in caught_warnings:
                warnings.warn(warning.message, warning.category, stacklevel=2)
        return windows[0] if windows else None

    def get_volume(self, device_number: int = 1) -> float:
        raise NotImplementedError()

    # fmt: off
    @overload
    def key_down(self, key: Union[str, Key]) -> None: ...
    @overload
    def key_down(self, key: Union[str, Key], *, blocking: Literal[True]) -> None: ...
    @overload
    def key_down(self, key: Union[str, Key], *, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def key_down(self, key: Union[str, Key], *, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def key_down(self, key: Union[str, Key], *, blocking: bool = True) -> Union[None, FutureResult[None]]:
        if isinstance(key, str):
            key = Key(key_name=key)
        if blocking:
            self.send_input(key.DOWN, blocking=True)
            return None
        else:
            return self.send_input(key.DOWN, blocking=False)

    # fmt: off
    @overload
    def key_press(self, key: Union[str, Key], *, release: bool = True) -> None: ...
    @overload
    def key_press(self, key: Union[str, Key], *, blocking: Literal[True], release: bool = True) -> None: ...
    @overload
    def key_press(self, key: Union[str, Key], *, blocking: Literal[False], release: bool = True) -> FutureResult[None]: ...
    @overload
    def key_press(self, key: Union[str, Key], *, release: bool = True, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def key_press(
        self, key: Union[str, Key], *, release: bool = True, blocking: bool = True
    ) -> Union[None, FutureResult[None]]:
        if blocking:
            self.key_down(key, blocking=True)
            if release:
                self.key_up(key, blocking=True)
            return None
        else:
            d = self.key_down(key, blocking=False)
            if release:
                return self.key_up(key, blocking=False)
            return d

    # fmt: off
    @overload
    def key_release(self, key: Union[str, Key]) -> None: ...
    @overload
    def key_release(self, key: Union[str, Key], *, blocking: Literal[True]) -> None: ...
    @overload
    def key_release(self, key: Union[str, Key], *, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def key_release(self, key: Union[str, Key], *, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def key_release(self, key: Union[str, Key], *, blocking: bool = True) -> Union[None, FutureResult[None]]:
        if blocking:
            self.key_up(key=key, blocking=True)
            return None
        else:
            return self.key_up(key=key, blocking=False)

    def key_state(self, key_name: str, mode: Optional[Union[Literal['P'], Literal['T']]] = None) -> bool:
        raise NotImplementedError()

    # fmt: off
    @overload
    def key_up(self, key: Union[str, Key]) -> None: ...
    @overload
    def key_up(self, key: Union[str, Key], *, blocking: Literal[True]) -> None: ...
    @overload
    def key_up(self, key: Union[str, Key], *, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def key_up(self, key: Union[str, Key], blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def key_up(self, key: Union[str, Key], blocking: bool = True) -> Union[None, FutureResult[None]]:
        if isinstance(key, str):
            key = Key(key_name=key)
        if blocking:
            self.send_input(key.UP, blocking=True)
            return None
        else:
            return self.send_input(key.UP, blocking=False)

    # fmt: off
    @overload
    def key_wait(self, key_name: str, *, timeout: Optional[int] = None, logical_state: bool = False, released: bool = False) -> int: ...
    @overload
    def key_wait(self, key_name: str, *, blocking: Literal[True], timeout: Optional[int] = None, logical_state: bool = False, released: bool = False) -> int: ...
    @overload
    def key_wait(self, key_name: str, *, blocking: Literal[False], timeout: Optional[int] = None, logical_state: bool = False, released: bool = False) -> FutureResult[int]: ...
    @overload
    def key_wait(self, key_name: str, *, timeout: Optional[int] = None, logical_state: bool = False, released: bool = False, blocking: bool = True) -> Union[int, FutureResult[int]]: ...
    # fmt: on
    def key_wait(
        self,
        key_name: str,
        *,
        timeout: Optional[int] = None,
        logical_state: bool = False,
        released: bool = False,
        blocking: bool = True,
    ) -> Union[int, FutureResult[int]]:
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

        resp = self._transport.function_call('AHKKeyWait', args)
        return resp

    def run_script(self, script_text: str, decode: bool = True, blocking: bool = True, **runkwargs: Any) -> str:
        raise NotImplementedError()

    # fmt: off
    @overload
    def send(self, s: str, *, raw: bool = False, key_delay: Optional[int] = None, key_press_duration: Optional[int] = None) -> None: ...
    @overload
    def send(self, s: str, *, raw: bool = False, key_delay: Optional[int] = None, key_press_duration: Optional[int] = None, blocking: Literal[True]) -> None: ...
    @overload
    def send(self, s: str, *, raw: bool = False, key_delay: Optional[int] = None, key_press_duration: Optional[int] = None, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def send(self, s: str, *, raw: bool = False, key_delay: Optional[int] = None, key_press_duration: Optional[int] = None, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def send(
        self,
        s: str,
        *,
        raw: bool = False,
        key_delay: Optional[int] = None,
        key_press_duration: Optional[int] = None,
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        args = [s]
        if key_delay:
            args.append(str(key_delay))
        else:
            args.append('')
        if key_press_duration:
            args.append(str(key_press_duration))
        else:
            args.append('')

        if raw:
            raw_resp = self._transport.function_call('AHKSendRaw', args=args, blocking=blocking)
            return raw_resp
        else:
            resp = self._transport.function_call('AHKSend', args=args, blocking=blocking)
            return resp

    # fmt: off
    @overload
    def send_raw(self, s: str, *, key_delay: Optional[int] = None, key_press_duration: Optional[int] = None) -> None: ...
    @overload
    def send_raw(self, s: str, *, key_delay: Optional[int] = None, key_press_duration: Optional[int] = None, blocking: Literal[True]) -> None: ...
    @overload
    def send_raw(self, s: str, *, key_delay: Optional[int] = None, key_press_duration: Optional[int] = None, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def send_raw(self, s: str, *, key_delay: Optional[int] = None, key_press_duration: Optional[int] = None, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def send_raw(
        self,
        s: str,
        *,
        key_delay: Optional[int] = None,
        key_press_duration: Optional[int] = None,
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        resp = self.send(
            s, raw=True, key_delay=key_delay, key_press_duration=key_press_duration, blocking=blocking
        )
        return resp

    # fmt: off
    @overload
    def send_input(self, s: str) -> None: ...
    @overload
    def send_input(self, s: str, *, blocking: Literal[True]) -> None: ...
    @overload
    def send_input(self, s: str, *, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def send_input(self, s: str, *, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def send_input(self, s: str, *, blocking: bool = True) -> Union[None, FutureResult[None]]:
        args = [s]
        resp = self._transport.function_call('AHKSendInput', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def send_play(self, s: str, *, key_delay: Optional[int] = None, key_press_duration: Optional[int] = None) -> None: ...
    @overload
    def send_play(self, s: str, *, key_delay: Optional[int] = None, key_press_duration: Optional[int] = None, blocking: Literal[True]) -> None: ...
    @overload
    def send_play(self, s: str, *, key_delay: Optional[int] = None, key_press_duration: Optional[int] = None, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def send_play(self, s: str, *, key_delay: Optional[int] = None, key_press_duration: Optional[int] = None, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def send_play(
        self,
        s: str,
        *,
        key_delay: Optional[int] = None,
        key_press_duration: Optional[int] = None,
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        args = [s]
        if key_delay:
            args.append(str(key_delay))
        else:
            args.append('')
        if key_press_duration:
            args.append(str(key_press_duration))
        else:
            args.append('')

        resp = self._transport.function_call('AHKSendPlay', args=args, blocking=blocking)
        return resp

    def set_capslock_state(
        self, state: Optional[Union[Literal['On'], Literal['Off'], Literal['AlwaysOn'], Literal['AlwaysOff']]] = None
    ) -> None:
        raise NotImplementedError()

    def set_volume(self, value: int, device_number: int = 1) -> None:
        raise NotImplementedError()

    def show_error_traytip(
        self,
        title: str,
        text: str,
        second: float = 1.0,
        silent: bool = False,
        large_icon: bool = False,
        blocking: bool = True,
    ) -> None:
        raise NotImplementedError()

    def show_info_traytip(
        self,
        title: str,
        text: str,
        second: float = 1.0,
        silent: bool = False,
        large_icon: bool = False,
        blocking: bool = True,
    ) -> None:
        raise NotImplementedError()

    def show_tooltip(
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

    def show_warning_traytip(
        self,
        title: str,
        text: str,
        second: float = 1.0,
        slient: bool = False,
        large_icon: bool = False,
        blocking: bool = True,
    ) -> None:
        raise NotImplementedError()

    def sound_beep(self, frequency: int = 523, duration: int = 150) -> None:
        raise NotImplementedError()

    def sound_get(
        self, device_number: int = 1, component_type: str = 'MASTER', control_type: str = 'VOLUME'
    ) -> None:
        raise NotImplementedError()

    def sound_play(self, filename: str, blocking: bool = True) -> None:
        raise NotImplementedError()

    def sound_set(
        self,
        value: Union[str, int, float],
        device_number: int = 1,
        component_type: str = 'MASTER',
        control_type: str = 'VOLUME',
    ) -> None:
        raise NotImplementedError()

    def type(self, s: str, blocking: bool = True) -> None:
        raise NotImplementedError()

    # fmt: off
    @overload
    def win_get(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> Union[Window, None]: ...
    @overload
    def win_get(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[Union[Window, None]]: ...
    @overload
    def win_get(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> Union[Window, None]: ...
    @overload
    def win_get(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[Window, None, FutureResult[Union[None, Window]]]: ...
    # fmt: on
    def win_get(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[Window, None, FutureResult[Union[None, Window]]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinGetID', args, blocking=blocking, engine=self)
        return resp

    # fmt: off
    @overload
    def win_get_text(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> str: ...
    @overload
    def win_get_text(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[str]: ...
    @overload
    def win_get_text(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> str: ...
    @overload
    def win_get_text(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[str, FutureResult[str]]: ...
    # fmt: on
    def win_get_text(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[str, FutureResult[str]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinGetText', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_get_title(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> str: ...
    @overload
    def win_get_title(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[str]: ...
    @overload
    def win_get_title(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> str: ...
    @overload
    def win_get_title(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[str, FutureResult[str]]: ...
    # fmt: on
    def win_get_title(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[str, FutureResult[str]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinGetTitle', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_get_position(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> Union[Position, None]: ...
    @overload
    def win_get_position(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[Union[Position, None]]: ...
    @overload
    def win_get_position(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> Union[Position, None]: ...
    @overload
    def win_get_position(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[Position, None, FutureResult[Union[Position, None]]]: ...
    # fmt: on
    def win_get_position(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[Position, None, FutureResult[Union[Position, None]]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinGetPos', args, blocking=blocking, engine=self)
        return resp


    # fmt: off
    @overload
    def win_get_idlast(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> Union[Window, None]: ...
    @overload
    def win_get_idlast(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[Union[Window, None]]: ...
    @overload
    def win_get_idlast(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> Union[Window, None]: ...
    @overload
    def win_get_idlast(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[Window, None, FutureResult[Union[Window, None]]]: ...
    # fmt: on
    def win_get_idlast(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[Window, None, FutureResult[Union[Window, None]]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinGetIDLast', args, blocking=blocking, engine=self)
        return resp

    # fmt: off
    @overload
    def win_get_pid(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> Union[int, None]: ...
    @overload
    def win_get_pid(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[Union[int, None]]: ...
    @overload
    def win_get_pid(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> Union[int, None]: ...
    @overload
    def win_get_pid(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[int, None, FutureResult[Union[int, None]]]: ...
    # fmt: on
    def win_get_pid(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[int, None, FutureResult[Union[int, None]]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinGetPID', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_get_process_name(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> Union[str, None]: ...
    @overload
    def win_get_process_name(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[Union[str, None]]: ...
    @overload
    def win_get_process_name(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> Union[str, None]: ...
    @overload
    def win_get_process_name(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[None, str, FutureResult[Optional[str]]]: ...
    # fmt: on
    def win_get_process_name(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[None, str, FutureResult[Optional[str]]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinGetProcessName', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_get_process_path(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> Union[str, None]: ...
    @overload
    def win_get_process_path(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[Union[str, None]]: ...
    @overload
    def win_get_process_path(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> Union[str, None]: ...
    @overload
    def win_get_process_path(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[str, None, Union[None, str, FutureResult[Optional[str]]]]: ...
    # fmt: on
    def win_get_process_path(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[str, None, Union[None, str, FutureResult[Optional[str]]]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinGetProcessPath', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_get_count(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> int: ...
    @overload
    def win_get_count(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[int]: ...
    @overload
    def win_get_count(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> int: ...
    @overload
    def win_get_count(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[int, FutureResult[int]]: ...
    # fmt: on
    def win_get_count(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[int, FutureResult[int]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinGetCount', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_get_minmax(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> Union[int, None]: ...
    @overload
    def win_get_minmax(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[Union[int, None]]: ...
    @overload
    def win_get_minmax(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> Union[int, None]: ...
    @overload
    def win_get_minmax(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[None, int, FutureResult[Optional[int]]]: ...
    # fmt: on
    def win_get_minmax(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[None, int, FutureResult[Optional[int]]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinGetMinMax', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_get_control_list(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> Union[List[Control], None]: ...
    @overload
    def win_get_control_list(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[Union[List[Control], None]]: ...
    @overload
    def win_get_control_list(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> Union[List[Control], None]: ...
    @overload
    def win_get_control_list(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[List[Control], None, FutureResult[Optional[List[Control]]]]: ...
    # fmt: on
    def win_get_control_list(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[List[Control], None, FutureResult[Optional[List[Control]]]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinGetControlList', args, blocking=blocking, engine=self)
        return resp

    # fmt: off
    @overload
    def win_get_from_mouse_position(self) -> Union[Window, None]: ...
    @overload
    def win_get_from_mouse_position(self, *, blocking: Literal[False]) -> FutureResult[Union[Window, None]]: ...
    @overload
    def win_get_from_mouse_position(self, *, blocking: Literal[True]) -> Union[Window, None]: ...
    @overload
    def win_get_from_mouse_position(self, *, blocking: bool = True) -> Union[Optional[Window], FutureResult[Optional[Window]]]: ...
    # fmt: on
    def win_get_from_mouse_position(
        self, *, blocking: bool = True
    ) -> Union[Optional[Window], FutureResult[Optional[Window]]]:
        raise NotImplementedError()

    # fmt: off
    @overload
    def win_exists(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> bool: ...
    @overload
    def win_exists(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[bool]: ...
    @overload
    def win_exists(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> bool: ...
    @overload
    def win_exists(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[bool, FutureResult[bool]]: ...
    # fmt: on
    def win_exists(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[bool, FutureResult[bool]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinExist', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_set_title(self, new_title: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> None: ...
    @overload
    def win_set_title(self, new_title: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> None: ...
    @overload
    def win_set_title(self, new_title: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def win_set_title(self, new_title: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def win_set_title(
        self,
        new_title: str,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        args = [new_title, title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinSetTitle', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_set_always_on_top(self, toggle: Literal['On', 'Off', 'Toggle', 1, -1, 0], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> None: ...
    @overload
    def win_set_always_on_top(self, toggle: Literal['On', 'Off', 'Toggle', 1, -1, 0], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def win_set_always_on_top(self, toggle: Literal['On', 'Off', 'Toggle', 1, -1, 0], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> None: ...
    @overload
    def win_set_always_on_top(self, toggle: Literal['On', 'Off', 'Toggle', 1, -1, 0], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def win_set_always_on_top(
        self,
        toggle: Literal['On', 'Off', 'Toggle', 1, -1, 0],
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        args = [str(toggle), title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinSetAlwaysOnTop', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_set_bottom(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> None: ...
    @overload
    def win_set_bottom(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def win_set_bottom(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> None: ...
    @overload
    def win_set_bottom(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def win_set_bottom(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinSetBottom', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_set_top(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> None: ...
    @overload
    def win_set_top(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def win_set_top(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> None: ...
    @overload
    def win_set_top(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def win_set_top(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinSetTop', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_set_disable(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> None: ...
    @overload
    def win_set_disable(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def win_set_disable(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> None: ...
    @overload
    def win_set_disable(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def win_set_disable(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinSetDisable', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_set_enable(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> None: ...
    @overload
    def win_set_enable(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def win_set_enable(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> None: ...
    @overload
    def win_set_enable(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def win_set_enable(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinSetEnable', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_set_redraw(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> None: ...
    @overload
    def win_set_redraw(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def win_set_redraw(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> None: ...
    @overload
    def win_set_redraw(self, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def win_set_redraw(
        self,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        args = [title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinSetRedraw', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_set_style(self, style: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> bool: ...
    @overload
    def win_set_style(self, style: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[bool]: ...
    @overload
    def win_set_style(self, style: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> bool: ...
    @overload
    def win_set_style(self, style: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[bool, FutureResult[bool]]: ...
    # fmt: on
    def win_set_style(
        self,
        style: str,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[bool, FutureResult[bool]]:
        args = [style, title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinSetStyle', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_set_ex_style(self, style: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> bool: ...
    @overload
    def win_set_ex_style(self, style: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[bool]: ...
    @overload
    def win_set_ex_style(self, style: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> bool: ...
    @overload
    def win_set_ex_style(self, style: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[bool, FutureResult[bool]]: ...
    # fmt: on
    def win_set_ex_style(
        self,
        style: str,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[bool, FutureResult[bool]]:
        args = [style, title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinSetExStyle', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_set_region(self, options: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> bool: ...
    @overload
    def win_set_region(self, options: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[bool]: ...
    @overload
    def win_set_region(self, options: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> bool: ...
    @overload
    def win_set_region(self, options: str, title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[bool, FutureResult[bool]]: ...
    # fmt: on
    def win_set_region(
        self,
        options: str,
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[bool, FutureResult[bool]]:
        args = [options, title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinSetRegion', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_set_transparent(self, transparency: Union[int, Literal['Off']], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> None: ...
    @overload
    def win_set_transparent(self, transparency: Union[int, Literal['Off']], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def win_set_transparent(self, transparency: Union[int, Literal['Off']], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> None: ...
    @overload
    def win_set_transparent(self, transparency: Union[int, Literal['Off']], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def win_set_transparent(
        self,
        transparency: Union[int, Literal['Off']],
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        args = [str(transparency), title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinSetTransparent', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def win_set_trans_color(self, color: Union[int, str], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> None: ...
    @overload
    def win_set_trans_color(self, color: Union[int, str], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def win_set_trans_color(self, color: Union[int, str], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> None: ...
    @overload
    def win_set_trans_color(self, color: Union[int, str], title: str = '', text: str = '', exclude_title: str = '', exclude_text: str = '', *, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: bool = True) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def win_set_trans_color(
        self,
        color: Union[int, str],
        title: str = '',
        text: str = '',
        exclude_title: str = '',
        exclude_text: str = '',
        *,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
        blocking: bool = True,
    ) -> Union[None, FutureResult[None]]:
        args = [str(color), title, text, exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')
        resp = self._transport.function_call('AHKWinSetTransColor', args, blocking=blocking)
        return resp

    # alias for backwards compatibility
    windows = list_windows

    # fmt: off
    @overload
    def right_click(self, x: Optional[Union[int, Tuple[int, int]]] = None, y: Optional[int] = None, *, click_count: Optional[int] = None, direction: Optional[Literal['U', 'D', 'Up', 'Down']] = None, relative: Optional[bool] = None, coord_mode: Optional[CoordModeRelativeTo] = None) -> None: ...
    @overload
    def right_click(self, x: Optional[Union[int, Tuple[int, int]]] = None, y: Optional[int] = None, *, click_count: Optional[int] = None, direction: Optional[Literal['U', 'D', 'Up', 'Down']] = None, relative: Optional[bool] = None, blocking: Literal[True], coord_mode: Optional[CoordModeRelativeTo] = None) -> None: ...
    @overload
    def right_click(self, x: Optional[Union[int, Tuple[int, int]]] = None, y: Optional[int] = None, *, click_count: Optional[int] = None, direction: Optional[Literal['U', 'D', 'Up', 'Down']] = None, relative: Optional[bool] = None, blocking: Literal[False], coord_mode: Optional[CoordModeRelativeTo] = None) -> FutureResult[None]: ...
    @overload
    def right_click(self, x: Optional[Union[int, Tuple[int, int]]] = None, y: Optional[int] = None, *, click_count: Optional[int] = None, direction: Optional[Literal['U', 'D', 'Up', 'Down']] = None, relative: Optional[bool] = None, blocking: bool = True, coord_mode: Optional[CoordModeRelativeTo] = None) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def right_click(
        self,
        x: Optional[Union[int, Tuple[int, int]]] = None,
        y: Optional[int] = None,
        *,
        click_count: Optional[int] = None,
        direction: Optional[Literal['U', 'D', 'Up', 'Down']] = None,
        relative: Optional[bool] = None,
        blocking: bool = True,
        coord_mode: Optional[CoordModeRelativeTo] = None,
    ) -> Union[None, FutureResult[None]]:
        button = 'R'
        return self.click(
            x,
            y,
            button=button,
            click_count=click_count,
            direction=direction,
            relative=relative,
            blocking=blocking,
            coord_mode=coord_mode,
        )

    # fmt: off
    @overload
    def click(self, x: Optional[Union[int, Tuple[int, int]]] = None, y: Optional[int] = None, *, button: Optional[Union[MouseButton, str]] = None, click_count: Optional[int] = None, direction: Optional[Literal['U', 'D', 'Up', 'Down']] = None, relative: Optional[bool] = None, coord_mode: Optional[CoordModeRelativeTo] = None) -> None: ...
    @overload
    def click(self, x: Optional[Union[int, Tuple[int, int]]] = None, y: Optional[int] = None, *, button: Optional[Union[MouseButton, str]] = None, click_count: Optional[int] = None, direction: Optional[Literal['U', 'D', 'Up', 'Down']] = None, relative: Optional[bool] = None, blocking: Literal[True], coord_mode: Optional[CoordModeRelativeTo] = None) -> None: ...
    @overload
    def click(self, x: Optional[Union[int, Tuple[int, int]]] = None, y: Optional[int] = None, *, button: Optional[Union[MouseButton, str]] = None, click_count: Optional[int] = None, direction: Optional[Literal['U', 'D', 'Up', 'Down']] = None, relative: Optional[bool] = None, blocking: Literal[False], coord_mode: Optional[CoordModeRelativeTo] = None) -> FutureResult[None]: ...
    @overload
    def click(self, x: Optional[Union[int, Tuple[int, int]]] = None, y: Optional[int] = None, *, button: Optional[Union[MouseButton, str]] = None, click_count: Optional[int] = None, direction: Optional[Literal['U', 'D', 'Up', 'Down']] = None, relative: Optional[bool] = None, blocking: bool = True, coord_mode: Optional[CoordModeRelativeTo] = None) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def click(
        self,
        x: Optional[Union[int, Tuple[int, int]]] = None,
        y: Optional[int] = None,
        *,
        button: Optional[Union[MouseButton, str]] = None,
        click_count: Optional[int] = None,
        direction: Optional[Literal['U', 'D', 'Up', 'Down']] = None,
        relative: Optional[bool] = None,
        blocking: bool = True,
        coord_mode: Optional[CoordModeRelativeTo] = None,
    ) -> Union[None, FutureResult[None]]:
        if x or y:
            if y is None and isinstance(x, tuple) and len(x) == 2:
                #  allow position to be specified by a two-sequence tuple
                x, y = x
            assert x is not None and y is not None, 'If provided, position must be specified by x AND y'
        if button is None:
            button = 'L'
        button = resolve_button(button)

        if relative:
            r = 'Rel'
        else:
            r = ''
        if coord_mode is None:
            coord_mode = ''
        args = [str(x), str(y), button, str(click_count), direction or '', r, coord_mode]
        resp = self._transport.function_call('AHKClick', args, blocking=blocking)
        return resp

    # fmt: off
    @overload
    def image_search(self, image_path: str, upper_bound: Tuple[Union[int, str], Union[int, str]] = (0, 0), lower_bound: Optional[Tuple[Union[int, str], Union[int, str]]] = None, *, color_variation: Optional[int] = None, coord_mode: str = 'Screen', scale_height: Optional[int] = None, scale_width: Optional[int] = None, transparent: Optional[str] = None, icon: Optional[int] = None) -> Optional[Tuple[int, int]]: ...
    @overload
    def image_search(self, image_path: str, upper_bound: Tuple[Union[int, str], Union[int, str]] = (0, 0), lower_bound: Optional[Tuple[Union[int, str], Union[int, str]]] = None, *, color_variation: Optional[int] = None, coord_mode: str = 'Screen', scale_height: Optional[int] = None, scale_width: Optional[int] = None, transparent: Optional[str] = None, icon: Optional[int] = None, blocking: Literal[False]) -> FutureResult[Optional[Tuple[int, int]]]: ...
    @overload
    def image_search(self, image_path: str, upper_bound: Tuple[Union[int, str], Union[int, str]] = (0, 0), lower_bound: Optional[Tuple[Union[int, str], Union[int, str]]] = None, *, color_variation: Optional[int] = None, coord_mode: str = 'Screen', scale_height: Optional[int] = None, scale_width: Optional[int] = None, transparent: Optional[str] = None, icon: Optional[int] = None, blocking: Literal[True]) -> Optional[Tuple[int, int]]: ...
    @overload
    def image_search(self, image_path: str, upper_bound: Tuple[Union[int, str], Union[int, str]] = (0, 0), lower_bound: Optional[Tuple[Union[int, str], Union[int, str]]] = None, *, color_variation: Optional[int] = None, coord_mode: str = 'Screen', scale_height: Optional[int] = None, scale_width: Optional[int] = None, transparent: Optional[str] = None, icon: Optional[int] = None, blocking: bool = True) -> Union[Tuple[int, int], None, FutureResult[Optional[Tuple[int, int]]]]: ...
    # fmt: on
    def image_search(
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
    ) -> Union[Tuple[int, int], None, FutureResult[Optional[Tuple[int, int]]]]:
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

        args = [str(x1), str(y1), str(x2), str(y2)]
        if options:
            s = ''
            for opt in options:
                s += f'*{opt} '
            s += image_path
            args.append(s)
        else:
            args.append(image_path)
        resp = self._transport.function_call('AHKImageSearch', args, blocking=blocking)
        return resp

    def mouse_drag(
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

    def pixel_get_color(
        self, x: int, y: int, coord_mode: str = 'Screen', alt: bool = False, slow: bool = False, rgb: bool = True
    ) -> str:
        raise NotImplementedError()

    def pixel_search(
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

    def show_traytip(
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
    def win_close(self, title: str = '', *, text: str = '', seconds_to_wait: Optional[int] = None, exclude_title: str = '', exclude_text: str = '', title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> None: ...
    @overload
    def win_close(self, title: str = '', *, text: str = '', seconds_to_wait: Optional[int] = None, exclude_title: str = '', exclude_text: str = '', title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[True]) -> None: ...
    @overload
    def win_close(self, title: str = '', *, text: str = '', seconds_to_wait: Optional[int] = None, exclude_title: str = '', exclude_text: str = '', title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None, blocking: Literal[False]) -> FutureResult[None]: ...
    @overload
    def win_close(self, title: str = '', *, text: str = '', seconds_to_wait: Optional[int] = None, exclude_title: str = '', exclude_text: str = '', blocking: bool = True, title_match_mode: Optional[TitleMatchMode] = None, detect_hidden_windows: Optional[bool] = None) -> Union[None, FutureResult[None]]: ...
    # fmt: on
    def win_close(
        self,
        title: str = '',
        *,
        text: str = '',
        seconds_to_wait: Optional[int] = None,
        exclude_title: str = '',
        exclude_text: str = '',
        blocking: bool = True,
        title_match_mode: Optional[TitleMatchMode] = None,
        detect_hidden_windows: Optional[bool] = None,
    ) -> Union[None, FutureResult[None]]:
        args: List[str]
        args = [title, text, str(seconds_to_wait) if seconds_to_wait is not None else '', exclude_title, exclude_text]
        if detect_hidden_windows is not None:
            if detect_hidden_windows is True:
                args.append('On')
            elif detect_hidden_windows is False:
                args.append('Off')
            else:
                raise TypeError(
                    f'Invalid value for parameter detect_hidden_windows. Expected boolean or None, got {detect_hidden_windows!r}'
                )
        else:
            args.append('')
        if title_match_mode is not None:
            if isinstance(title_match_mode, tuple):
                match_mode, match_speed = title_match_mode
            elif title_match_mode in (1, 2, 3, 'RegEx'):
                match_mode = title_match_mode
                match_speed = ''
            elif title_match_mode in ('Fast', 'Slow'):
                match_mode = ''
                match_speed = title_match_mode
            else:
                raise ValueError(
                    f"Invalid value for title_match_mode argument. Expected 1, 2, 3, 'RegEx', 'Fast', 'Slow' or a tuple of these. Got {title_match_mode!r}"
                )
            args.append(str(match_mode))
            args.append(str(match_speed))
        else:
            args.append('')
            args.append('')

        resp = self._transport.function_call('AHKWinClose', args=args, blocking=blocking)
        return resp

    def block_forever(self) -> NoReturn:
        while True:
            sleep(1)
