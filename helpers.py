import httpx
from lnurl import handle as lnurl_handle
from lnurl.models import LnurlPayResponse


async def get_pr(ln_address, amount):
    data = await lnurl_handle(ln_address, user_agent="LNbits Sellcoins", timeout=5)
    if not isinstance(data, LnurlPayResponse):
        return None
    callback_url = f"{data.callback}?amount={int(amount * 1000)}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url=callback_url)
            if response.status_code != 200:
                return
            return response.json()["pr"]
    except Exception:
        return None
