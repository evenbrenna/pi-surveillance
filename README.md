Video streaming from raspberry pi zero w with motion detection and automatic dropbox uploads

Based on [this tutorial](http://www.pyimagesearch.com/2015/06/01/home-surveillance-and-motion-detection-with-the-raspberry-pi-python-and-opencv/)

## Hardware used
- Raspberry Pi Zero W with camera module

## Dependencies
- openCV (Instructions [here](http://www.pyimagesearch.com/2015/12/14/installing-opencv-on-your-raspberry-pi-zero/))
- dropbox module (`pip install dropbox`)
- picamera module (`pip install picamera`)
- imutils module (`pip install imutils`)

## Run
- Make a copy of `conf.json.template` and name it `conf.json`. Edit to taste.
- Run with `python pi-surveillance.py --conf conf.json`

## Troubleshooting
- This error: `failed to open vchiq instance`, was solved by adding my user on the pi to the video group: `usermod -a -G video <username>`
- I had an issue with ssh X11 forwarding which was solved by adding the line `ForwardX11Trusted yes` to my `~/.ssh/config` on my mac.
