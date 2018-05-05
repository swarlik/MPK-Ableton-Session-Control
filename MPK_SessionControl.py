#-----------------------------------------------
#
#  Author: Sanchit Malhotra, adapted from
#          Sarah Howe  sarah@keithmcmillen.com
#
#-----------------------------------------------

from __future__ import with_statement

import Live
import time

from _Framework.ButtonElement import ButtonElement
from _Framework.SliderElement import SliderElement
from _Framework.ChannelStripComponent import ChannelStripComponent
from _Framework.ClipSlotComponent import ClipSlotComponent
from _Framework.CompoundComponent import CompoundComponent
from _Framework.ControlElement import ControlElement
from _Framework.ControlSurface import ControlSurface
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.InputControlElement import *
from _Framework.MixerComponent import MixerComponent
from _Framework.SceneComponent import SceneComponent
from _Framework.SessionComponent import SessionComponent
from _Framework.SessionZoomingComponent import SessionZoomingComponent
from _Framework.EncoderElement import EncoderElement
from _Framework.ToggleComponent import ToggleComponent
from _Framework.TransportComponent import TransportComponent

#define global variables
CHANNEL = 0  #channels are numbered 0 - 15
is_momentary = True
NUM_TRACKS = 3

# Bank B MIDI Note Assignemnts - used for track/scene control
BANK_B = [1, 2, 3, 4, 5, 6, 7, 8]
# Keyboard starting value (C4):
KEYBOARD_LOW_C = 60
# Keyboard middle C value (C5):
KEYBOARD_MID_C = 72
# Keyboard ending value (C6):
KEYBOARD_HIGH_C = 84
# Knob MIDI CC assignments
KNOBS = [85, 86, 87, 88, 89, 90, 102, 103]

