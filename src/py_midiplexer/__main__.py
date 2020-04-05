import mido
from .controller import MidiController
from .client import MidiClient
from .py_midiplexer import MidiPlexer
from pprint import pprint

import sys
from nubia import Nubia, Options
from .includes.nubia.nubia_plugin import NubiaMidiPlexerPlugin

if __name__ == "__main__":
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

mux = MidiPlexer()

fc300 = mux.add_controller('fc300')
print('register sig 0')
fc300.register(0)
print('register dup 0')
fc300.register(0)
print('register sig 1')
fc300.register(1)
print('register dup 1')
fc300.register(1)
print('register mode switch')
fc300.register('switch')
print('register mode switch dup')
fc300.register('switch')


non = mux.add_client("non-sequencer")
non.create_track(0, 'control_change', {'control':20, 'value':0})
non.create_track(1, 'control_change', {'control':20, 'value':1})

mux.assign_mode_switch("fc300", 'switch')

mux.add_track_to_scene("non-sequencer", 0, "scene1")
mux.add_track_to_scene("non-sequencer", 1, "scene1")

mux.assign_track("fc300", 0, "non-sequencer", 0)
mux.assign_track("fc300", 1, "non-sequencer", 1)

mux.assign_scene("fc300", 0, "scene1")
mux.assign_scene("fc300", 1, "off")


pprint(mux.__dict__())
if __name__ == '__main__':
    while True:
        rcv = fc300.listen()
        print(f'received signal: {rcv}')
        mux.handle_signal("fc300", rcv)

    sys.exit(0)
