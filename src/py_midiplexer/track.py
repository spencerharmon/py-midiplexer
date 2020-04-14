import logging
class Track(object):
    """
    Generic track superclass.
    """
    def __init__(self, label):
        self.label = label
        #always initiate to false?
        self.playing=False
        self.logger = logging.getLogger(f'{__class__.__name__}:{str(self.label)}')

    def trigger(self, port):
        pass

    def is_playing(self):
        return self.playing
    
    def __dict__(self):
        return {self.number: {"midi_data": self.midi_data, "midi_value": self.midi_value}}

import mido

class MidiTrack(Track):
    def __init__(self, label, attrs):
        super().__init__(label)
        # three types of data are accepted. 'data' can be thought of as a default.
        # on_ and off_ contain overrides for data when called in the on or off context determined in trigger.
        try:
            self.default_data = attrs['data']
        except KeyError:
            self.default_data = {}

        try:
            self.on_data = attrs['on_data']
        except KeyError:
            self.on_data = {}

        try:
            self.off_data = attrs['off_data']
        except KeyError:
            self.off_data = {}
        self.typ = attrs['type']
        self.reset_to_default_data()

    def get_msg(self) -> mido.Message:
        """
        parse the msg_dict and return a mido Message.
        validation is performed by the mido Message class.
        """

        try:
            channel = self.attr_dict['channel']
        except KeyError:
            channel = 0

        try:
            note = self.attr_dict['note']
        except KeyError:
            note = 0

        try:
            velocity = self.attr_dict['velocity']
        except KeyError:
            velocity = 64

        try:
            value = self.attr_dict['value']
        except KeyError:
            value = 0

        try:
            control = self.attr_dict['control']
        except KeyError:
            control = 0

        try:
            program = self.attr_dict['program']
        except KeyError:
            program = 0

        try:
            pitch = self.attr_dict['pitch']
        except KeyError:
            pitch = 0

        try:
            data = self.attr_dict['data']
        except KeyError:
            data = 0

        try:
            frame_type = self.attr_dict['frame_type']
        except KeyError:
            frame_type = 0

        try:
            frame_value = self.attr_dict['frame_value']
        except KeyError:
            frame_value = 0

        try:
            pos = self.attr_dict['pos']
        except KeyError:
            pos = 0

        try:
            song = self.attr_dict['song']
        except KeyError:
            song = 0
            
        if self.typ == "note_off":
            return mido.Message(self.typ, channel=channel, note=note, velocity=velocity)
        elif self.typ == "note_on":
            return mido.Message(self.typ, channel=channel, note=note, velocity=velocity)
        elif self.typ == "polytouch":
            return mido.Message(self.typ, channel=channel, note=note, value=value)
        elif self.typ == "control_change":
            return mido.Message(self.typ, channel=channel, control=control, value=value)
        elif self.typ == "program_change":
            return mido.Message(self.typ, channel=channel, program=program)
        elif self.typ == "aftertouch":
            return mido.Message(self.typ, channel=channel, value=value)
        elif self.typ == "pitchwheel":
            return mido.Message(self.typ, channel=channel, pitch=pitch)
        elif self.typ == "sysex":
            return mido.Message(self.typ, data=data)
        elif self.typ == "quarter_frame":
            return mido.Message(self.typ, frame_type=frame_type, frame_value=frame_value)
        elif self.typ == "songpos":
            return mido.Message(self.typ, pos=pos)
        elif self.typ == "song_select":
            return mido.Message(self.typ, song=song)
        elif self.typ == "tune_request":
            return mido.Message(self.typ)
        elif self.typ == "clock":
            return mido.Message(self.typ)
        elif self.typ == "start":
            return mido.Message(self.typ)
        elif self.typ == "continue":
            return mido.Message(self.typ)
        elif self.typ == "stop":
            return mido.Message(self.typ)
        elif self.typ == "reset":
            return mido.Message(self.typ)

    def update_msg_for_blank_signal(self, datadict):
        for k, v in datadict.items():
            self.logger.debug(f"changing data; {k}: {v}")
            self.attr_dict.update({k: v})
        msg = {"type":self.typ, "data":self.attr_dict}
        self.logger.debug(f"Updating message: {msg.__str__()}")
            
    def reset_to_default_data(self):
        self.attr_dict = {}
        self.update_msg_for_blank_signal(self.default_data)
        
    def update_msg_for_on_signal(self):
        self.update_msg_for_blank_signal(self.on_data)
        
    def update_msg_for_off_signal(self):
        self.update_msg_for_blank_signal(self.off_data)

    def trigger(self, port, desired_state):
        """
        trigger sends a signal on the given port in necessary to achieve the desired state. If on_data or off_data
        config items are used, they are applied durint this step.       
        """
        the_same = self.playing
        if desired_state is None:
            #trigger mode
            if self.playing:
                self.playing=False
                self.update_msg_for_off_signal()
            else:
                self.playing=True
                self.update_msg_for_on_signal()
            port.send(self.get_msg())
            
        elif desired_state:
            #desired playing
            if not self.playing:
                self.update_msg_for_on_signal()
                port.send(self.get_msg())
                self.playing = True
        else:
            # desired stopped
            if self.playing:
                self.update_msg_for_off_signal()
                port.send(self.get_msg())
                self.playing = False
                
        if self.playing is not the_same:
            m = {False: "not playing",
                 True: "playing"}
            self.logger.debug(f'State changed from {m[the_same]} to {m[self.playing]}.')

        #always reset to default, I guess..
        self.reset_to_default_data()

    def get_config_dict(self):
        return {"label": self.label, "type": self.typ, "data": self.attr_dict}
