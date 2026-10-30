import subprocess


def run_ffmpeg(arguments, *, cwd=None, timeout=3600):
    return subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-threads",
            "2",
            "-filter_complex_threads",
            "2",
            "-filter_threads",
            "2",
            *arguments,
        ],
        cwd=cwd,
        capture_output=True,
        check=True,
        timeout=timeout,
    )
