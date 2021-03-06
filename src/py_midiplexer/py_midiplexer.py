from enum import Enum
from pprint import pprint
from py_midiplexer.controller import MidiController, Controller
from py_midiplexer.client import MidiClient, Client
from py_midiplexer import exceptions
import multiprocessing
from multiprocessing.sharedctypes import Array
from ctypes import c_char
import logging
import queue
import time
import traceback
import os
import json

class Mode(Enum):
    """
    I think the most important distinction between trigger and scene is that trigger just fires off signals at the specified
    client(s)/track(s), but scene tries to turn off other tracks. It's not perfect since we don't have any feedback on the current
    state of a track (yet. Can you say OSC?). So, for now, we'll blindly assume that everything will be found exactly as midiplexer
    left it (or at least hope that the user manually returned things to the expected state). 
    It was going to be that trigger was one-at-a-time, but it's frankly too much work to enforce that, and what's the point? It's
    an option to do one-at-a-time, just don't screw up the config. 
    """
    TRIGGER = 1
    SCENE = 2
    
class MidiPlexer(multiprocessing.Process):
    def __init__(self, f=os.environ['HOME']+'/.config/py-midiplexer/config.json', daemon_mode=True):
        self.logger = logging.getLogger('MidiPlexer')
        self.shutdown_callback = multiprocessing.Event()
        self.signal_queue = multiprocessing.Queue()
        self.command_queue = multiprocessing.Queue()
        self.stdout_queue = multiprocessing.Queue()
        self.config_queue = multiprocessing.Queue()
        self.status_queue = multiprocessing.Queue()

        self.daemon_mode = daemon_mode
        self.config = f

        self.saved = True
        self.clients = []
        self.controllers = []
        self.scenes = {}
        self.controller_signal_scene_map = {}
        self.controller_signal_trigger_map = {}
        self.mode_switch = {}
        self.mode = Mode.TRIGGER

        super().__init__()

    def controller_listen(self, controller: Controller):
            signal = controller.check()
            if signal is not None:
                self.handle_signal(controller.name, signal)


    def create_scene_from_current(self, scene_label):
        """
        Adds a new scene to the config based on the currently-playing tracks across all clients
        """
        scene_dict = {}
        for client in self.clients:
            client.command_queue.put({'queue_trackstate_playing':None})
            scene_dict.update({client.name: client.trackstate_queue.get()})
        self.scenes.update({scene_label: scene_dict})

        self.saved = False
            
        

    def load_config(self, f=None):
