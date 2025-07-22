import os, subprocess, aiofiles, aiohttp 
from yt_dlp import YoutubeDL
from config import YOUTUBE_IMG_URL

async def get_thumb(videoid):
    # Check if the video is already cached
    output_path = f"cache/{videoid}.mp4"
    if os.path.isfile(output_path):
        return output_path

    url = f"https://www.youtube.com/watch?v={videoid}"
    try:
        # yt-dlp configuration
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': f"cache/{videoid}.%(ext)s",
            'merge_output_format': 'mp4',
            'quiet': True,
        }

        # Download the video using yt-dlp
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Verify the downloaded file exists
        if os.path.isfile(output_path):
            return output_path
        else:
            return YOUTUBE_IMG_URL

    except Exception as e:
        print(f"Error downloading video: {e}")
        return YOUTUBE_IMG_URL
