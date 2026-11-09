from lnbits.core.services import get_pr_from_lnurl


async def get_pr(ln_address, amount):
    try:
        return await get_pr_from_lnurl(ln_address, int(amount * 1000))
    except Exception:
        return None
