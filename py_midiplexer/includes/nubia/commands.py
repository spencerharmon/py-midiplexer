from nubia import command, argument, context
from termcolor import cprint
from py_midiplexer import exceptions
import multiprocessing
import logging
import time

def print_exceptions(func):
    #nubia autocommand error trying to load '_wrapped' when I use this wrapper.. hm...
    def _wrapped(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except exceptions.PyMidiPlexerException as e:
            cprint(e.msg)
    return _wrapped

@command("scene")
class SceneCommands(object):
    """
    Commands that interact with a scene
    """
    def __init__(self, scenelabel=None):
        self.midiplexer = context.get_context().midiplexer
        if scenelabel is None:
            self._label = f"scene{len(self.midiplexer.scenes.keys())}"
        else:
            self._label = scenelabel
        
    @command
    def add_signal(self, controller=None, signal=None):
        """
        Deprecated. Use `scene-map add` instead.
        Add a controller signal that triggers the specified scene.
        """
        if controller is None or signal is None:
            for ctrlr in self.context.midiplexer.controllers:
              #todo:listen for signal
                pass
        try:
            self.context.midiplexer.assign_scene(controller, signal, self._label)
        except exceptions.PyMidiPlexerExceptions as e:
            cprint(e.msg, color='red')

    @command
    def add_track(self, clientlabel='', tracklabel=''):
        """
        Adds a client track to a scene.
        """
        self.midiplexer.command_queue.put({'add_track_to_scene':(clientlabel, tracklabel, self._label)})
        
    @command
    def list(self):
        """
        List all scenes.
        """
        #todo: stdout queue
        self.midiplexer.command_queue.put({"get_scenes_stdout":()})
        
        cprint(self.midiplexer.stdout_queue.get().__str__())

    @command
    def create_scene_from_current(self):
        """
        Overwrites or creates a scene with all of the currently-playing tracks in it. 
        """
        self.midiplexer.command_queue.put({"create_scene_from_current":(self._label,)})


@command("controller")
class ControllerCommands(object):
    """
    Commands that interact with a controller
    """
    def __init__(self, ctlrlabel=None):
        self.context = context.get_context()
        if ctlrlabel is None:
            self._label = f"ctlr{len(self.context.midiplexer.controllers)}"
        else:
            self._label = ctlrlabel

    @command
    def add(self, type='midi'):
        """
        add the specified controller
        """
        self.context.midiplexer.command_queue.put({'add_controller': (self._label, type)})

    @command
    def list(self):
        """
        list all controllers
        """
        #todo: use stdout_queue.
        cprint([ctlr.__dict__() for ctlr in self.context.midiplexer.controllers].__str__())

    @command
    def register_signal(self, signal_label=None):
        """
        register the next midi signal received
        """
        self.context.midiplexer.command_queue.put({'register_controller_signal':(self._label, signal_label)})

    @command
    def register_modeswitch(self, signal_label='modeswitch'):
        """
        register the next midi signal as the mode switch.
        """
        self.context.midiplexer.command_queue.put({'register_modeswitch':(self._label, signal_label)})

@command("client")
class ClientCommands(object):
    """
    Entrypoint to create and modify client attributes.
    """
    def __init__(self, name=''):
        self.midiplexer = context.get_context().midiplexer
        self.name = name
        self.logger = logging.getLogger(self.__class__.__name__)
            
    @command
    def add(self, toggle_record=False, type='midi'):
        """
        Create the named client. In midi mode, Creates an output jack port. 

        """
        client = self.midiplexer.command_queue.put({'add_client': (self.name, toggle_record, type)})

    @command
    def clear(self, tracklabel):
        """
        sets a track's toggle_record state to True and playing state to false. "resets" luppp tracks.
        """    
        self.midiplexer.command_queue.put({'track_toggle_record':(self.name, tracklabel)})

    @command
    def add_track(self,
                     label="",
                     midi_type="",
                     channel: int=0,
                     note: int=0,
                     control: int=0,
                     velocity: int=64,
                     value: int=0,
                     pitch: int=0,
                     data: int=0,
                     frame_type: int=0,
                     frame_value: int=0,
                     pos: int=0,
                     song: int=0):
        """
        instantiate a track object. to determine the needed kwargs, check the output of the subcommand `client add-track-help`
        """
        attrs = {}
        attrs.update({"type":midi_type})
        dat = {}
        dat.update({"channel":channel})
        dat.update({"note":note})
        dat.update({"control":control})
        dat.update({"velocity":velocity})
        dat.update({"value":value})
        dat.update({"pitch":pitch})
        dat.update({"data":data})
        dat.update({"frame_type":frame_type})
        dat.update({"frame_value":frame_value})
        dat.update({"pos":pos})
        dat.update({"song":song})
        attrs.update({"data":dat})

        self.midiplexer.command_queue.put({'client_add_track':(self.name, label, attrs)})

    @command
    def create_track_help(self):
        """
        which options you should use for create_track. Could be more helpful.
        """
        midi_message_options = [{"type":"note_off",
                "data":{ "channel":0, "note":0, "velocity":64}},
            {"type":"note_on",
                "data":{ "channel":0, "note":0, "velocity":64}},
            {"type":"polytouch",
                "data":{ "channel":0, "note":0, "value":0}},
            {"type":"control_change",
                "data":{ "channel":0, "control":0, "value":0}},
            {"type":"program_change",
                "data":{ "channel":0, "program":0}},
            {"type":"aftertouch",
                "data":{ "channel":0, "value":0}},
            {"type":"pitchwheel",
                "data":{ "channel":0, "pitch":0}},
            {"type":"sysex",
                "data":{ "data":0}},
            {"type":"quarter_frame",
                "data":{ "frame_type":0, "frame_value":0}},
            {"type":"songpos",
                "data":{ "pos":0}},
            {"type":"song_select",
                "data":{ "song":0}},
            {"type":"tune_request",
                "data":{}},
            {"type":"clock",
                "data":{}},
            {"type":"start",
                "data":{}},
            {"type":"continue",
                "data":{}},
            {"type":"stop",
                "data":{}},
            {"type":"reset",
                "data":{}}
        ]
        cprint(midi_message_options.__str__())
        
    @command
    def list(self):
        """
        Lists all clients regardless of arguments specified.
        """
        out = []
        for client in self.context.midiplexer.clients:
#            for name, client in c.items():
                out.append(client.__dict__())
                
        cprint(out.__str__())

    @command
    def list_tracks(self):
        """
        List all tracks for the specified client.
        """
        self.midiplexer.command_queue.put({'client_list_tracks': self.name})
        for i in range(100):
            if self.midiplexer.stdout_queue.empty():
                time.sleep(0.03)
            else:
                out = self.midiplexer.stdout_queue.get_nowait()
                #todo: prettify output.
                cprint(out.__str__())
                return
        self.logger.error("list-tracks timed out.")
    
            
@command("trigger-map")
class TriggerMapCommands(object):
    """
    Map controller signals to client tracks.
    """
    def __init__(self, controller: str='', signal='', client: str='', track=''):
        self.midiplexer = context.get_context().midiplexer
        self.controller = controller
        self.signal = signal
        self.client = client
        self.track = track

    @command
    def add(self):
        """
        Create a new triggermapping.
        """
        self.midiplexer.command_queue.put({'assign_track':(self.controller, self.signal, self.client, self.track)})

    @command
    def delete(self):
        """
        Coming soon.
        """
        #todo
        pass
    
    @command
    def show(self):
        """
        show the trigger map.
        """
        self.midiplexer.command_queue.put({"get_trigger_map_stdout":()})
        cprint(self.midiplexer.stdout_queue.get().__str__())
        
@command("scene-map")
class SceneMapCommands(object):
    """
    Map a controller signal to a scene.
    """
    def __init__(self, controller: str='', signal='', scene: str=''):
        self.midiplexer = context.get_context().midiplexer
        self.controller = controller
        self.signal = signal
        self.scene= scene

    @command
    def add(self):
        """
        Create a new scene mapping.
        """
        # todo: this is broken since adding the command queue to the MidiPlexer class.
        self.midiplexer.command_queue.put({'assign_scene':(self.controller, self.signal, self.scene)})

    @command
    def delete(self):
        """
        Coming soon.
        """
        #todo
        pass

    @command
    def show(self):
        """
        show the scene map.
        """
        self.midiplexer.command_queue.put({"get_scene_map_stdout":()})
        cprint(self.midiplexer.stdout_queue.get().__str__())


@command
def save():
    """
    Save the state of pymidiplexer to a file.
    """
    context.get_context().midiplexer.command_queue.put({'save':()})
