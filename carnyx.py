import sys
import subprocess
import os
from unidecode import unidecode
from pathlib import Path
from mutagen import File
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError
import json
import re


class SilentLogger:
    def debug(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass  # swallow errors


# def dump_obj(src):
#     file = open("junk.json", "w")
#     file.write(json.dumps(src, indent=4))
#     file.close()


def clean_str(src: str):
    unidecoded = unidecode(src)
    alphanumeric = "".join(c for c in unidecoded if c.isdigit() or c.isalpha() or c == " ")
    single_spaced = re.sub(' +', ' ', alphanumeric)
    return single_spaced.strip()


def handle_args() -> str:
    if len(sys.argv) != 2:
        print("usage: carnyx.py <playlist_url|playlist_id>", file=sys.stderr)
        exit(1)
    playlist_url = sys.argv[1]
    if sys.argv[1].find("youtube.com") == -1:
        playlist_url = f"https://www.youtube.com/playlist?list={sys.argv[1]}"
    return playlist_url


def get_playlist(playlist_url: str) -> tuple[str, list[dict[str]]]:
    ydl_opts = {
        "logger": SilentLogger(),
        "quiet": True,
        "no_color": True,
        "ignore_no_formats_error": True,
        "force_generic_extractor": False,
        "noprogress": True,
        "no_warnings": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(playlist_url, download=False)
            playlist_name = info["title"]
            videos = []
            for entry in info["entries"]:
                if entry is not None and entry["title"] != "[Deleted video]":
                    try:
                        videos.append({
                            "id": entry["id"],
                            "title": clean_str(entry["title"]),
                            "channel": clean_str(entry["channel"])
                        })
                    except KeyError as e:
                        if "id" in entry.keys():
                            print(f"\tRecieved invalid video metadata: Missing {e} for {entry["id"]}", flush=True)
                        else:
                            print(f"\tRecieved invalid video metadata: Missing {e} for {entry["id"]}", flush=True)
            return (playlist_name, videos)
        except (ExtractorError, DownloadError) as e:
            print(f"Failed to extract playlist data: {e}")
            exit(1)


def get_local_videos(title: str) -> list[str]:
    if not os.path.exists(title):
        os.mkdir(title)
        return []

    return list(map(lambda x: x[:-4], os.listdir(title)))


def compare_videos(local_videos: list[str], playlist_videos: list[dict[str]]):
    local_set = set(local_videos)
    playlist_set = set(map(lambda x: x["title"], playlist_videos))
    to_download = list(filter(lambda x: x["title"] not in local_set, playlist_videos))
    to_delete = list(filter(lambda x: x not in playlist_set, local_videos))
    return to_download, to_delete


def delete_videos(to_delete: list[str], playlist_title: str):
    for video in to_delete:
        video_path = os.path.join(playlist_title, f"{video}.mp3")
        if os.path.isfile(video_path):
            print(f"\t\"{video}\"", flush=True)
            os.remove(video_path)


def set_metadata(video: dict[str], playlist_title: str):
    file_path = os.path.join(playlist_title, f"{video["title"]}.mp3")
    file = File(file_path, easy=True)
    file["title"] = [video["title"]]
    file["album"] = [playlist_title]
    file["artist"] = [video["channel"]]
    file.save()


def download_video(video: dict[str], playlist_title:str):
    abs_dir_path = os.path.abspath(playlist_title)
    abs_file_path = f'{abs_dir_path}/{video["title"]}.mp3'

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': abs_file_path[:-4],
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        "no_color": True,
        "ignore_no_formats_error": True,
        "force_generic_extractor": False,
        "noprogress": True,
        "logger": SilentLogger()
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://youtube.com/watch?v={video["id"]}"])
            ydl.close()
        set_metadata(video, playlist_title)
    except (ExtractorError, DownloadError) as e:
        print(f"\t\tDownload failed: {e.msg}")
    


def download_videos(videos: list[dict[str]], playlist_title: str):
    for video in videos:
        print(f"\t\"{video["title"]}\"", flush=True)
        download_video(video, playlist_title)


def confirm_metadata(videos: list[dict[str]], playlist_title: str):
    for video in videos:
        file_path = os.path.join(playlist_title, f"{video["title"]}.mp3")
        if os.path.isfile(file_path):
            set_metadata(video, playlist_title)


def main():
    playlist_url = handle_args()
    print(f"Playlist URL: {playlist_url}", flush=True)
    
    playlist_title, playlist_videos = get_playlist(playlist_url)
    print(f"Playlist loaded: \"{playlist_title}\" with {len(playlist_videos)} videos", flush=True)
    
    local_videos = get_local_videos(playlist_title)
    if len(local_videos) != 0:
        print(f"Local playlist loaded: {len(local_videos)} videos", flush=True)
    else:
        print("No local files for playlist detected", flush=True)

    to_download, to_delete = compare_videos(local_videos, playlist_videos)
    if len(to_download) != 0:
        print("To download:")
        for video in to_download:
            print(f"\t[{video["id"]}] ({video["channel"]}): \"{video["title"]}\"")
    if len(to_delete) != 0:
        print("To delete:")
        for video in to_delete:
            print(f"\t\"{video}\"")

    if len(to_delete) != 0:
        print("Deleting videos:", flush=True)
        delete_videos(to_delete, playlist_title)

    if len(to_download) != 0:
        print("Downloading videos:", flush=True)
        download_videos(to_download, playlist_title)

    confirm_metadata(to_download, playlist_title)


if __name__ == "__main__":
    main()
