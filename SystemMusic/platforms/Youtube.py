import asyncio
import os
import re
import httpx
from typing import Union

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

from SystemMusic.utils.database import is_on_off
from SystemMusic.utils.formatters import time_to_seconds


async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")


async def get_stream_url(query, video=False):
    api_url = "http://47.129.201.23:2020/try"
    
    async with httpx.AsyncClient(timeout=60) as client:
        params = {"query": query, "vid": "true" if video else "false"}
        response = await client.get(api_url, params=params)
        if response.status_code != 200:
            return ""
        info = response.json()
        if "error" in info:
            return ""
        return info.get("link", "")


async def get_direct_audio(tg_url: str):
    if not tg_url:
        return None
    cmd = f'yt-dlp -g -f "best" --no-warnings --quiet "{tg_url}"'
    out = await shell_cmd(cmd)
    lines = [line.strip() for line in out.split('\n') if line.strip()]
    return lines[0] if lines else None


async def get_direct_video(tg_url: str):
    if not tg_url:
        return None
    cmd = f'yt-dlp -g -f "best" --no-warnings --quiet "{tg_url}"'
    out = await shell_cmd(cmd)
    lines = [line.strip() for line in out.split('\n') if line.strip()]
    return lines[0] if lines else None


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if re.search(self.regex, link):
            return True
        else:
            return False

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset : offset + length]

    async def _get_yt_entry(self, link: str, limit: int = 1):
        if "&" in link:
            link = link.split("&")[0]
        ydl_opts = {'quiet': True, 'no_warnings': True}
        is_url = re.search(self.regex, link)
        search_term = f"ytsearch{limit}:{link}" if not is_url else link
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_term, download=False)
            if 'entries' in info:
                entries = info['entries']
                if limit == 1:
                    return entries[0] if entries else None
                return entries
            else:
                return [info]

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        entries = await self._get_yt_entry(link, 1)
        if not entries:
            return "", "0:00", 0, "", ""
        entry = entries[0]
        title = entry.get('title', '')
        duration_sec = entry.get('duration', 0)
        duration_min = f"{duration_sec//60}:{duration_sec%60:02d}" if duration_sec else "0:00"
        thumbnail = entry.get('thumbnail', '')
        vidid = entry.get('id', '')
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        entries = await self._get_yt_entry(link, 1)
        if not entries:
            return ""
        return entries[0].get('title', '')

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        entries = await self._get_yt_entry(link, 1)
        if not entries:
            return "0:00"
        duration_sec = entries[0].get('duration', 0)
        return f"{duration_sec//60}:{duration_sec%60:02d}" if duration_sec else "0:00"

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        entries = await self._get_yt_entry(link, 1)
        if not entries:
            return ""
        return entries[0].get('thumbnail', '')

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        tg_url = await get_stream_url(link, True)
        direct_url = await get_direct_video(tg_url)
        return direct_url or ""

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        playlist = await shell_cmd(
            f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
        )
        try:
            result = playlist.split("\n")
            for key in result:
                if key == "":
                    result.remove(key)
        except:
            result = []
        return result

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        entries = await self._get_yt_entry(link, 1)
        if not entries:
            return {}, ""
        entry = entries[0]
        title = entry.get('title', '')
        duration_sec = entry.get('duration', 0)
        duration_min = f"{duration_sec//60}:{duration_sec%60:02d}" if duration_sec else "0:00"
        vidid = entry.get('id', '')
        yturl = entry.get('webpage_url', f"https://www.youtube.com/watch?v={vidid}")
        thumbnail = entry.get('thumbnail', '')
        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }
        return track_details, vidid

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        ytdl_opts = {"quiet": True}
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        with ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for format in r["formats"]:
                try:
                    str(format["format"])
                except:
                    continue
                if not "dash" in str(format["format"]).lower():
                    try:
                        format["format"]
                        format["filesize"]
                        format["format_id"]
                        format["ext"]
                        format["format_note"]
                    except:
                        continue
                    formats_available.append(
                        {
                            "format": format["format"],
                            "filesize": format["filesize"],
                            "format_id": format["format_id"],
                            "ext": format["ext"],
                            "format_note": format["format_note"],
                            "yturl": link,
                        }
                    )
        return formats_available, link

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        entries = await self._get_yt_entry(link, 10)
        if not entries or query_type >= len(entries):
            return "", "0:00", "", ""
        entry = entries[query_type]
        title = entry.get('title', '')
        duration_sec = entry.get('duration', 0)
        duration_min = f"{duration_sec//60}:{duration_sec%60:02d}" if duration_sec else "0:00"
        vidid = entry.get('id', '')
        thumbnail = entry.get('thumbnail', '')
        return title, duration_min, thumbnail, vidid

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        if videoid:
            link = self.base + link
        loop = asyncio.get_running_loop()

        def song_video_dl_from_tg(tg_url: str, title: str):
            if not tg_url or not title:
                return None
            ydl_optssx = {
                "format": "best",
                "outtmpl": f"downloads/{title}.%(ext)s",
                "quiet": True,
                "no_warnings": True,
                "merge_output_format": "mp4",
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([tg_url])
            fpath = f"downloads/{title}.mp4"
            if os.path.exists(fpath):
                return fpath
            return None

        def song_audio_dl_from_tg(tg_url: str, title: str):
            if not tg_url or not title:
                return None
            ydl_optssx = {
                "format": "best",
                "outtmpl": f"downloads/{title}.%(ext)s",
                "quiet": True,
                "no_warnings": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([tg_url])
            fpath = f"downloads/{title}.mp3"
            if os.path.exists(fpath):
                return fpath
            return None

        if songvideo:
            tg_url = await get_stream_url(link, True)
            fpath = await loop.run_in_executor(None, song_video_dl_from_tg, tg_url, title)
            return fpath or ""
        elif songaudio:
            tg_url = await get_stream_url(link, False)
            fpath = await loop.run_in_executor(None, song_audio_dl_from_tg, tg_url, title)
            return fpath or ""
        elif video:
            tg_url = await get_stream_url(link, True)
            downloaded_file = await get_direct_video(tg_url)
            direct = None
        else:
            tg_url = await get_stream_url(link, False)
            downloaded_file = await get_direct_audio(tg_url)
            direct = None
        return downloaded_file, direct
