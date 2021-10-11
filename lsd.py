#!/usr/bin/python3

# CONFIGURATION-SECTION
OUTPUT_DIR = ""  # set an output folder in case you want to set this folder as default
CLIENT_ID = "abcdefghijklmnpqrstuvwxyz"
CLIENT_SECRET = "ABCDEFGHIJKLMNPQRSTUVWXYZ"

# check for missing dependencies which are:
try:
    import subprocess
    import os
    import threading
    import time
    import shutil
    from urllib.request import urlretrieve
    import dbus

    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials as SpClCr
    from pydub import AudioSegment, silence
except ImportError as e:
    subprocess = os = threading = time = shutil = urlretrieve = dbus = spotipy = SpClCr = AudioSegment = silence = None
    exit("\033[91mMissing dependency: {}. Please check your installation!".format(e.name))

# colors used to make the terminal look nicer
GREEN, YELLOW, RED, CYAN, BOLD, RST = '\033[92m', '\033[93m', '\033[91m', '\033[96m', '\033[1m', '\033[0m'
INFO, WARNING, ERROR, REQUEST = f"[{GREEN}+{RST}]", f"[{YELLOW}~{RST}]", f"[{RED}-{RST}]", f"[{CYAN}?{RST}]"

# main-function
if __name__ == '__main__':
    # verify that the Pulseaudio and the parec-command is installed on this system
    if subprocess.Popen("parec --help && pacmd --help", stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, shell=True).wait() != 0:
        exit("{} This script needs a Linux system with Pulseaudio installed (e.g. KDE) to record tracks.".format(ERROR))

    # always check for ctrl+c
    try:
        sp = spotipy.Spotify(auth_manager=SpClCr(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))
        T_WIDTH = shutil.get_terminal_size().columns

        # welcome-message
        gap = "\n" + " " * (T_WIDTH // 2 - 12)
        print(gap + f"██{RED}╗{RST}      ███████{YELLOW}╗{RST} ██████{GREEN}╗{RST}" +
              gap + f"██{RED}║{RST}      ██{YELLOW}╔════╝{RST} ██{GREEN}╔══{RST}██{GREEN}╗{RST}" +
              gap + f"██{RED}║{RST}      ███████{YELLOW}╗{RST} ██{GREEN}║{RST}  ██{GREEN}║{RST}" +
              gap + f"██{RED}║{RST}      {YELLOW}╚════{RST}██{YELLOW}║{RST} ██{GREEN}║{RST}  ██{GREEN}║{RST}" +
              gap + f"███████{RED}╗{RST} ███████{YELLOW}║{RST} ██████{GREEN}╔╝{RST}" +
              gap + f"{RED}╚══════╝{RST} {YELLOW}╚══════╝{RST} {GREEN}╚═════╝{RST}" +
              "\n" + " " * (T_WIDTH // 2 - 14) + " Linux-Spotify-Downloader 2.0" +
              gap + " developed by Jannis Zahn")

        # specify the output-directory
        print("\n" + "---- CONFIGURATION " + "-" * (T_WIDTH - 19) + "\n")
        if not os.path.isdir(OUTPUT_DIR):
            while True:
                OUTPUT_DIR = input("{} Please specify an existing and writable output-directory: ".format(REQUEST))
                if os.path.isdir(OUTPUT_DIR): break
        OUTPUT_DIR = os.path.abspath(OUTPUT_DIR)
        print("{} Output-Directory: {}".format(INFO, OUTPUT_DIR))

        # initialize session-bus for Spotify and create the interface
        print("\n" + "---- DEPENDENCIES " + "-" * (T_WIDTH - 18) + "\n")
        session_bus = dbus.SessionBus()
        print("{} You need to open Spotify first ...".format(REQUEST), end="", flush=True)
        while True:
            try:
                bus = session_bus.get_object("org.mpris.MediaPlayer2.spotify", "/org/mpris/MediaPlayer2")
                methods_if = dbus.Interface(bus, "org.mpris.MediaPlayer2.Player")
                prop_if = dbus.Interface(bus, "org.freedesktop.DBus.Properties")
                break
            except dbus.exceptions.DBusException:
                time.sleep(0.2)
        print("\r{} OK, I have found a running Spotify-Application".format(INFO))

        # find spotify-input-sink and create monitor to record from
        print("{} I have to play a track to create a new recording interface ...".format(INFO), end="", flush=True)
        methods_if.Play()
        time.sleep(3)
        while True:
            sink_inputs = subprocess.run(["pacmd", "list-sink-inputs"], stdout=subprocess.PIPE).stdout.decode()
            if "application.name = \"Spotify\"" in sink_inputs: break
            time.sleep(1)
        methods_if.Pause()
        time.sleep(0.5)
        sink_index = sink_inputs.split("application.name = \"Spotify\"")[0].split("index: ")[-1].split("\n")[0]
        if subprocess.Popen(f"pactl load-module module-null-sink sink_name=lsd && pactl move-sink-input {sink_index} "
                            f"lsd", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True).wait() == 0:
            print("\r{} I have successfully created the recording interface to record from Spotify only.\n".format(INFO)
                  + "{}    I will now listen for tracks to be played ... Please close Spotify as soon as you finished "
                    "playing all songs!{}".format(BOLD, RST))
        else:
            exit("\r{} Error while creating the recording device for Spotify.".format(ERROR))

        # start the recording with parec (PulseAudio-Recording)
        print("\n" + "---- RECORDING " + "-" * (T_WIDTH - 15) + "\n")
        recording_process = subprocess.Popen(f"parec -d lsd.monitor --file-format=wav".split()
                                             + [OUTPUT_DIR + "/.temp.wav"])

        # initialize some variables
        last_url = ""
        counter = 0
        tracks = []
        ad = False

        # wait until first song starts (to make it possible to record also the current song)
        while prop_if.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus") != "Playing": time.sleep(0.01)

        # continue reading dbus-properties until Spotify gets closed
        try:
            while True:
                # get all meta-information about the current track
                meta = prop_if.Get("org.mpris.MediaPlayer2.Player", "Metadata")

                if last_url != meta["xesam:url"]:
                    last_url = meta["xesam:url"]
                    if meta["xesam:url"].startswith("https://open.spotify.com/track/"):
                        ad = False
                        counter += 1
                        tracks.append(meta["xesam:url"])
                        print("{} ({}) Recording: {} - {}{}{}"
                              .format(INFO, counter, meta["xesam:artist"][0], BOLD, meta["xesam:title"], RST))
                    elif not ad:
                        print("{} I have detected an advertisement, so I won't record this shit!".format(WARNING))
                        ad = True
                time.sleep(0.01)

        except dbus.exceptions.DBusException:  # means that Spotify is closed, because there is no bus any more
            recording_process.terminate()  # stop the recording
            subprocess.Popen(["pulseaudio", "-k"])  # restore original pulseaudio-configuration
            print("{} I have recorded {} track(s).".format(INFO, counter))

            if counter > 0:
                print("\n" + "---- CONVERTING & TAGGING " + "-" * (T_WIDTH - 26) + "\n")

                print("{} Converting the recorded wav-file to mp3 ...".format(INFO))
                AudioSegment.from_wav(OUTPUT_DIR + "/.temp.wav") \
                    .export(OUTPUT_DIR + "/.temp.mp3", format="mp3", bitrate="192k")

                # cut the recording, tag and export all tracks
                print("{} Splitting the recorded file on silence ...".format(INFO))
                recording = AudioSegment.from_mp3(OUTPUT_DIR + "/.temp.mp3")
                chunks = silence.split_on_silence(recording, silence_thresh=-60, min_silence_len=100, seek_step=10)

                skipped = 0
                for idx, audio in enumerate(chunks):
                    if audio.duration_seconds >= 40:
                        song = sp.track(tracks[idx - skipped])
                        print("\r{} Converting and tagging \"{}\" ...".format(INFO, song["name"])
                              + " " * (T_WIDTH - 33 - len(song["name"])), end="", flush=True)

                        # parse tags and download cover
                        tags = {
                            "title": song["name"].replace("-", "~").replace("/", "|"),
                            "artist": ", ".join(
                                song["artists"][x]["name"].replace("-", "~") for x in range(len(song["artists"]))),
                            "album_artist": ", ".join(song["album"]["artists"][x]["name"].replace("-", "~")
                                                      for x in range(len(song["album"]["artists"]))),
                            "album": song["album"]["name"],
                            "copyright": "Recorded with LinuxSpotifyDownloader from Spotify",
                            "track": song["track_number"],
                            "date": song["album"]["release_date"][0:4]
                        }
                        urlretrieve(song["album"]["images"][0]["url"], OUTPUT_DIR + "/.cover.jpg")  # download cover art

                        audio.export(OUTPUT_DIR + "/" + song["name"].replace("-", "~").replace("/", "|") + ".mp3",
                                     format="mp3", bitrate="192k", tags=tags, cover=OUTPUT_DIR + "/.cover.jpg")
                    else: skipped += 1
                os.remove(OUTPUT_DIR + "/.temp.wav")  # remove the old wav-file and mp3-file ...
                os.remove(OUTPUT_DIR + "/.temp.mp3")
                os.remove(OUTPUT_DIR + "/.cover.jpg")  # ...and the cover-file
                print("\r{}{} Done!".format(INFO, GREEN) + " " * (T_WIDTH - 9))

    except KeyboardInterrupt:
        subprocess.Popen(["pulseaudio", "-k"])
        exit("\n{}Detected Ctrl+C (Keyboard-Interrupt) ... Bye! :-)".format(RED))
