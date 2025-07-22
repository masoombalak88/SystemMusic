import os
import subprocess
import aiofiles
import aiohttp
from youtubesearchpython.__future__ import VideosSearch

from config import YOUTUBE_IMG_URL

async def get_thumb(videoid):
    if os.path.isfile(f"cache/{videoid}.mp4"):
        return f"cache/{videoid}.mp4"

    url = f"https://www.youtube.com/watch?v={videoid}"
    try:
        results = VideosSearch(url, limit=1)
        for result in (await results.next())["result"]:
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        # Convert the thumbnail image to a 5-second MP4 video using FFmpeg
        output_video = f"cache/{videoid}.mp4"
        ffmpeg_cmd = [
            "ffmpeg", "-loop", "1", "-i", f"cache/thumb{videoid}.png",
            "-c:v", "libx264", "-t", "5", "-pix_fmt", "yuv420p",
            "-vf", "scale=1280:720", output_video
        ]
        subprocess.run(ffmpeg_cmd, check=True)

        try:
            os.remove(f"cache/thumb{videoid}.png")
        except:
            pass

        return output_video
    except Exception:
        return YOUTUBE_IMG_URL
