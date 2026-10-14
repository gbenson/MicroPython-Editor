#
# Pygame front end.
#
from __future__ import annotations

import re

class AbstractTerminal:
    """Methods expected by `pye_edit()`.
    """
    def get_screen_size(self) -> tuple[int, int]:
        raise NotImplementedError

    def wr(self, s: str) -> None:
        raise NotImplementedError(repr(s))

    def rd(self) -> str:
        raise NotImplementedError

    # get_screen_size, wr and rd are always required;
    # rd_raw is only called if rd returns KEY_MOUSE.
    def rd_raw(self) -> str:
        raise NotImplementedError


_ESCAPE_SEQUENCE_RX = re.compile("\x1B(.*?[A-Za-z])")


class PygameTerminal(AbstractTerminal):
    _CONST_COMMANDS = {
        ##"\x1B[{row};{col}H",  ## 0: Set cursor
        "\x1B[0K": "_clear_to_eol",  # emacs: C-k
        "\x1B[?25h": "_cursor_on",
        "\x1B[?25l": "_cursor_off",
        "\x1B[0m": "_highlight_off",     # plain text
        "\x1B[1;37;44m": "_highlight_1", # status line
        #"\x1B[43m": "_highlight_2",      # selected text
        "\x1B[?9h": "_mouse_reporting_on",
        #"\x1B[?9l": "_8: Mouse reporting off
        #"\x1BM": "_9: Scroll one line up
        #"\n": "_10: Scroll one line down
        ##"\x1B[1;{stop}r": "_11: Set lowest line of scrolling range
        #"\x1B[r": "_12: Scroll the full screen
        #"\b": "_13: backspace one character, used in line_edit
        ## 14: Long status line format string.
        #"{chd}{file} Row: {row}/{total} Col: {col}  {msg}",
        ## 15: Shorter status line format string.
        #"{chd}{file} {row}:{col}  {msg}",
    }

    _OTHER_COMMANDS = {
        "H": "_cursor_position",
        "r": "_set_scroll_region_end",
    }

    def __init__(self, width: int = 480, height: int = 480, scale: int = 2):
        pass

    def get_screen_size(self) -> tuple[int, int]:
        return (60, 60)  # XXX

    def __enter__(self) -> PygameTerminal:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        return False  # don't suppress exception

    def wr(self, s: str) -> None:
        if s.isprintable():
            X = "\x1B[48;5;232;1;31m"
            print(f"{X}>\x1B[0m{s}{X}<\x1B[0m")
            return
        elif (cmd := self._CONST_COMMANDS.get(s)):
            return getattr(self, cmd)()
        elif (m := _ESCAPE_SEQUENCE_RX.match(s)):
            seq = m.group(1)
            if (cmd := self._OTHER_COMMANDS.get(seq[-1])):
                return getattr(self, cmd)(seq[:-1])
            raise NotImplementedError(f"{s!r} -> ESC {seq[-1]}")
        else:
            raise NotImplementedError(repr(s))

    def _clear_to_eol(self) -> None:
        print("\x1B[40;38;5;226m clear to end of line \x1B[0m")

    def _cursor_off(self) -> None:
        print("\x1B[40;38;5;226m cursor off \x1B[0m")

    def _cursor_on(self) -> None:
        print("\x1B[40;38;5;226m cursor on \x1B[0m")

    def _highlight_off(self) -> None:
        print("\x1B[40;38;5;226m highlight off (plain text) \x1B[0m")

    def _highlight_1(self) -> None:
        print("\x1B[40;38;5;226m highlight 1 (status bar) \x1B[0m")

    def _mouse_reporting_on(self) -> None:
        print("\x1B[48;5;236;38;5;8m mouse reporting on \x1B[0m")

    def _cursor_position(self, s: str) -> None:
        assert s.startswith("[")
        row, column = s[1:].split(";")
        print(f"\x1B[40;38;5;226m cursor position ({row}, {column}) \x1B[0m")

    def _set_scroll_region_end(self, s: str) -> None:
        assert s.startswith("[1;")
        row = int(s[3:])
        print(f"\x1B[40;38;5;226m set scroll region end {row} \x1B[0m")


## test, if the Editor class is already present
if "pye_edit" not in globals().keys():
    from pye_core import pye_edit


def pye(*args, tab_size=4, undo=50):
    with PygameTerminal() as io_device:
        return pye_edit(args, tab_size=tab_size, undo=undo, io_device=io_device)


if __name__ == "__main__":
    import sys
    pye(sys.argv[1:], undo=500)
