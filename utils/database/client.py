from .base import BaseDbService,DB_NAME
import aiosqlite

class ClientDbService(BaseDbService):

    def __init__(self,table_name:str):
        super().__init__(table_name=table_name)

    async def update(self,client_id:int,amount:int):
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE clients SET credit = credit + ? WHERE id = ?", (amount, client_id))
            await db.commit()