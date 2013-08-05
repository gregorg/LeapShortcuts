#!/usr/bin/python -O

import Leap, sys, time
from Leap import CircleGesture, KeyTapGesture, ScreenTapGesture, SwipeGesture

import logging
import os
import re
import threading
import subprocess


class DesktopListener(Leap.Listener):
	SWIPE_DETECT = 0.00
	SWIPE_TOLERANCE = 0.20

	def on_init(self, controller):
		self.lastX = -1
		self.lastY = -1
		self.sensitivity = 5
		self.thumbVanishTime = 0
		self.lastFingerCount = 0
		self.lastClickTime = 0
		self.fingerId = 0
		self.thumbId = 0
		self.seenIds = []
		self.mouseDown = False
		logging.info("Initialized")

	def on_connect(self, controller):
		logging.info("Connected")
		# Enable gestures
		controller.enable_gesture(Leap.Gesture.TYPE_CIRCLE);
		controller.enable_gesture(Leap.Gesture.TYPE_KEY_TAP);
		controller.enable_gesture(Leap.Gesture.TYPE_SCREEN_TAP);
		controller.enable_gesture(Leap.Gesture.TYPE_SWIPE);
	
	def on_disconnect(self, controller):
		# Note: not dispatched when running in a debugger.
		logging.info("Disconnected")
	
	def on_exit(self, controller):
		logging.info("Exited")
	
	def on_frame(self, controller):
		# Get the most recent frame and report some basic information
		frame = controller.frame()

		if not frame.hands.empty:
			if len(frame.hands) == 2:
				print "Frame id: %d, timestamp: %d, hands: %d, fingers: %d, tools: %d, gestures: %d" % (
					  frame.id, frame.timestamp, len(frame.hands), len(frame.fingers), len(frame.tools), len(frame.gestures()))

			# Get the first hand
			hand = frame.hands[0]

			# Check if the hand has any fingers
			fingers = hand.fingers
			if not fingers.empty:
				# Calculate the hand's average finger tip position
				avg_pos = Leap.Vector()
				for finger in fingers:
					avg_pos += finger.tip_position
				avg_pos /= len(fingers)
				logging.debug("Hand has %d fingers, average finger tip position: %s" % (
					  len(fingers), avg_pos))

			# Get the hand's sphere radius and palm position
			#print "Hand sphere radius: %f mm, palm position: %s" % (
			#	  hand.sphere_radius, hand.palm_position)

			# Get the hand's normal vector and direction
			normal = hand.palm_normal
			direction = hand.direction

			# Calculate the hand's pitch, roll, and yaw angles
			#print "Hand pitch: %f degrees, roll: %f degrees, yaw: %f degrees" % (
			#	direction.pitch * Leap.RAD_TO_DEG,
			#	normal.roll * Leap.RAD_TO_DEG,
			#	direction.yaw * Leap.RAD_TO_DEG)

			# Gestures
			for gesture in frame.gestures():
				if gesture.type == Leap.Gesture.TYPE_CIRCLE:
					circle = CircleGesture(gesture)

					# Determine clock direction using the angle between the pointable and the circle normal
					if circle.pointable.direction.angle_to(circle.normal) <= Leap.PI/4:
						clockwiseness = "clockwise"
					else:
						clockwiseness = "counterclockwise"

					# Calculate the angle swept since the last frame
					swept_angle = 0
					if circle.state != Leap.Gesture.STATE_START:
						previous_update = CircleGesture(controller.frame(1).gesture(circle.id))
						swept_angle =  (circle.progress - previous_update.progress) * 2 * Leap.PI

					logging.debug("Circle id: %d, %s, progress: %f, radius: %f, angle: %f degrees, %s" % (
							gesture.id, self.state_string(gesture.state),
							circle.progress, circle.radius, swept_angle * Leap.RAD_TO_DEG, clockwiseness))

				if gesture.type == Leap.Gesture.TYPE_SWIPE:
					swipe = SwipeGesture(gesture)
					logging.debug("Swipe id: %d, state: %s, position: %s, direction: %s, speed: %f" % (
							gesture.id, self.state_string(gesture.state),
							swipe.position, swipe.direction, swipe.speed))
					if swipe.direction.x < self.SWIPE_DETECT and abs(swipe.direction.y) < self.SWIPE_TOLERANCE:
						subprocess.call(['xte', 'keydown Control_L', 'keydown Alt_L', 'key Left', 'keyup Alt_L', 'keyup Control_L'])
					elif swipe.direction.x > self.SWIPE_DETECT and abs(swipe.direction.y) < self.SWIPE_TOLERANCE:
						subprocess.call(['xte', 'keydown Control_L', 'keydown Alt_L', 'key Right', 'keyup Alt_L', 'keyup Control_L'])

				if gesture.type == Leap.Gesture.TYPE_KEY_TAP:
					keytap = KeyTapGesture(gesture)
					logging.debug("Key Tap id: %d, %s, position: %s, direction: %s" % (
							gesture.id, self.state_string(gesture.state),
							keytap.position, keytap.direction ))

				if gesture.type == Leap.Gesture.TYPE_SCREEN_TAP:
					screentap = ScreenTapGesture(gesture)
					logging.debug("Screen Tap id: %d, %s, position: %s, direction: %s" % (
							gesture.id, self.state_string(gesture.state),
							screentap.position, screentap.direction ))
					subprocess.call(['gnome-screensaver-command', '--lock'])

		
	def state_string(self, state):
		if state == Leap.Gesture.STATE_START:
			return "STATE_START"
		
		if state == Leap.Gesture.STATE_UPDATE:
			return "STATE_UPDATE"
		
		if state == Leap.Gesture.STATE_STOP:
			return "STATE_STOP"
		
		if state == Leap.Gesture.STATE_INVALID:
			return "STATE_INVALID"


