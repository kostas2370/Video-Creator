import logging
from typing import Union

from vendor.bing_image_downloader import downloader

logger = logging.getLogger(__name__)


def download_image(
    query: str, path: str, amount: int = 1, *args, **kwargs
) -> Union[str, None]:
    """
    Download images from Bing using a downloader.

    Parameters:
    -----------
    query : str
        The search query for images.
    path : str
        The directory path where the downloaded images will be saved.
    amount : int, optional
        The number of images to download. Default is 1.
    *args, **kwargs : additional arguments and keyword arguments
        Additional arguments and keyword arguments to pass to the downloader.

    Returns:
    --------
    str or None
        The path to the first downloaded image, or None if the download failed.

    Notes:
    ------
    - This function uses a downloader to download images from Bing based on the provided search query.
    - The downloaded images are saved in the specified directory path.
    - The number of images to download can be specified using the 'amount' parameter.
    - Additional arguments and keyword arguments can be passed to the downloader.
    """
    try:
        logger.info("Downloading image from bing")
        return downloader.download(
            query=f"{query}",
            limit=amount,
            output_dir=path,
            adult_filter_off=True,
            force_replace=False,
            timeout=60,
            filter="photo",
        )[0]

    except Exception as exc:
        logger.error(f"Error downloading image with query {query} Error {exc}")
        return None