class MPK_SessionControl(ControlSurface):
  __module__ = __name__
  __doc__ = "MPK Session Control Script"

  def __init__(self, c_instance):
    ControlSurface.__init__(self, c_instance)
    with self.component_guard():
      self._setup_mixer_control()
      self._setup_transport_control()
      self._setup_session_control()
      self._setup_channel_strip_control()
      self.set_highlighting_session_component(self.session)

  # Sets up the control surface ('colored box')
  def _setup_session_control(self):
    num_tracks = 3 # 3 columns (tracks)
    num_scenes = 1 # 1 row (scenes)

    # a session highlight ("red box") will appear with any two non-zero values
    self.session = SessionComponent(num_tracks, num_scenes)
    # (track_offset, scene_offset) Sets the initial offset of the "red box" from top left
    self.session.set_offsets(0,0)

    self.session.set_select_buttons(ButtonElement(is_momentary, MIDI_NOTE_TYPE, CHANNEL, KEYBOARD_HIGH_C - 7), ButtonElement(is_momentary, MIDI_NOTE_TYPE, CHANNEL, KEYBOARD_HIGH_C - 6))

    # These calls control the actual movement of the box; however, we're just
    # using scene and track select to move around
    # self.session.set_scene_bank_buttons(ButtonElement(is_momentary, MIDI_CC_TYPE, CHANNEL, 86), ButtonElement(is_momentary, MIDI_CC_TYPE, CHANNEL, 85))
    # self.session.set_track_bank_buttons(ButtonElement(is_momentary, MIDI_CC_TYPE, CHANNEL, 15), ButtonElement(is_momentary, MIDI_CC_TYPE, CHANNEL, 14))

    # Launch current scene with top right pad
    self.session.selected_scene().set_launch_button(ButtonElement(is_momentary, MIDI_NOTE_TYPE, CHANNEL, BANK_B[3]))
    # Stop all clips with bottom right pad
    self.session.set_stop_all_clips_button(ButtonElement(is_momentary, MIDI_NOTE_TYPE, CHANNEL, BANK_B[7]))

    # First three pads launch clips in box
    clip_launch_notes = [BANK_B[0], BANK_B[1],  BANK_B[2]]
    clip_select_notes = [KEYBOARD_MID_C - 6, KEYBOARD_MID_C - 4, KEYBOARD_MID_C - 2]

    for tracks in range(num_tracks):
      self.session.scene(0).clip_slot(tracks).set_launch_button(ButtonElement(is_momentary, MIDI_NOTE_TYPE, CHANNEL, clip_launch_notes[tracks]))
      self.session.scene(0).clip_slot(tracks).set_select_button(ButtonElement(is_momentary, MIDI_NOTE_TYPE, CHANNEL, clip_select_notes[tracks]))
      self.session.scene(0).clip_slot(tracks).set_started_value(1)
      self.session.scene(0).clip_slot(tracks).set_stopped_value(0)

    # Bottom three pads stop current tracks in box
    track_stop_notes = [BANK_B[4], BANK_B[5], BANK_B[6]]
    # This looks unnecessary but I don't know the actual API call to to set the stop track button for the selected track
    stop_track_buttons = []
    for tracks in range(num_tracks):
      stop_track_buttons.append(ButtonElement(is_momentary, MIDI_NOTE_TYPE, CHANNEL, track_stop_notes[tracks]))

    self.session.set_stop_track_clip_buttons(tuple(stop_track_buttons))

    #here we set up a mixer and channel strip(s) which move with the session
    self.session.set_mixer(self.mixer)  #bind the mixer to the session so that they move together
    selected_scene = self.song().view.selected_scene #this is from the Live API
    all_scenes = self.song().scenes
    index = list(all_scenes).index(selected_scene)
    self.session.set_offsets(0, index) #(track_offset, scene_offset)

  def _setup_transport_control(self):
    self.transport = TransportComponent()
    self.transport.set_stop_button(ButtonElement(is_momentary, MIDI_NOTE_TYPE, CHANNEL, KEYBOARD_LOW_C))
    self.transport.set_play_button(ButtonElement(is_momentary, MIDI_CC_TYPE, CHANNEL, 113))
    self.transport.set_metronome_button(ButtonElement(is_momentary, MIDI_CC_TYPE, CHANNEL, 114))
    self.transport.set_tap_tempo_button(ButtonElement(is_momentary, MIDI_CC_TYPE, CHANNEL, 81))

  def _setup_mixer_control(self):
    #set up the mixer
    self.mixer = MixerComponent(NUM_TRACKS, 2)  #(num_tracks, num_returns, with_eqs, with_filters)
    self.mixer.set_track_offset(0)  #sets start point for mixer strip (offset from left)
    self.mixer.selected_strip().set_arm_button(ButtonElement(is_momentary, MIDI_NOTE_TYPE, CHANNEL, KEYBOARD_HIGH_C))
    self.mixer.set_select_buttons(ButtonElement(is_momentary, MIDI_NOTE_TYPE, CHANNEL, KEYBOARD_HIGH_C - 2), ButtonElement(is_momentary, MIDI_NOTE_TYPE, CHANNEL, KEYBOARD_HIGH_C - 4))
    self.mixer.master_strip().set_volume_control(SliderElement(MIDI_CC_TYPE, CHANNEL, KNOBS[3]))
    #self.mixer.master_strip().set_pan_control(SliderElement(MIDI_CC_TYPE, CHANNEL, KNOBS[7]))
    #set the selected strip to the first track, so that we don't assign a button to arm the master track, which would cause an assertion error
    self.song().view.selected_track = self.mixer.channel_strip(0)._track
    self.mixer.selected_strip().set_volume_control(SliderElement(MIDI_CC_TYPE, CHANNEL, KNOBS[0]))
    #self.mixer.selected_strip().set_pan_control(SliderElement(MIDI_CC_TYPE, CHANNEL, KNOBS[4]))

    selected_track = self.song().view.selected_track
    all_tracks = ((self.song().tracks + self.song().return_tracks) + (self.song().master_track,))
    currentTrackIndex = list(all_tracks).index(selected_track)
    if currentTrackIndex < len(all_tracks) - 1:
        self.mixer.channel_strip(currentTrackIndex + 1).set_volume_control(SliderElement(MIDI_CC_TYPE, CHANNEL, KNOBS[1]))
        #self.mixer.channel_strip(currentTrackIndex + 1).set_pan_control(SliderElement(MIDI_CC_TYPE, CHANNEL, KNOBS[5]))
    if currentTrackIndex < len(all_tracks) - 2:
        self.mixer.channel_strip(currentTrackIndex + 2).set_volume_control(SliderElement(MIDI_CC_TYPE, CHANNEL, KNOBS[2]))
        #self.mixer.channel_strip(currentTrackIndex + 2).set_pan_control(SliderElement(MIDI_CC_TYPE, CHANNEL, KNOBS[6]))



  def _setup_channel_strip_control(self):
  	self.channelstrip = ChannelStripComponent()
  	self.channelstrip.set_track(self.mixer.channel_strip(0)._track)

  def _on_selected_track_changed(self):
    """This is an override, to add special functionality (we want to move the session to the selected track, when it changes)
    Note that it is sometimes necessary to reload Live (not just the script) when making changes to this function"""
    ControlSurface._on_selected_track_changed(self) # This will run component.on_selected_track_changed() for all components
    """here we set the mixer and session to the selected track, when the selected track changes"""
    selected_track = self.song().view.selected_track #this is how to get the currently selected track, using the Live API
    self.mixer.channel_strip(0).set_track(selected_track)
    all_tracks = ((self.song().tracks + self.song().return_tracks) + (self.song().master_track,))  #this is from the MixerComponent's _next_track_value method
    index = list(all_tracks).index(selected_track) #and so is this

    self.session.set_offsets(index, self.session._scene_offset) #(track_offset, scene_offset); we leave scene_offset unchanged, but set track_offset to the selected track. This allows us to jump the red box to the selected track.

  def _on_selected_scene_changed(self):
    """This is an override, to add special functionality (we want to move the session to the selected scene, when it changes)"""
    """When making changes to this function on the fly, it is sometimes necessary to reload Live (not just the script)..."""
    ControlSurface._on_selected_scene_changed(self) # This will run component.on_selected_scene_changed() for all components
    """Here we set the mixer and session to the selected track, when the selected track changes"""
    selected_scene = self.song().view.selected_scene #this is how we get the currently selected scene, using the Live API
    all_scenes = self.song().scenes #then get all of the scenes
    index = list(all_scenes).index(selected_scene) #then identify where the selected scene sits in relation to the full list
    self.session.set_offsets(self.session._track_offset, index) #(track_offset, scene_offset) Set the session's scene offset to match the selected track (but make no change to the track offset)

  def disconnect(self):
    #clean things up on disconnect

    #create entry in log file
    self.log_message(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()) + "----------MPK SessionControl log closed----------")

    ControlSurface.disconnect(self)
    return None
