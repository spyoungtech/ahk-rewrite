from __future__ import annotations

import ast
import itertools
import string
import sys
from abc import abstractmethod
from base64 import b64encode
from collections import namedtuple
from typing import Any
from typing import cast
from typing import Generator
from typing import List
from typing import NoReturn
from typing import Optional
from typing import Protocol
from typing import runtime_checkable
from typing import Tuple
from typing import Type
from typing import TYPE_CHECKING

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard
from typing import TypeVar
from typing import Union


class OutOfMessageTypes(Exception):
    ...


Position = namedtuple('Position', ('x', 'y', 'width', 'height'))


@runtime_checkable
class BytesLineReadable(Protocol):
    def readline(self) -> bytes:
        ...


def is_window_control_list_response(resp_obj: object) -> TypeGuard[Tuple[str, List[Tuple[str, str]]]]:
    if not isinstance(resp_obj, tuple):
        return False
    if len(resp_obj) != 2:
        return False
    if not isinstance(resp_obj[0], str):
        return False
    expected_win_list = resp_obj[1]
    if not isinstance(expected_win_list, list):
        return False
    for obj in expected_win_list:
        if not isinstance(obj, tuple):
            return False
        if len(obj) != 2:
            return False
        id_, klass = obj
        if not isinstance(id_, str) or not isinstance(klass, str):
            return False
    return True


def is_winget_response_type(
    obj: object,
) -> TypeGuard[
    Union[
        'StringResponseMessage',
        'IntegerResponseMessage',
        'WindowListResponseMessage',
        'WindowControlListResponseMessage',
    ]
]:
    if isinstance(obj, StringResponseMessage):
        return True
    elif isinstance(obj, IntegerResponseMessage):
        return True
    elif isinstance(obj, WindowListResponseMessage):
        return True
    elif isinstance(obj, WindowControlListResponseMessage):
        return True
    elif isinstance(obj, NoValueResponseMessage):
        return True
    else:
        return False


T_ResponseMessageType = TypeVar('T_ResponseMessageType', bound='ResponseMessage')


def tom_generator() -> Generator[bytes, None, None]:
    characters = string.digits + string.ascii_letters
    for a, b, c in itertools.product(characters, characters, characters):
        yield bytes(f'{a}{b}{c}', encoding='ascii')
    raise OutOfMessageTypes('Out of TOMS')


TOMS = tom_generator()


class ResponseMessage:
    type: Optional[str] = None
    _type_order_mark = next(TOMS)

    @classmethod
    def __init_subclass__(cls: Type[T_ResponseMessageType], **kwargs: Any) -> None:
        tom = next(TOMS)
        cls._type_order_mark = tom
        assert tom not in _message_registry, f'cannot register class {cls!r} with TOM {tom!r} which is already in use'
        _message_registry[tom] = cls
        assert cls.type is not None, f'must assign a type for class {cls!r}'
        super().__init_subclass__(**kwargs)

    def __init__(self, raw_content: bytes, engine: Optional[Union[AsyncAHK, AHK]] = None):
        self._raw_content: bytes = raw_content
        self._engine: Optional[Union[AsyncAHK, AHK]] = engine

    def __repr__(self) -> str:
        return f'ResponseMessage<type={self.type!r}>'

    @staticmethod
    def _tom_lookup(tom: bytes) -> 'ResponseMessageClassTypes':
        klass = _message_registry.get(tom)
        if klass is None:
            raise ValueError(f'No such TOM {tom!r}')
        return klass

    @classmethod
    def from_bytes(
        cls: Type[T_ResponseMessageType], b: bytes, engine: Optional[Union[AsyncAHK, AHK]] = None
    ) -> 'ResponseMessageTypes':
        tom, _, message_bytes = b.split(b'\n', 2)
        klass = cls._tom_lookup(tom)
        return klass(raw_content=message_bytes, engine=engine)

    def to_bytes(self) -> bytes:
        content_lines = self._raw_content.count(b'\n')
        return self._type_order_mark + b'\n' + bytes(str(content_lines), 'ascii') + b'\n' + self._raw_content

    @abstractmethod
    def unpack(self) -> Any:
        return NotImplemented


_message_registry: dict[bytes, 'ResponseMessageClassTypes']
_message_registry = {ResponseMessage._type_order_mark: ResponseMessage}


class TupleResponseMessage(ResponseMessage):
    type = 'tuple'

    def unpack(self) -> Tuple[Any, ...]:
        s = self._raw_content.decode(encoding='utf-8')
        val = ast.literal_eval(s)
        assert isinstance(val, tuple)
        return val


class CoordinateResponseMessage(ResponseMessage):
    type = 'coordinate'

    def unpack(self) -> Tuple[int, int]:
        s = self._raw_content.decode(encoding='utf-8')
        val = ast.literal_eval(s)
        assert isinstance(val, tuple)
        x, y = cast(Tuple[int, int], val)
        return x, y


class IntegerResponseMessage(ResponseMessage):
    type = 'integer'

    def unpack(self) -> int:
        s = self._raw_content.decode(encoding='utf-8')
        val = ast.literal_eval(s)
        assert isinstance(val, int)
        return val


class BooleanResponseMessage(IntegerResponseMessage):
    type = 'boolean'

    def unpack(self) -> bool:
        val = super().unpack()
        assert val in (1, 0)
        return bool(val)


class StringResponseMessage(ResponseMessage):
    type = 'string'

    def unpack(self) -> str:
        return self._raw_content.decode('utf-8')


