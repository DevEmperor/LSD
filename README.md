[![asciicast](https://asciinema.org/a/441333.svg)](https://asciinema.org/a/441333)



# LSD (Linux Spotify Downloader)

**LSD (Linux Spotify Downloader) is a command line tool for downloading or rather recording content on Spotify.**



## Dependencies

- Python 3.6 or higher
- any Linux distribution with PulseAudio as its sound server
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



## Usage

1. Run LSD with "*python3 lsd.py*"
2. Enter the path to your output directory. (If you always want to export to the same folder, you can also enter the path in the configuration section of "*lsd.py*".)
3. Open the Spotify Application and wait a few seconds until LSD has initialized the recording interface using PulseAudio
4. Now you can play a playlist, audiobook, podcast or individual tracks. Everything is recorded and then separated and tagged fully automatically.
   LSD only records the audio output from Spotify, but you should still make sure that you don't fast-forward tracks or record multiple times, otherwise the program won't work properly when exporting.
5. Close Spotify as soon as you are finished recording and LSD will do the rest for you.



## License

Fastr is under the terms of the [Apapche 2.0 license](https://www.apache.org/licenses/LICENSE-2.0), following all clarifications stated in the [license file](https://raw.githubusercontent.com/DevEmperor/LSD/master/LICENSE)
