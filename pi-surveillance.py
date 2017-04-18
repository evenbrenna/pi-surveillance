from pyimagesearch.tempimage import TempImage
from dropbox.client import DropboxOAuth2FlowNoRedirect
from dropbox.client import DropboxClient
from picamera.array import PiRGBArray
from picamera import PiCamera

import argparse
import warnings
import datetime
import imutils
import json
import time
import cv2

# Argument parser
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required = True, help = "Path to config file")
args = vars(ap.parse_args())

# Filter warnings generated from urllib3 and dropbox packages
warnings.filterwarnings("ignore")

# Load config vars from config file
config = json.load(open(args["conf"]))

# Will store an initialized dropbox client if dropbox option is enabled
dropbox = None

# Authorize dropbox session
if config["use_dropbox"]:
	flow = DropboxOAuth2FlowNoRedirect(config["dropbox_key"], config["dropbox_secret"])
	print "[INFO] Authorize this application: {}".format(flow.start())
	authCode = raw_input("Enter auth code here: ").strip()
	(accessToken, userID) = flow.finish(authCode)
	client = DropboxClient(accessToken)
	print "[SUCCESS] dropbox account linked"

# Init camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = tuple(config["resolution"])
camera.framerate = config["fps"]
rawCapture = PiRGBArray(camera, size=tuple(config["resolution"]))

# Allow camera to warmup, then initialize the average frame, last
# uploaded timestamp, and frame motion counter
print "[INFO] warming up..."
time.sleep(config["camera_warmup_time"])
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0

# capture frames from the camera
for f in camera.capture_continuous(rawCapture, format = "bgr", use_video_port = True):
    # Grab the raw NumPy array representing the image and
    # initialize the timestamp and status text
    frame = f.array
    timestamp = datetime.datetime.now()
    motionDetected = False
    statusText = "Everything is quiet"

    # Resize the frame, convert it to grayscale, and blur it
    frame = imutils.resize(frame, width = 500)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    # If the average frame is None, initialize it
    if avg is None:
        print "[INFO] starting background model..."
        avg = gray.copy().astype("float")
        rawCapture.truncate(0)
        continue

    # Accumulate the weighted average between the current frame and
    # previous frames, then compute the difference between the current
    # frame and running average
    cv2.accumulateWeighted(gray, avg, 0.5)
    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

    # Threshold the delta image, dilate the thresholded image
    # to fill in holes, then find contours on thresholded image
    thresh = cv2.threshold(frameDelta, config["delta_thresh"], 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations = 2)
    (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Loop over the contours
    for c in cnts:
        # If the contour is large enough then compute the bounding
        # box for the contour, draw it on the frame, and update the text
        if cv2.contourArea(c) > config["min_area"]:
            (x, y, w, h) = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            statusText = "Motion detected!"
            motionDetected = True

    # Draw the text and timestamp on the frame
    ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
    cv2.putText(frame, "Status: {}".format(statusText), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

    # check to see if the room is occupied
    if motionDetected:
        # check to see if enough time has passed between uploads
        if (timestamp - lastUploaded).seconds >= config["min_upload_seconds"]:
            motionCounter += 1

            # Check if the number of frames with consistent motion is high enough
            if motionCounter >= config["min_motion_frames"]:
                if config["use_dropbox"]:
                    t = TempImage()
                    cv2.imwrite(t.path, frame)
                    print "[UPLOAD] {}".format(ts)
                    path = "{base_path}/{timestamp}.jpg".format(
                        base_path = conf["dropbox_base_path"], timestamp = ts)
                    dropbox.put_file(path, open(t.path, "rb"))
                    t.cleanup()

                # update the last uploaded timestamp and reset the motion counter
                lastUploaded = timestamp
                motionCounter = 0
    else:
        motionCounter = 0

    # Check if the frames should be displayed to screen
    if config["show_video"]:
        cv2.imshow("Security Feed", frame)
        key = cv2.waitKey(1) & 0xFF

        # If the `q` key is pressed, break from the lop
        if key == ord("q"):
            break

    # Clear the stream in preparation for the next frame
    rawCapture.truncate(0)