class WindowListResponseMessage(ResponseMessage):
    type = 'windowlist'

    def unpack(self) -> Union[List[Window], List[AsyncWindow]]:
        from ._async.engine import AsyncAHK
        from ._async.window import AsyncWindow
        from ._sync.window import Window
        from ._sync.engine import AHK

        s = self._raw_content.decode(encoding='utf-8')
        s = s.rstrip(',')
        window_ids = s.split(',')
        if isinstance(self._engine, AsyncAHK):
            async_ret = [AsyncWindow(engine=self._engine, ahk_id=ahk_id) for ahk_id in window_ids if ahk_id]
            return async_ret
        elif isinstance(self._engine, AHK):
            ret = [Window(engine=self._engine, ahk_id=ahk_id) for ahk_id in window_ids if ahk_id]
            return ret
        else:
            raise ValueError(f'Invalid engine: {self._engine!r}')


class NoValueResponseMessage(ResponseMessage):
    type = 'novalue'

    def unpack(self) -> None:
        assert self._raw_content == b'\xee\x80\x80', f'Unexpected or Malformed response: {self._raw_content!r}'
        return None


class AHKExecutionException(Exception):
    pass


class ExceptionResponseMessage(ResponseMessage):
    type = 'exception'

    def unpack(self) -> NoReturn:
        s = self._raw_content.decode(encoding='utf-8')
        raise AHKExecutionException(s)


class WindowControlListResponseMessage(ResponseMessage):
    type = 'windowcontrollist'

    def unpack(self) -> Union[List[AsyncControl], List[Control]]:
        from ._async.engine import AsyncAHK
        from ._async.window import AsyncWindow, AsyncControl
        from ._sync.window import Window, Control
        from ._sync.engine import AHK

        s = self._raw_content.decode(encoding='utf-8')
        val = ast.literal_eval(s)
        assert is_window_control_list_response(val)
        assert self._engine is not None
        assert val is not None
        ahkid, controls = val
        if isinstance(self._engine, AsyncAHK):
            ret_async: List[AsyncControl] = []
            async_window = AsyncWindow(engine=self._engine, ahk_id=ahkid)
            for control in controls:
                hwnd, classname = control
                async_ctrl = AsyncControl(window=async_window, hwnd=hwnd, control_class=classname)
                ret_async.append(async_ctrl)
            return ret_async
        elif isinstance(self._engine, AHK):
            ret_sync: List[Control] = []
            window = Window(engine=self._engine, ahk_id=ahkid)
            for control in controls:
                hwnd, classname = control
                ctrl = Control(window=window, hwnd=hwnd, control_class=classname)
                ret_sync.append(ctrl)
            return ret_sync
        else:
            raise ValueError(f'Invalid engine: {self._engine!r}')


class WindowResponseMessage(ResponseMessage):
    type = 'window'

    def unpack(self) -> Union[Window, AsyncWindow]:
        from ._async.engine import AsyncAHK
        from ._async.window import AsyncWindow
        from ._sync.window import Window
        from ._sync.engine import AHK

        s = self._raw_content.decode(encoding='utf-8')
        ahk_id = s.strip()
        if isinstance(self._engine, AsyncAHK):
            async_ret = AsyncWindow(engine=self._engine, ahk_id=ahk_id)
            return async_ret
        elif isinstance(self._engine, AHK):
            ret = Window(engine=self._engine, ahk_id=ahk_id)
            return ret
        else:
            raise ValueError(f'Invalid engine: {self._engine!r}')


class PositionResponseMessage(TupleResponseMessage):
    type = 'position'

    def unpack(self) -> Position:
        resp = super().unpack()
        if not len(resp) == 4:
            raise ValueError(f'Unexpected response. Expected tuple of length 4, got tuple of length {len(resp)}')
        pos = Position(*resp)
        return pos


T_RequestMessageType = TypeVar('T_RequestMessageType', bound='RequestMessage')


class RequestMessage:
    def __init__(self, function_name: str, args: Optional[List[str]] = None):
        self.function_name: str = function_name
        self.args: List[str] = args or []

    def format(self) -> bytes:
        arg_binary = b'|'.join(b64encode(bytes(arg, 'UTF-8')) for arg in self.args)
        ret = bytes(self.function_name, 'UTF-8') + b'|' + arg_binary + b'\n'
        return ret


ResponseMessageTypes = Union[
    ResponseMessage,
    TupleResponseMessage,
    CoordinateResponseMessage,
    IntegerResponseMessage,
    BooleanResponseMessage,
    StringResponseMessage,
    WindowListResponseMessage,
    NoValueResponseMessage,
    WindowControlListResponseMessage,
    ExceptionResponseMessage,
    PositionResponseMessage,
]
ResponseMessageClassTypes = Union[
    Type[PositionResponseMessage],
    Type[TupleResponseMessage],
    Type[CoordinateResponseMessage],
    Type[IntegerResponseMessage],
    Type[BooleanResponseMessage],
    Type[StringResponseMessage],
    Type[WindowListResponseMessage],
    Type[NoValueResponseMessage],
    Type[WindowControlListResponseMessage],
    Type[ExceptionResponseMessage],
    Type[ResponseMessage],
]
if TYPE_CHECKING:
    from ._async.engine import AsyncAHK
    from ._async.window import AsyncWindow, AsyncControl
    from ._sync.window import Window, Control
    from ._sync.engine import AHK
