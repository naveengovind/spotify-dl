import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen
from pathlib import Path
import eyed3
from ytmusicapi import YTMusic
from youtube_dl import YoutubeDL
import re
import os
from simple_chalk import chalk
from spotify_api import album, track, playlist
from rich.progress import Progress
from lyricsgenius import Genius
import time


def __convert_time_to_mills__(s: str) -> int:
    hours, minutes, seconds = (["0", "0"] + s.split(":"))[-3:]
    hours = int(hours)
    minutes = int(minutes)
    seconds = float(seconds)
    return int(3600000 * hours + 60000 * minutes + 1000 * seconds)


def __create_search_term__(track_data) -> str:
    name = track_data['name']
    artists = track_data['artists']
    artistNames = ''

    for artist in artists:
        artistNames += artist["name"] + ' '

    artistNames = artistNames.strip()
    return name + ' ' + artistNames


def __create_alternate_search_term__(track_data) -> str:
    name = track_data['name']
    name = re.sub("[\(\[].*?[\)\]]", "", name)
    artists = track_data['artists'][0]['name']
    return name + ' ' + artists


def __identify_type__(url: str):
    if url.__contains__('track'):
        return 'song'
    elif url.__contains__('album'):
        return 'album'
    elif url.__contains__('playlist'):
        return 'playlist'


