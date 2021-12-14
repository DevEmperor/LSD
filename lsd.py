#!/usr/bin/python3

# CONFIGURATION-SECTION
OUTPUT_DIR = ""  # set an output folder in case you want to set this folder as default
SPOTIFY_CLIENT_ID = "SPOTIFY_CLIENT_ID"
SPOTIFY_CLIENT_SECRET = "SPOTIFY_CLIENT_SECRET"
GENIUS_ACCESS_TOKEN = "GENIUS_ACCESS_TOKEN"

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
    from spotipy.oauth2 import SpotifyClientCredentials
    from pydub import AudioSegment, silence
    import lyricsgenius
    import eyed3

    # verify that the Pulseaudio and the parec-command is installed on this system
    if subprocess.Popen("parec --help && pw-cli --help", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True).wait() != 0:
        raise ImportError(name="Pipewire & PulseAudio")
except ImportError as e:
    exit("\033[91mMissing dependency: {}. Please check your installation!".format(e.name))

# colors used to make the terminal look nicer
GREEN, YELLOW, RED, CYAN, BOLD, RST = '\033[92m', '\033[93m', '\033[91m', '\033[96m', '\033[1m', '\033[0m'
INFO, WARNING, ERROR, REQUEST = f"[{GREEN}+{RST}]", f"[{YELLOW}~{RST}]", f"[{RED}-{RST}]", f"[{CYAN}?{RST}]"

