import multiprocessing
from py_midiplexer.track import MidiTrack
from py_midiplexer import exceptions
import logging
import queue
import time

class Client(multiprocessing.Process):
    """
    A client represents one of the programs we're controlling. All clients have a name and a list of tracks.
    Name is a string.
    Each track is a Track object.
    """
    def __init__(self, shutdown_callback, stdout_queue, name: str, tracks: list):
        self.stdout_queue = stdout_queue
        self.shutdown_callback = shutdown_callback
        self.command_queue = multiprocessing.Queue()
        self.event_queue = multiprocessing.Queue()
        self.tracks = {}
        for t in tracks:
            create_track(t)
        super().__init__()
        self.name = name
        self.logger = logging.getLogger(f'{self.__class__.__name__}:{self.name}')

    def create_track(self, label, data):
        """
        append a track to the self.tracks member
        """
        pass

    def shutdown(self):
        try:
            self.port.close()
        except:
            pass
        self.event_queue.close()
        self.logger.info(f"Exiting.")
        
    def __dict__(self):
        return {"name": self.name, "tracks": {label: track.__dict__() for label, track in self.tracks.items()}}

class MidiClient(Client):
    """
    MidiClient defines an interface for jack midi clients.
    """
    def __init__(self, shutdown_callback, stdout_queue, name, tracks=[], backend='mido.backends.rtmidi/UNIX_JACK'):
        super().__init__(shutdown_callback, stdout_queue, name, tracks)
        self.backend = backend



    def create_track(self, label, attrs):
        self.logger.debug(f"Creating track {label}: {attrs}")
        self.tracks.update({label: MidiTrack(label, attrs)})
    
    def trigger_track(self, label, scenemode):
        # maybe this is deprecated
        self.tracks[track].trigger(self.port, scenemode)
        for l, track in self.tracks.items():
            if l == label:
                print(track.__dict__())

    def list_tracks(self):
        self.stdout_queue.put(self.__dict__()["tracks"])
                
    def process_events(self):
        while True:
            try:
                (tracklist, desired_state) = self.event_queue.get_nowait()
                # list of track instances for event. Queued tracklist of None is equivalent to "all"
                desired_state = False if tracklist is None else desired_state
                try:
                  tracklist = self.tracks if tracklist is None else [self.tracks[track] for track in tracklist]
                except KeyError as e:
                    track_label, = e.args
                    raise exceptions.NoSuchTrack(self.name, track_label)

                self.logger.debug('Received event. Track '
                                  f'{tracklist} desired state is '
                                  f'{"on" if desired_state else "off"}'
                                  f'{None if desired_state is None else ""}')
                if desired_state is None:
                    # trigger mode
                    [track.trigger(self.port, desired_state) for track in tracklist]
                else:
                    # trigger the tracks that are not playing whose desired state is on/playing.
                    # careful. desired_state=False implies all tracks not in the list should be on.
                    [track.trigger(self.port, desired_state) for track in tracklist]
                    # opposite case. turn off the tracks that shouldn't be on.
                    [track.trigger(self.port, not desired_state)
                     for track in self.tracks if not track in tracklist]
                    
                continue
                #don't do this stuff. let track.trigger() handle desired_state
                if desired_state is None:
                    # trigger mode
                    [track.trigger(self.port, desired_state) for track in tracklist]
                elif desired_state:
                    # trigger the tracks that are not playing whose desired state is on/playing.
                    [track.trigger(self.port, desired_state) for track in tracklist if track.playing is False]
                    # opposite case. turn off the tracks that shouldn't be on.
                    [track.trigger(self.port, desired_state)
                     for track in self.tracks
                     if not track in tracklist and track.playing is True]
                else:
                    # trigger tracks that are playing whose desired state is off.
                    [track.trigger(self.port, desired_state) for track in tracklist if track.playing is True]
                    

            except queue.Empty:
                break

    def process_commands(self):
        while True:
            try:
                command = self.command_queue.get_nowait()
                for c in command.keys():
                    if c == 'create_track':
                        label, attrs = command['create_track']
                        self.create_track(label, attrs)
                    if c == 'list_tracks':
                        self.list_tracks()
            except queue.Empty:
                break

        
    def run(self):
        #late import mido.
        import mido
        mido.set_backend(self.backend)
        
        self.port = mido.open_output(self.name, client_name="py_midiplexer")
        self.logger.debug(f"Starting.")
        while not self.shutdown_callback.is_set():
            self.process_commands()
            try:
                self.process_events()
            except exceptions.NoSuchTrack as e:
                self.logger.error(f"Track not found: {e.track_label}.")
                

        self.shutdown()