class ytmusic_tools(YTMusic):

    def __init__(self):
        super().__init__()
        self.bars = {}
        self.bars_count = 0
        self.lock = threading.Lock()
        self.progress = Progress()  # type: Progress
        self.progress.__enter__()
        self.genius = Genius("w_iYnsU-rtqLy_fgQKKftC9huYvIT9x9TbXRpe2oVfr8TzCnbipUp7BTXGB16j3v")
        self.failed = []
        # = Spotify(
        # oauth_manager=SpotifyPKCE(client_id='0f3478f7324f489cb56d390d339fb5cb',
        # redirect_uri='http://127.0.0.1:9090',
        # scope='user-library-read'))
        # self.genres = set(.recommendation_genre_seeds())

    def __match_track_back_up__(self, track_data, search_term=None):
        if search_term is None:
            results = self.search(__create_search_term__(track_data=track_data), filter='videos', limit=3)
        else:
            results = self.search(search_term, filter='videos', limit=3)
        if len(results) > 0:
            for result in results:
                if abs(__convert_time_to_mills__(result['duration']) - track_data['duration_ms']) < 5000:
                    names = ''
                    for artist in track_data['artists']:
                        if len(names) > 1:
                            names += ', ' + artist['name']
                        else:
                            names += artist['name']
                    lims = u"""la la la"""
                    try:
                        song = self.genius.search_song(track_data['name'], track_data['artists'][0]['name'])
                        lyrics = str(song.lyrics)
                        lims = lims.replace('la la la', re.sub("\[.*?]", "", lyrics))
                    except Exception:
                        print("Could not find lyrics for", track_data['name'])
                        lims = lims.replace("la la la", "")
                    return {'id': result['videoId'], 'artwork': urlopen(track_data['album']['images'][0]['url']).read(),
                            'title': track_data['name'], 'artists': names, 'album': track_data['album']['name'],
                            'lyrics': lims, 'track_num': -1}

    def match_track_with_spot_meta_data(self, track_data, search_term=None):
        if search_term is None:
            results = self.search(__create_search_term__(track_data=track_data), filter='songs', limit=3)
        else:
            results = self.search(search_term, filter='songs', limit=3)
        if len(results) > 0:
            for result in results:
                if abs(__convert_time_to_mills__(result['duration']) - track_data['duration_ms']) < 3000:
                    ret_data = {}
                    dl = self.get_song(result['videoId'])['videoDetails']
                    if result is not None and 'album' in track_data and track_data['album'] is not None:
                        album = track_data['album']['name']
                        ret_data = {'id': result['videoId'],
                                    'artwork': urlopen(track_data['album']['images'][0]['url']).read(),
                                    'title': dl['title'],
                                    'artists': dl['author'], 'album': album, 'lyrics': u"""la la la""",
                                    "track_num": track_data['disc_number']}
                    else:
                        bum = track(track_data['id'])['album']
                        album = bum['name']
                        ret_data = {'id': result['videoId'], 'artwork': urlopen(bum['images'][0]['url']).read(),
                                    'title': dl['title'],
                                    'artists': dl['author'], 'album': album, 'lyrics': u"""la la la""",
                                    "track_num": track_data['disc_number']}
                    try:
                        song = self.genius.search_song(track_data['name'], track_data['artists'][0]['name'])
                        lyrics = str(song.lyrics)
                        ret_data['lyrics'] = ret_data['lyrics'].replace('la la la', re.sub("\[.*?]", "", lyrics))
                    except Exception:
                        ret_data['lyrics'] = ""
                        print("Could not find lyrics for", track_data['name'])
                    return ret_data

        return self.__match_track_back_up__(track_data=track_data)

    def download(self, url):
        type = __identify_type__(url)
        prat = ""
        plim = None
        with ThreadPoolExecutor(max_workers=500) as executor:
            if type == 'album':
                tracks = album(url)['tracks']['items']
                for i in range(0, len(tracks)):
                    ttrack = tracks[i]
                    executor.submit(self.download_track, track_data=ttrack, executor=executor, track_num=i)
                    time.sleep(3)
            elif type == 'playlist':
                plim = playlist(url)
                tracks = plim['tracks']['items']
                for i in range(0, len(tracks)):
                    ttrack = tracks[i]['track']
                    executor.submit(self.download_track, track_data=ttrack, executor=executor)
                    time.sleep(3)
            elif type == 'song':
                executor.submit(self.download_track, track_data=track(url), executor=executor)
            else:
                results = self.search(url, filter='songs', limit=5)
                print(url)
                print(results)
        if type == 'playlist':
            lists = ""
            for filename in os.listdir(prat):
                f = os.path.join(prat, filename)
                # checking if it is a file
                if os.path.isfile(f):
                    lists += "./" + filename + "\n"
            with open(os.path.join(prat, plim['name'] + ".m3u"), "w") as file:
                file.write(lists)
        self.exit_handler()

    def download_track(self, track_data, executor=None, track_num=0):
        prat = os.path.join(str(Path.home()), "Music")
        try:
            meta_data = self.match_track_with_spot_meta_data(track_data)
            if meta_data is None:
                meta_data = self.match_track_with_spot_meta_data(track_data,
                                                                 search_term=__create_alternate_search_term__(
                                                                     track_data))
                if meta_data is None:
                    print('unable to download song ' + track_data['name'])
                    return
            url = 'https://music.youtube.com/watch?v=' + meta_data['id']
            path = Path(
                os.path.join(prat, meta_data['artists'].replace('&', ',').split(', ')[0].strip(), meta_data['album']))
            path.mkdir(parents=True, exist_ok=True)
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(path, (meta_data['title'].replace('/', '_').replace('\\', '_') + ".%(ext)s")),
                'progress_hooks': [self.my_hook],
                'quiet': True,
                'no_warnings': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '0',
                }]
            }
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            audiofile = eyed3.load(
                os.path.join(path, (meta_data['title'].replace('/', '_').replace('\\', '_') + ".mp3")))
            if audiofile.tag is None:
                audiofile.initTag()
            audiofile.tag.images.set(3, meta_data['artwork'], 'image/jpeg')
            audiofile.tag.title = meta_data['title']
            audiofile.tag.artist = meta_data['artists'].replace('&', ',')
            audiofile.tag.album = meta_data['album']
            audiofile.tag.album_artist = meta_data['artists'].replace('&', ',').split(', ')[0].strip()
            audiofile.tag.lyrics.set('\n'.join(meta_data['lyrics'].split('\n')[1:]))
            if meta_data['track_num'] != -1:
                audiofile.tag.track_num = meta_data['track_num']
            else:
                audiofile.tag.track_num = track_num
            # genres = .artist(track_data['artists'][0]['id'])['genres']
            # gen = []
            # for genre in genres:
            # if self.genres.__contains__(genre.replace(' ', '-')):
            # gen.append(genre)
            # audiofile.tag.genre = ', '.join(gen)
            audiofile.tag.save()
        except Exception:
            executor.submit(self.download_track, track_data=track_data, prat=prat, executor=executor)
            print(chalk.red('error downloading track ' + track_data['name']))
            self.failed.append(track_data)

    def my_hook(self, d):
        filename = d['filename']  # type: str
        if d['status'] == 'finished':
            file_tuple = os.path.split(os.path.abspath(d['filename']))
            self.progress.remove_task(self.bars[filename])
            # print("Done downloading {}".format(file_tuple[1]))
            # print(chalk.green('converting to mp3... '))
        if d['status'] == 'downloading':
            if filename not in self.bars:
                self.bars[filename] = self.progress.add_task(
                    "[red]" + filename[filename.rindex('/') + 1:filename.rindex('.')] + ": ", total=1000)
            p = d['_percent_str']
            p = p.replace('%', '')
            self.progress.update(self.bars[filename], advance=float(p) * 10)

    def exit_handler(self):
        self.progress.__exit__(None, None, None)
        print(chalk.green('exiting...'))
