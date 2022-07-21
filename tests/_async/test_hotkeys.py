import asyncio
import os
import subprocess
import sys
import time
from unittest import IsolatedAsyncioTestCase
from unittest import mock

from ahk import AsyncAHK
from ahk import AsyncWindow

async_sleep = asyncio.sleep  # unasync: remove

sleep = time.sleep


class TestMouseAsync(IsolatedAsyncioTestCase):
    win: AsyncWindow

    async def asyncSetUp(self) -> None:
        self.ahk = AsyncAHK()

    async def asyncTearDown(self) -> None:
        self.ahk.stop_hotkeys()
        self.ahk._transport._proc.kill()

    async def test_hotkey(self):
        with mock.MagicMock(return_value=None) as m:
            self.ahk.add_hotkey('a', callback=m)
            self.ahk.start_hotkeys()
            await self.ahk.key_down('a')
            m.assert_called()

    async def test_hotkey_ex_handler(self):
        def side_effect():
            raise Exception('oh no')

        with mock.MagicMock() as mock_cb, mock.MagicMock() as mock_ex_handler:
            mock_cb.side_effect = side_effect
            self.ahk.add_hotkey('a', callback=mock_cb, ex_handler=mock_ex_handler)
            self.ahk.start_hotkeys()
            await self.ahk.key_down('a')
            mock_ex_handler.assert_called()
