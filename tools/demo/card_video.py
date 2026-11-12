"""Make the short video of a demo vendor from photos of its products (a slow zoom on each one,
then a fade to the next), as a vendor would film its products: 4:5, 720 x 900, MP4.

    python3 tools/demo/card_video.py OUT.mp4 photo1.jpg photo2.jpg ...
"""
import subprocess
import sys

from PIL import Image

WIDTH, HEIGHT, FPS = 720, 900, 30
SECONDS, FADE = 2.2, 0.4


def corner_colour(path):
    image = Image.open(path).convert("RGB")
    red, green, blue = image.getpixel((4, 4))
    return f"0x{red:02X}{green:02X}{blue:02X}"


def main(out, photos):
    frames = int(SECONDS * FPS)
    command = ["ffmpeg", "-y", "-v", "error"]
    filters = []
    for index, photo in enumerate(photos):
        command += ["-i", photo]
        filters.append(
            f"[{index}:v]scale={WIDTH}:{WIDTH},pad={WIDTH}:{HEIGHT}:0:{(HEIGHT - WIDTH) // 2}:color={corner_colour(photo)},"
            f"zoompan=z='min(1.0+0.0016*on,1.12)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":s={WIDTH}x{HEIGHT}:fps={FPS},setsar=1,format=yuv420p[v{index}]"
        )
    last = "v0"
    for index in range(1, len(photos)):
        offset = index * (SECONDS - FADE)
        filters.append(f"[{last}][v{index}]xfade=transition=fade:duration={FADE}:offset={offset:.2f}[x{index}]")
        last = f"x{index}"
    command += [
        "-filter_complex", ";".join(filters), "-map", f"[{last}]",
        "-c:v", "libx264", "-preset", "slow", "-crf", "30", "-profile:v", "main", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-an", out,
    ]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
