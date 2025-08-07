import httpx
from lnurl import handle as lnurl_handle

async def get_pr(ln_address, amount):
    data = await lnurl_handle(ln_address, user_agent="LNbits Sellcoins", timeout=5)
    if data.get("status") == "ERROR":
        return
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url=f"{data['callback']}?amount={amount* 1000}")
            if response.status_code != 200:
                return
            return response.json()["pr"]
    except Exception:
        return None
