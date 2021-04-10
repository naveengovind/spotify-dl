import tempfile
from urllib.request import urlopen
from pathlib import Path
import eyed3
from tqdm.auto import tqdm
from PIL import Image
from ytmusicapi import YTMusic
from youtube_dl import YoutubeDL
import re
import os
from simple_chalk import chalk
from .spotify_api import album, track, playlist

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
        # = Spotify(
            #oauth_manager=SpotifyPKCE(client_id='0f3478f7324f489cb56d390d339fb5cb',
                                      #redirect_uri='http://127.0.0.1:9090',
                                      #scope='user-library-read'))
        #self.genres = set(.recommendation_genre_seeds())

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
                    return {'id': result['videoId'], 'artwork': urlopen(track_data['album']['images'][0]['url']).read(),
                            'title': track_data['name'], 'artists': names, 'album': track_data['album']['name']}

    def match_track_with_spot_meta_data(self, track_data, search_term=None):
        if search_term is None:
            results = self.search(__create_search_term__(track_data=track_data), filter='songs', limit=3)
        else:
            results = self.search(search_term, filter='songs', limit=3)
        if len(results) > 0:
            for result in results:
                if abs(__convert_time_to_mills__(result['duration']) - track_data['duration_ms']) < 3000:
                    dl = self.get_song(result['videoId'])
                    URL = dl['thumbnail']['thumbnails'][-1]['url']
                    temp = tempfile.NamedTemporaryFile(suffix=".jpg")
                    img = Image.open(urlopen(URL)).convert('RGB')
                    img.save(temp.name, 'jpeg')
                    img.crop(
                        (int((img.width - img.height) / 2), 0, img.height + (int((img.width - img.height) / 2)),
                         img.height)).save(
                        temp.name, quality=100)
                    if result is not None and 'album' in result and result['album'] is not None:
                        album = result['album']['name']
                    else:
                        album = dl['title']
                    ret_data = {'id': result['videoId'], 'artwork': open(temp.name, 'rb').read(), 'title': dl['title'],
                                'artists': ', '.join(dl['artists']), 'album': album}
                    temp.close()
                    return ret_data

        return self.__match_track_back_up__(track_data=track_data)

    def download(self, url):
        type = __identify_type__(url)
        if type == 'album':
            tracks = album(url)['tracks']['items']
            for i in range(0, len(tracks)):
                ttrack = tracks[i]
                self.download_track(track_data=ttrack)
        elif type == 'playlist':
            tracks = playlist(url)['tracks']['items']
            for i in range(0, len(tracks)):
                ttrack = tracks[i]['track']
                self.download_track(track_data=ttrack)
        elif type == 'song':
            self.download_track(track_data=track(url))

    def download_track(self, track_data):
        try:
            meta_data = self.match_track_with_spot_meta_data(track_data)
            if meta_data is None:
                meta_data = self.match_track_with_spot_meta_data(track_data,
                                                                 search_term=__create_alternate_search_term__(track_data))
                if meta_data is None:
                    print('unable to download song ' + track_data['name'])
                    return
            url = 'https://music.youtube.com/watch?v=' + meta_data['id']
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': '~/Music/' + meta_data['title'] + '.%(ext)s',
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

            audiofile = eyed3.load(str(Path.home()) + '/Music/' + meta_data['title'] + '.mp3')
            if audiofile.tag is None:
                audiofile.initTag()
            audiofile.tag.images.set(3, meta_data['artwork'], 'image/jpeg')
            audiofile.tag.title = meta_data['title']
            audiofile.tag.artist = meta_data['artists']
            audiofile.tag.album = meta_data['album']
            #genres = .artist(track_data['artists'][0]['id'])['genres']
            #gen = []
            #for genre in genres:
                #if self.genres.__contains__(genre.replace(' ', '-')):
                    #gen.append(genre)
            #audiofile.tag.genre = ', '.join(gen)
            audiofile.tag.save()
        except Exception:
            print(chalk.red('error downloading a track'))

    def my_hook(self, d):
        filename = d['filename'] #type: str
        if d['status'] == 'finished':
            self.bars[filename].close()
            file_tuple = os.path.split(os.path.abspath(d['filename']))
            #print("Done downloading {}".format(file_tuple[1]))
            print(chalk.green('converting to mp3... '))
        if d['status'] == 'downloading':
            if filename not in self.bars:
                self.bars[filename] = tqdm(total=100, unit='mb', desc=filename[filename.rindex('/')+1:filename.rindex('.')], bar_format=chalk.white("{l_bar}")+chalk.cyan("{bar}")+chalk.white("{r_bar}"))
            p = d['_percent_str']
            p = p.replace('%', '')
            self.bars[filename].n = float(p)  # check this
            self.bars[filename].refresh()
