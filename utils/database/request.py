from .base import BaseDbService,DB_NAME
import aiosqlite


class RequestDbService(BaseDbService):

    def __init__(self,table_name:str):
        super().__init__(table_name=table_name)

    async def list(self):
        """Return all requests with related admin and nut names."""
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("""
                SELECT r.id, a.name AS admin, n.name AS nut, r.packages, r.credit_paid, r.description
                FROM request r
                JOIN admin a ON r.admin_id = a.id
                JOIN nut n ON r.nut_id = n.id
            """)
            return await cursor.fetchall()