#        from .config import conf
#        self.process_conf_dict(conf)
#        return
        mdict = None
        config = f if f is not None else self.config
        if config is not None and config != '':
            with open(config) as f:
                try:
                    mdict = json.load(f)
                except json.decoder.JSONDecodeError as e:
                    self.logger.error("Invalid JSON file. Will overwrite.")
                    self.logger.error(''.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)))
        if mdict is not None:
            self.process_conf_dict(mdict)
            self.logger.warn("Loaded config {config}")
            self.logger.debug(json.dumps(mdict))

            self.saved = True

    def process_conf_dict(self, conf):
        for client in conf['clients']:
            self.add_client(client['name'], toggle_record=client['toggle_record'], type=client['type'], tracks=client['tracks'])
        for ctrlr in conf['controllers']:
            self.add_controller(ctrlr['name'], type=ctrlr['type'], signal_map=ctrlr['signal_map']) 
        self.scenes = conf['scenes']
        self.controller_signal_scene_map = conf['controller_signal_scene_map']
        self.controller_signal_trigger_map = conf['controller_signal_trigger_map']
        self.mode_switch = conf['mode_switch']
        
    def add_controller(self, name, type='midi', signal_map={}):
        self.logger.debug(f'command received: add controller "{name}"')
        if type == 'midi': #maybe someday we'll have an osc controller class...
            controller = MidiController(self.shutdown_callback, self.signal_queue, self.stdout_queue, name, signal_map=signal_map)
            self.controllers.append(controller)
            if self.daemon_mode:
                controller.start()
        self.saved = False

    def add_client(self, name, toggle_record=False, type='midi', tracks={}):
        if type == 'midi': #maybe someday we'll have an osc client class...
            client = MidiClient(self.shutdown_callback, self.stdout_queue, name, tracks=tracks, toggle_record=toggle_record)
            self.clients.append(client)
            if self.daemon_mode:
                client.start()
        self.saved = False

    def client_add_track(self, client_name, track_label, attrs):
        for client in self.clients:
            if client.name == client_name:
                client.command_queue.put({'create_track':(track_label, attrs)})
        self.saved = False

    def client_list_tracks(self, client_name):
        for client in self.clients:
            if client.name == client_name:
                client.command_queue.put({'list_tracks':None})
                
    def add_scene(self, scene: str):
        self.scenes.update({scene: {}})
        self.saved = False
        
    def add_track_to_scene(self, client: str, track_label, scene: str):
        if scene not in self.scenes.keys():
            self.add_scene(scene)
        if client in self.scenes[scene].keys():
            self.scenes[scene][client].append(track_label)
        else:
            self.scenes[scene].update({client: [track_label]})
        self.saved = False

    def assign_track(self, controller: str, signal, client: str, track_label):
        if controller in self.controller_signal_trigger_map.keys():
            if signal in self.controller_signal_trigger_map[controller].keys():
                if client in self.controller_signal_trigger_map[controller][signal].keys():
                    self.controller_signal_trigger_map[controller][signal][client].append(track_label)
                else:
                    self.controller_signal_trigger_map[controller][signal].update({client: [track_label]})
            else:
                self.controller_signal_trigger_map[controller].update({signal: {client: [track_label]}})
        else:
            self.controller_signal_trigger_map.update({controller: {signal: {client: [track_label]}}})
        self.saved = False
        
    def assign_scene(self, controller: str, signal, scene: str):
        if scene not in self.scenes.keys():
            self.add_scene(scene)
        if controller in self.controller_signal_scene_map.keys():
            if signal in self.controller_signal_scene_map[controller].keys():
                self.controller_signal_scene_map[controller][signal].update(scene)
            else:
                self.controller_signal_scene_map[controller].update({signal: scene})
        else:
            self.controller_signal_scene_map.update({controller: {signal: scene}})
        self.saved = False

    def assign_mode_switch(self, controller: str, signal):
        if controller not in self.mode_switch.keys():
            self.mode_switch.update({controller: [signal]})
        else:
            self.mode_switch[controller].append(signal)
        self.saved = False

    def controller_signal_exists(self, controller: str, signal: int) -> bool:
        for c in self.controllers:
            if c.name == controller:
                for k, v in c.signal_map.items():
                    if v == signal:
                        return True
        return False
        
    def client_track_exists(self, client: str, track_label) -> bool:
        for cli in self.clients:
            if cli.name == client:
                for label, track in cli.tracks.items():
                    if label == track_label:
                        return True
        return False
        
    def trigger_scene(self, scene: int):
        """
        scene presses are idempotent. Multiple presses should have no effect.
        an empty scene turns off all tracks.
        """
        self.logger.info(f"Triggering scene {scene}.")
        for client in self.clients:
            if client.name in self.scenes[scene].keys():
                # client has tracks in the scene. send list to event queue with desired state of True
                self.trigger_event(client, self.scenes[scene][client.name], True)
                #turning off tracks not in the scene is handled in MidiClient.process_events()
            else:
                #client not in scene. turn all tracks off.
                self.trigger_event(client, None, False)
    
    def trigger_track(self, client: str, track):
        """
        special case of trigger_event() that triggers a single track.
        Places track events on the event queue.
        desired state is True (on), False (off), or None (for trigger mode)
        """
        self.logger.info(f"Triggering track {client} {track}.")
        for c in self.clients:
            if c.name == client:
                self.trigger_event(c, [track], None)

    def trigger_event(self, client: Client, tracklist: list, desired_state):
        if self.mode == Mode.TRIGGER:
            # trigger mode must be None
            desired_state = None

        self.logger.info(f"Sending event to client {client.name}, tracklist {tracklist}, state {desired_state}..")
        client.event_queue.put((tracklist, desired_state))
            
    def handle_signals(self):
        if not self.signal_queue.empty():
            while not self.signal_queue.empty():
                try:
                    (controller, signal) = self.signal_queue.get_nowait()
                except queue.Empty:
                    time.sleep(0.008)
                    continue
                self.logger.debug(f'Received signal {signal} from controller {controller}.')
                for c, s in self.mode_switch.items():
                    if c == controller and signal in s:
                        self.change_mode()
                        return
                try:
                    if self.mode == Mode.TRIGGER:
                        for client in self.controller_signal_trigger_map[controller][signal]:
                            for track in self.controller_signal_trigger_map[controller][signal][client]:
                                #todo: start in another process?
                                self.trigger_track(client, track)
                    elif self.mode == Mode.SCENE:
                        self.logger.debug(self.controller_signal_scene_map.__str__())
                        self.trigger_scene(self.controller_signal_scene_map[controller][signal])
                except KeyError as e:
                    self.logger.warn(f"Registered signal {signal} on controller {controller} not in {self.mode} map.")
                    self.logger.error(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
        else:
            raise exceptions.NothingToDo

    
    def register_controller_signal(self, ctlrlabel, signal_label=''):
        for c in self.controllers:
            if c.name == ctlrlabel:
                if signal_label == '':
                            label = f"signal{len(c.signal_map.values())}"
                else:
                    label = signal_label
                self.logger.debug(f'Registering signal "{signal_label}" to controller {ctlrlabel}.')
                c.command_queue.put({'register': signal_label})
        self.saved = False
    
    def change_mode(self):
        if self.mode == Mode.TRIGGER:
            new_mode = Mode.SCENE
        elif self.mode == Mode.SCENE:
            new_mode = Mode.TRIGGER
        self.mode = new_mode
        self.logger.info(f"Changed mode to {new_mode}")

    def print(self):
        pprint(self.__dict__())

    def process_commands(self):
        if not self.command_queue.empty():
            while True:
                try:
                    command = self.command_queue.get_nowait()
                    self.logger.debug(f'Received command {command}.')
                    for c in command.keys():
                        if c == 'assign_track':
                            controller, signal, client, track = command['assign_track']
                            self.assign_track(controller, signal, client, track)
                            continue
                        if c == 'add_client':
                            name, typ, toggle_record = command['add_client']
                            self.add_client(name, toggle_record=toggle_record, type=typ)
                            continue
                        if c == 'add_controller':
                            label, typ = command['add_controller']
                            self.add_controller(label, type=typ)
                            continue
                        if c == 'register_controller_signal':
                            label, signal_label  = command['register_controller_signal']
                            self.register_controller_signal(label, signal_label=signal_label)
                            continue
                        if c == 'client_add_track':
                            name, label, attrs = command['client_add_track']
                            self.client_add_track(name, label, attrs)
                            continue
                        if c == 'client_list_tracks':
                            client = command['client_list_tracks']
                            self.client_list_tracks(client)
                            continue
                        if c == 'register_modeswitch':
                            controller, label = command['register_modeswitch']
                            self.register_controller_signal(controller, signal_label=label)
                            self.assign_mode_switch(controller, label)
                            continue
                        if c == 'add_track_to_scene':
                            clientlabel, tracklabel, scenelabel = command['add_track_to_scene']
                            self.add_track_to_scene(clientlabel, tracklabel, scenelabel)
                            continue
                        if c == 'assign_scene':
                            controller, signal, scene = command['assign_scene']
                            self.assign_scene(controller, signal, scene)
                            continue
                        if c == 'save':
                            self.save()
                            continue
                        if c == 'create_scene_from_current':
                            scenelabel, = command['create_scene_from_current']
                            self.create_scene_from_current(scenelabel)
                        if c == 'get_scenes_stdout':
                            self.stdout_queue.put(self.scenes)
                        if c == 'get_trigger_map_stdout':
                            self.stdout_queue.put(self.controller_signal_trigger_map)
                        if c == 'get_scene_map_stdout':
                            self.stdout_queue.put(self.controller_signal_scene_map)
                        if c == 'track_toggle_record':
                            clientlabel, tracklabel = command[c]
                            self.track_toggle_record(clientlabel, tracklabel)

                        
                except queue.Empty:
                    break
        else:
            raise exceptions.NothingToDo

    def track_toggle_record(self, clientlabel, tracklabel):
        for client in self.clients:
            if client.name == clientlabel:
                client.command_queue.put({'toggle_record':(tracklabel,)})

        
    def update_status(self):
        try:
            self.status_queue.get_nowait()
        except queue.Empty:
            pass
        self.status_queue.put({
            'mode': self.mode,
            'filename': self.config,
            'saved': self.saved
        })

    def run(self):
        self.load_config()
        while not self.shutdown_callback.is_set():
            try:
                self.handle_signals()
                wait = False            
            except exceptions.NothingToDo:
                wait = True
                
            try:
                self.process_commands()
                wait = False            
            except exceptions.NothingToDo:
                wait = True
            if wait:
                self.update_status()
                time.sleep(0.008)
            # Shutdown Callback is set
        self.logger.warn("MidiPlexer stopped.")
            

    def shutdown(self):
        self.shutdown_callback.set()
        for c in self.controllers:
            c.join()
        for c in self.clients:
            c.join()
        self.logger.warn("Shutting Down.")
        
    def save(self, f=None):
        #todo
        config = f if f is not None else self.config
        with open(config, 'w') as f:
            conf = self.get_config_dict()
            json.dump(conf, f, indent=2)
            self.logger.warn(f"Saving to {config}")
            self.logger.debug(str(conf))

    def queue_config_dict(self):
        self.config_queue.put(self.get_config_dict())

    def get_config_dict(self):
       [client.command_queue.put({'queue_config_dict':()})for client in self.clients]
       [c.command_queue.put({'queue_config_dict':()}) for c in self.controllers]
       return {
            "clients": [client.config_queue.get() for client in self.clients],
            "controllers": [c.config_queue.get() for c in self.controllers],
            "scenes": self.scenes,
            "controller_signal_scene_map": self.controller_signal_scene_map,
            "controller_signal_trigger_map": self.controller_signal_trigger_map,
            "mode_switch": self.mode_switch,
        }