def setup_logging(debug_level=None, threadless=False, logfile=None, rotate=False): # {{{
	# if threadless mode, it's a workarround for new Process
	if threadless or rotate:
		try:
			logfile = logging.root.handlers[0].baseFilename

			if rotate:
				try:
					logging.root.handlers[0].close()
					# rotate handled by logrotate
				except:
					logging.warning("Unable to close file:", exc_info=True)
		except AttributeError: logfile=None
	
		# removing them with technic to not need lock :
		# see line 1198 from /usr/lib/python2.6/logging/__init__.py
		while len(logging.root.handlers) > 0:
			logging.root.handlers.remove(logging.root.handlers[0])
		
		if debug_level is None:
			debug_level = logging.root.getEffectiveLevel()
	else:
		# ensure closed
		logging.shutdown()
		if debug_level is None:
			debug_level = logging.DEBUG
			
	if logfile: 
		loghandler = logging.handlers.WatchedFileHandler(logfile)
	else:		   
		loghandler = logging.StreamHandler()
					
	loghandler.setLevel(debug_level)
	#loghandler.setFormatter(logging.Formatter(logformat, logdatefmt))
	use_color = False
	if os.environ.has_key("TERM") and ( re.search("term", os.environ["TERM"]) or os.environ["TERM"] in ('screen',) ):
		use_color = True
	loghandler.setFormatter(ColoredFormatter(use_color))
			
	while len(logging.root.handlers) > 0:
		logging.root.removeHandler(logging.root.handlers[0])

	logging.root.addHandler(loghandler)
	logging.root.setLevel(debug_level)

# }}}

class ColoredFormatter(logging.Formatter): # {{{
	COLORS = {
		'WARNING': 'yellow',
		'INFO': 'cyan',
		'CRITICAL': 'white',
		'ERROR': 'red'
	}
	COLORS_ATTRS = {
		'CRITICAL': 'on_red',
	}

	def __init__(self, use_color = True):
		# main formatter:
		logformat = '%(asctime)s %(threadName)14s.%(funcName)-15s %(levelname)-8s %(message)s'
		logdatefmt = '%H:%M:%S %d/%m/%Y'
		logging.Formatter.__init__(self, logformat, logdatefmt)

		# for thread-less scripts :
		logformat = '%(asctime)s %(module)14s.%(funcName)-15s %(levelname)-8s %(message)s'
		self.mainthread_formatter = logging.Formatter(logformat, logdatefmt)

		self.use_color = use_color
		if self.use_color and not 'termcolor' in sys.modules:
			logging.debug("You could activate colors with 'termcolor' module")
			self.use_color = False

	def format(self, record):
		if self.use_color and record.levelname in self.COLORS:
			if record.levelname in self.COLORS_ATTRS:
				record.msg = termcolor.colored(record.msg, self.COLORS[record.levelname], self.COLORS_ATTRS[record.levelname])
			else:
				record.msg = termcolor.colored(record.msg, self.COLORS[record.levelname])
		if threading.currentThread().getName() == 'MainThread':
			return self.mainthread_formatter.format(record)
		else:
			return logging.Formatter.format(self, record)

# }}}



def main():
	# Logging
	setup_logging(logging.DEBUG)

	# Create a sample listener and controller
	listener = DesktopListener()
	controller = Leap.Controller()
	
	# Have the sample listener receive events from the controller
	controller.add_listener(listener)
	
	# Keep this process running until CTRL+C is pressed
	logging.info("Ready!")
	try:
		while (True):
			time.sleep(0.1)
	except KeyboardInterrupt: pass
	
	# Remove the sample listener when done
	controller.remove_listener(listener)


if __name__ == "__main__":
	main()

