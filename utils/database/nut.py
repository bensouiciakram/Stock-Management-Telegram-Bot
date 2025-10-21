from .base import BaseDbService,DB_NAME
import aiosqlite

class NutDbService(BaseDbService):

    def __init__(self,table_name:str):
        super().__init__(table_name=table_name)

    async def update(self,nut_id: int, delta: int):
        """Increase or decrease the number of packages for a nut."""
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "UPDATE nuts SET packages = packages + ? WHERE id = ?",
                (delta, nut_id)
            )
            await db.commit()