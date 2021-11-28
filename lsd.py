#!/usr/bin/python3

# CONFIGURATION-SECTION
OUTPUT_DIR = ""  # set an output folder in case you want to set this folder as default
SPOTIFY_CLIENT_ID = "SPOTIFY_CLIENT_ID"
SPOTIFY_CLIENT_SECRET = "SPOTIFY_CLIENT_SECRET"
GENIUS_ACCESS_TOKEN = "GENIUS_ACCESS_TOKEN"
SPOTIFY_CLIENT_ID = "c00625bc5088473f932aef5259b70860"
SPOTIFY_CLIENT_SECRET = "84f586c716de45e9b8b9e351d4084128"
GENIUS_ACCESS_TOKEN = "3AjfAc-3MXGS6ofU4ox_fbGyq7vETXyX5i_OQp7g4I_vhhNgCcki2cN9gaNhHm10"

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
              "\n" + " " * (T_WIDTH // 2 - 14) + " Linux-Spotify-Downloader 2.2" +
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
        time.sleep(1)

        # find spotify-input-sink and create monitor to record from
        print("{} I have to play a track to create a new recording interface ...".format(INFO))
        methods_if.Play()
        time.sleep(3)
        while True:
            sink_inputs = subprocess.run("pw-cli ls Node".split(), stdout=subprocess.PIPE).stdout.decode()
            if "application.name = \"spotify\"" in sink_inputs:
                break
            time.sleep(1)
        methods_if.Pause()
        time.sleep(0.5)
        sink_index = sink_inputs.split("application.name = \"spotify\"")[0].split("\tid ")[-1].split(",")[0]
        if subprocess.Popen("pactl load-module module-null-sink sink_name=lsd && pactl move-sink-input {} lsd".format(sink_index),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True).wait() == 0:
            print("{}{} I will now listen for tracks to be played ... "
                  "Please close Spotify as soon as you finished playing all songs!{}".format(INFO, BOLD, RST))
        else:
            exit("\r{} Error while creating the recording device for Spotify.".format(ERROR))

        # start the recording with parec (PulseAudio-Recording)
        print("\n" + "---- RECORDING " + "-" * (T_WIDTH - 15) + "\n")
        recording_process = subprocess.Popen("parec -d lsd.monitor --file-format=wav".split() + [OUTPUT_DIR + "/.temp.wav"])

        # initialize some variables
        counter = 0
        tracks = [""]
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
                    if tracks[-1].startswith("https://open.spotify.com/track/"):
                        ad = False
                        counter += 1
                        print("{} ({}) Recording: {} - {}{}{}".format(INFO, counter, meta["xesam:artist"][0], BOLD, meta["xesam:title"], RST))
                    elif not ad:
                        print("{} I have detected an advertisement, so I won't record this shit!".format(WARNING))
                        ad = True
                time.sleep(0.01)

        except dbus.exceptions.DBusException:  # means that Spotify is closed, because there is no bus any more
            recording_process.terminate()  # stop the recording
            subprocess.Popen("systemctl --user restart pipewire pipewire-pulse".split())  # restore original pulseaudio-configuration
            tracks = tracks[1:]  # remove the first empty element since it is only used once for comparing above
            print("\n{} I have recorded {} track(s).".format(INFO, counter))

            if counter > 0:
                print("\n" + "---- CONVERTING & TAGGING " + "-" * (T_WIDTH - 26) + "\n")

                print("{} Converting the recorded wav-file to mp3 ...".format(INFO))
                AudioSegment.from_wav(OUTPUT_DIR + "/.temp.wav").export(OUTPUT_DIR + "/.temp.mp3", format="mp3", bitrate="192k")

                # cut the recording, tag and export all tracks
                print("{} Splitting the recorded file on silence ...".format(INFO))
                recording = AudioSegment.from_mp3(OUTPUT_DIR + "/.temp.mp3")
                chunks = silence.split_on_silence(recording, silence_thresh=-65, min_silence_len=200, seek_step=10, keep_silence=True)

                # initialize access to Genius-API
                genius = None
                if GENIUS_ACCESS_TOKEN != "":
                    genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN)
                    genius.verbose = False

                idx = 0
                skipped = 0
                audio = AudioSegment.empty()
                while idx < len(chunks):  # go through all splitted chunks
                    if not tracks[idx - skipped].startswith("https://open.spotify.com/track/"):  # check if chunk is an ad
                        idx += 1
                        continue

                    if audio.duration_seconds == 0:  # if audio is empty ...
                        song = sp.track(tracks[idx - skipped])  # ... track it ...
                        print("{} Converting and tagging \"{}\" ...".format(INFO, song["name"]))
                        audio = chunks[idx]  # ... and start filling it up with the first chunk
                        idx += 1
                    if song["duration_ms"] / 1000 - 6 > audio.duration_seconds:  # if the audio isn't about as long as the original song...
                        audio += chunks[idx]  # ... fill it with the next chunk
                        skipped += 1
                        idx += 1
                    else:  # otherwise it can be tagged and exported
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

                        filename = OUTPUT_DIR + "/" + song["name"].replace("-", "~").replace("/", "~").replace("|", "~") + ".mp3"
                        audio.export(filename, format="mp3", bitrate="192k", tags=tags, cover=OUTPUT_DIR + "/.cover.jpg")

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

                        audio = AudioSegment.empty()

                os.remove(OUTPUT_DIR + "/.temp.mp3")  # remove all temporary files
                os.remove(OUTPUT_DIR + "/.cover.jpg")
            os.remove(OUTPUT_DIR + "/.temp.wav")
            print("{}{} Done!".format(INFO, GREEN))

    except KeyboardInterrupt:
        subprocess.Popen("systemctl --user restart pipewire pipewire-pulse".split())
        exit("\n{}Detected Ctrl+C (Keyboard-Interrupt) ... Bye! :-)".format(RED))
