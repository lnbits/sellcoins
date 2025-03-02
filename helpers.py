# Description: A place for helper functions.

from fastapi import Request
from lnurl.core import encode as lnurl_encode

# The lnurler function is used to generate the lnurlpay and lnurlwithdraw links
# from the lnurl api endpoints in views_lnurl.py.
# It needs the Request object to know the url of the LNbits.
# Lnurler is used in views_api.py


def lnurler(sellcoins_id: str, route_name: str, req: Request) -> str:
    url = req.url_for(route_name, sellcoins_id=sellcoins_id)
    url_str = str(url)
    if url.netloc.endswith(".onion"):
        url_str = url_str.replace("https://", "http://")
    return str(lnurl_encode(url_str))
