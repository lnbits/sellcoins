async def m001_initial(db):
    """
    Initial templates table.
    """
    await db.execute(
        """
        CREATE TABLE sellcoins.settings (
            user_id TEXT PRIMARY KEY NOT NULL,
            fiat TEXT NOT NULL,
            wallet_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            stripe_key TEXT NOT NULL
        );
    """
    )


async def m002_initial(db):
    """
    Initial templates table.
    """
    await db.execute(
        """
        CREATE TABLE sellcoins.products (
            id TEXT PRIMARY KEY NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            price INTEGER NOT NULL,
            auto_convert BOOLEAN,
            amount INTEGER,
            cut_percentage INTEGER
        );
    """
    )


async def m003_initial(db):
    """
    Initial templates table.
    """
    await db.execute(
        """
        CREATE TABLE sellcoins.orders (
            id TEXT PRIMARY KEY NOT NULL,
            product_id TEXT NOT NULL,
            status TEXT NOT NULL,
            stripe_purchase_id TEXT NOT NULL,
            created TEXT NOT NULL
        );
    """
    )