# main-function
if __name__ == '__main__':
    # always check for ctrl+c
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))
        T_WIDTH = shutil.get_terminal_size().columns

        # welcome-message
        gap = "\n" + " " * (T_WIDTH // 2 - 12)
        print(gap + f"██{RED}╗{RST}      ███████{YELLOW}╗{RST} ██████{GREEN}╗{RST}" +
              gap + f"██{RED}║{RST}      ██{YELLOW}╔════╝{RST} ██{GREEN}╔══{RST}██{GREEN}╗{RST}" +
              gap + f"██{RED}║{RST}      ███████{YELLOW}╗{RST} ██{GREEN}║{RST}  ██{GREEN}║{RST}" +
              gap + f"██{RED}║{RST}      {YELLOW}╚════{RST}██{YELLOW}║{RST} ██{GREEN}║{RST}  ██{GREEN}║{RST}" +
              gap + f"███████{RED}╗{RST} ███████{YELLOW}║{RST} ██████{GREEN}╔╝{RST}" +
              gap + f"{RED}╚══════╝{RST} {YELLOW}╚══════╝{RST} {GREEN}╚═════╝{RST}" +
              "\n" + " " * (T_WIDTH // 2 - 14) + " Linux-Spotify-Downloader 2.3" +
              gap + " developed by Jannis Zahn")

        # specify the output-directory
        print("\n" + "---- CONFIGURATION " + "-" * (T_WIDTH - 19) + "\n")
        if not os.path.isdir(OUTPUT_DIR):
            while True:
                OUTPUT_DIR = input("{} Please specify an existing and writable output-directory: ".format(REQUEST))
                if os.path.isdir(OUTPUT_DIR):
                    break
        OUTPUT_DIR = os.path.abspath(OUTPUT_DIR)
        print("{} Output-Directory: {}".format(INFO, OUTPUT_DIR))

        # initialize session-bus for Spotify and create the interface
        print("\n" + "---- DEPENDENCIES " + "-" * (T_WIDTH - 18) + "\n")
        session_bus = dbus.SessionBus()
        print("{} You need to open Spotify first ...".format(REQUEST))
        while True:
            try:
                bus = session_bus.get_object("org.mpris.MediaPlayer2.spotify", "/org/mpris/MediaPlayer2")
                methods_if = dbus.Interface(bus, "org.mpris.MediaPlayer2.Player")
                prop_if = dbus.Interface(bus, "org.freedesktop.DBus.Properties")
                break
            except dbus.exceptions.DBusException:
                time.sleep(0.2)
        print("{} OK, I have found a running Spotify-Application".format(INFO))
        time.sleep(1)

        # find spotify-input-sink and create monitor to record from
        print("{} I have to play a track to create a new recording interface ...".format(INFO))
        methods_if.Play()
        time.sleep(2)
        sink_inputs = subprocess.run("pw-cli ls Node".split(), stdout=subprocess.PIPE).stdout.decode()
        methods_if.Pause()
        time.sleep(2)
        sink_index_spotify = sink_inputs.split("application.name = \"spotify\"")[0].split("\tid ")[-1].split(",")[0]
        if subprocess.Popen("pactl load-module module-null-sink sink_name=lsd && pactl move-sink-input {} lsd".format(sink_index_spotify),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True).wait() == 0:
            print("{}{} I will now listen for tracks to be played ... "
                  "Please close Spotify as soon as you finished playing all songs!{}".format(INFO, BOLD, RST))
        else:
            exit("{} Error while creating the recording device for Spotify.".format(ERROR))

        sink_inputs = subprocess.run("pw-cli ls Node".split(), stdout=subprocess.PIPE).stdout.decode()
        sink_index_lsd = sink_inputs.split("node.name = \"lsd\"")[0].split("\tid ")[-1].split(",")[0]

        # start the recording with parec (PulseAudio-Recording)
        print("\n" + "---- RECORDING " + "-" * (T_WIDTH - 15) + "\n")

        recording_process = subprocess.Popen("parec --monitor-stream {} --file-format=wav".format(sink_index_lsd).split() + [OUTPUT_DIR + "/.temp.wav"])

        # initialize some variables
        counter = 0
        tracks = [""]
        timestamps = []
        t_start = time.time()
        ad = False

        # continue reading dbus-properties until Spotify gets closed
        try:
            # wait until first song starts (to make it possible to record also the current song)
            while prop_if.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus") != "Playing":
                time.sleep(0.01)

            while True:
                # get all meta-information about the current track
                meta = prop_if.Get("org.mpris.MediaPlayer2.Player", "Metadata")

                if tracks[-1] != meta["xesam:url"]:
                    tracks.append(meta["xesam:url"])
                    timestamps.append(time.time())
                    if tracks[-1].startswith("https://open.spotify.com/track/"):
                        ad = False
                        counter += 1
                        print("{} ({}) Recording: {} - {}{}{}".format(INFO, counter, meta["xesam:artist"][0], BOLD, meta["xesam:title"], RST))
                    elif not ad:
                        print("{} I have detected an advertisement, so I won't record this shit!".format(WARNING))
                        ad = True
                time.sleep(0.01)

        except dbus.exceptions.DBusException:  # means that Spotify is closed, because there is no bus any more
            timestamps.append(time.time())  # necessary to slice the last track
            recording_process.terminate()  # stop the recording
            subprocess.Popen("systemctl --user restart pipewire pipewire-pulse".split())  # restore original pulseaudio-configuration
            tracks = tracks[1:]  # remove the first empty element since it is only used once for comparing above
            print("\n{} I have recorded {} track(s).".format(INFO, counter))

            if counter > 0:
                print("\n" + "---- CONVERTING & TAGGING " + "-" * (T_WIDTH - 26) + "\n")

                print("{} Converting the recorded wav-file to mp3 ...".format(INFO))
                AudioSegment.from_wav(OUTPUT_DIR + "/.temp.wav").export(OUTPUT_DIR + "/.temp.mp3", format="mp3", bitrate="192k")
                recording = AudioSegment.from_mp3(OUTPUT_DIR + "/.temp.mp3")

                print("{} Splitting the recorded file on silence ...".format(INFO))
                chunks = silence.detect_nonsilent(recording, min_silence_len=400, silence_thresh=-65, seek_step=10)
                chunks_starts = [c[0] for c in chunks]
                chunks_ends = [c[1] for c in chunks]

                # initialize access to Genius-API
                genius = None
                if GENIUS_ACCESS_TOKEN != "":
                    genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN)
                    genius.verbose = False

                for idx in range(len(timestamps) - 1):
                    if tracks[idx].startswith("https://open.spotify.com/track/"):  # check for ad
                        song = sp.track(tracks[idx])
                        print("{} Converting and tagging \"{}\" ...".format(INFO, song["name"]))

                        # parse tags and download cover
                        tags = {
                            "title": song["name"].replace("-", "~").replace("/", "|"),
                            "artist": ", ".join(song["artists"][x]["name"].replace("-", "~") for x in range(len(song["artists"]))),
                            "album_artist": ", ".join(song["album"]["artists"][x]["name"].replace("-", "~") for x in range(len(song["album"]["artists"]))),
                            "album": song["album"]["name"],
                            "copyright": "Recorded with LinuxSpotifyDownloader from Spotify",
                            "track": song["track_number"],
                            "date": song["album"]["release_date"][0:4]
                        }
                        urlretrieve(song["album"]["images"][0]["url"], OUTPUT_DIR + "/.cover.jpg")  # download cover art
                        filename = OUTPUT_DIR + "/" + song["name"].replace("-", "~").replace("/", "~").replace("|", "~").replace("\"", "\'") + ".mp3"

                        timestamp_start = int(timestamps[idx]*1000 - t_start*1000)
                        timestamp_end = int(timestamps[idx + 1]*1000 - t_start*1000)
                        # the timestamps are too imprecise, therefore the next position is searched where silence starts / stops and then both values are compared
                        slice_start = min(chunks_starts, key=lambda x: abs(x - timestamp_start))
                        slice_end = min(chunks_ends, key=lambda x: abs(x - timestamp_end))
                        recording[slice_start:slice_end].export(filename, format="mp3", bitrate="192k", tags=tags, cover=OUTPUT_DIR + "/.cover.jpg")

                        if genius.access_token.startswith("Bearer"):
                            genius_song = genius.search_song(song["name"], song["artists"][0]["name"])
                            if genius_song is not None:  # only if a song text was found
                                lyrics = genius_song.lyrics
                            else:
                                lyrics = "There are no lyrics available for this track..."
                        else:
                            lyrics = "There are no lyrics available for this track..."
                        audiofile = eyed3.load(filename)  # inject the lyrics with eyeD3 because ffmpeg sets a wrong tag
                        audiofile.tag.lyrics.set(lyrics, u"XXX")
                        audiofile.tag.save()

                os.remove(OUTPUT_DIR + "/.temp.mp3")  # remove all temporary files
                os.remove(OUTPUT_DIR + "/.cover.jpg")
            os.remove(OUTPUT_DIR + "/.temp.wav")
            print("{}{} Done!".format(INFO, GREEN))

    except KeyboardInterrupt:
        subprocess.Popen("systemctl --user restart pipewire pipewire-pulse".split())
        exit("\n{}Detected Ctrl+C (Keyboard-Interrupt) ... Bye! :-)".format(RED))
