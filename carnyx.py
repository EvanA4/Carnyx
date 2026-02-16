from sys import argv
from yt_dlp import YoutubeDL
from unidecode import unidecode
from mutagen.easyid3 import EasyID3
from requests import get
from json import loads, dumps
import os


class VideoData:
    def __init__(self, id: str, title: str, channel: str):
        self.id = id
        self.title = title
        self.channel = channel


def printUsage():
    print(f"usage: python {argv[0]} <playlistID> <playlistDir>")
    print("                      <videoID> [optional playlist name]")
    exit(1)


def getVideoData(ytid: str) -> list[VideoData]:
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "dump_single_json": False,
        "no_warnings": True
    }
    with YoutubeDL(ydl_opts) as ydl:
        is_video = len(argv[1]) == 11
        videos = []
        if is_video:
            info = ydl.extract_info(f"https://youtube.com/watch?v={ytid}", download=False)
            videos.append(VideoData(info["id"], unidecode(info["title"]).strip(), info["channel"]))
        else:
            info = ydl.extract_info(f"https://youtube.com/playlist?list={ytid}", download=False)
            videos = []
            for video in info["entries"]:
                videos.append(VideoData(
                    video["id"],
                    unidecode(video["title"]).strip(),
                    video["channel"]
                ))
        return videos


def setMetaData(abs_path: str, video: VideoData, playlist_name = ""):
    id3 = EasyID3(abs_path)
    id3["artist"] = video.channel
    if playlist_name != "":
        id3["album"] = playlist_name
    id3["title"] = video.title
    id3.save()


def downloadVideo(video: VideoData, playlist_name = "", do_path = False) -> None:
    '''
    Four options:
    !playlist_name && !do_path => create in cwd
    !playlist_name && do_path => ERROR
    playlist_name && !do_path => create in cwd
    playlist_name && do_path => create in folder
    '''

    if not playlist_name and do_path:
        print("Invalid combination of playlist_name and do_path!")
        exit(1)

    abs_dir_path = os.path.abspath(playlist_name if do_path else ".")
    abs_file_path = f"{abs_dir_path}/{video.title}.mp3"

    # download video
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': abs_file_path[:-4],
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True
    }
    ydl = YoutubeDL(ydl_opts)
    ydl.download([f"https://youtube.com/watch?v={video.id}"])

    # set metadata
    setMetaData(
        abs_file_path,
        video,
        playlist_name
    )


def handleVideo(ytid: str, playlist_name = "") -> None:
    video = getVideoData(ytid)[0]
    if playlist_name == "":
        downloadVideo(video)
    else:
        downloadVideo(video, playlist_name)


def handlePlaylist(ytid: str, playlist_name: str) -> None:
    if not os.path.exists(playlist_name):
        os.mkdir(playlist_name)

    videos = getVideoData(ytid)
    cloud_titles = { video.title: video for video in videos }
    local_titles = set(map(lambda x: x[:-4], os.listdir(playlist_name)))

    to_create = [] # in cloud but not in local

    for title in cloud_titles:
        if title not in local_titles:
            to_create.append(cloud_titles[title])
    for title in local_titles:
        if title not in cloud_titles:
            os.remove(f"{playlist_name}/{title}.mp3")

    for video in to_create:
        downloadVideo(video, playlist_name, True)


def main():
    # handle input
    if len(argv) < 2:
        printUsage()
    is_video = len(argv[1]) == 11
    if (not is_video and len(argv) != 3)    \
        or (is_video and len(argv) > 3)     \
        or (not is_video and len(argv[1]) != 34):
        printUsage()

    # direct to appropriate handler
    if is_video:
        if len(argv) == 2:
            handleVideo(argv[1])
        else:
            handleVideo(argv[1], argv[2])
    else:
        if (os.path.abspath(argv[2]) == os.getcwd()):
            print("Error: playlist directory cannot be cwd.")
            exit(1)
        handlePlaylist(argv[1], argv[2])


if __name__ == "__main__":
    main()


# PLtbneUBkSuGFXfEZyUIq2n-G6zRNfzNgh
# NqtcqA53l3I