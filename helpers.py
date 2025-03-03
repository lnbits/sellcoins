import httpx
from fastapi import Request
from lnurl.core import encode as lnurl_encode

def lnurler(sellcoins_id: str, route_name: str, req: Request) -> str:
    url = req.url_for(route_name, sellcoins_id=sellcoins_id)
    url_str = str(url)
    if url.netloc.endswith(".onion"):
        url_str = url_str.replace("https://", "http://")
    return str(lnurl_encode(url_str))

async def verify_stripe_key(api_key):
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url="https://api.stripe.com/v1/account",  headers=headers)
            if response.status_code == 200:
                account_data = response.json()
                return {
                    "success": True,
                    "id": account_data.get("id"),
                    "email": account_data.get("email"),
                    "business_name": account_data.get("business_profile", {}).get("name", "N/A"),
                }
            else:
                return False
    except Exception:
        return False
