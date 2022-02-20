[![asciicast](https://asciinema.org/a/469262.svg)](https://asciinema.org/a/469262)


# LSD (Linux Spotify Downloader)
![GitHub](https://img.shields.io/github/license/DevEmperor/LSD?style=for-the-badge)  ![GitHub release (latest by date)](https://img.shields.io/github/v/release/DevEmperor/LSD?style=for-the-badge) ![Downloads](https://img.shields.io/github/downloads/DevEmperor/LSD/total?style=for-the-badge)

**LSD (Linux Spotify Downloader) is a command line tool for downloading or rather recording content on Spotify.**



## Dependencies

- Python 3.6 or higher
- any Linux distribution with Pipewire & PulseAudio as its sound server
- git, ffmpeg and pip



## Installation and preparation

1. Clone this git-repository:

   ```bash
   git clone https://github.com/DevEmperor/lsd.git
   ```

2. install the dependencies (python libraries):

   ```bash
   pip3 install -r requirements.txt
   ```

3. visit [https://developer.spotify.com/dashboard/](https://developer.spotify.com/dashboard/) and create a new app, then copy the "Client ID" and "Client Secret" and add them into the configuration section of "*lsd.py*"

**Only if you want LSD to add lyrics to your tracks:**

4. visit [https://genius.com/api-clients/new](https://genius.com/api-clients/new) and create a new API client (enter only "App Name" and "App Website URL"; you can set "App Website URL" to the URL of this repository), then click on "Generate Access Token" and copy the token into the configuration section of "_lsd.py_"



## Usage

1. Run LSD with `python3 lsd.py`
2. Enter the path to your output directory. (If you always want to export to the same folder, you can also enter the path in the configuration section of "*lsd.py*")
3. Open the Spotify Application and wait a few seconds until LSD has initialized the recording interface using PulseAudio
4. Now you can play a playlist, audiobook, podcast or individual tracks. Everything is recorded and then separated and tagged fully automatically.
   LSD only records the audio output from Spotify, so you can safely go on with your usual work.
5. Close Spotify as soon as you are finished recording and LSD will do the rest for you.



## License

LSD is under the terms of the [Apapche 2.0 license](https://www.apache.org/licenses/LICENSE-2.0), following all clarifications stated in the [license file](https://raw.githubusercontent.com/DevEmperor/LSD/master/LICENSE)
