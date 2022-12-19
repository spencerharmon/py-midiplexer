import mido
from .controller import MidiController
from .client import MidiClient
from .py_midiplexer import MidiPlexer

import sys
from nubia import Nubia, Options
from .includes.nubia.nubia_plugin import NubiaMidiPlexerPlugin


def main():
    muxer = MidiPlexer()

    plugin = NubiaMidiPlexerPlugin(muxer)
    shell = Nubia(
        name="py_midiplexer",
        plugin=plugin,
        options=Options(persistent_history=True),
    )
    shell.run()
    muxer.shutdown()
    sys.exit()
