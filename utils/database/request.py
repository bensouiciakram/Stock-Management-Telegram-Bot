from .base import BaseDbService,DB_NAME
import aiosqlite


class RequestDbService(BaseDbService):

    def __init__(self,table_name:str):
        super().__init__(table_name=table_name)

    async def list(self):
        """Return all requests with related admin and nut names."""
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("""
                SELECT r.id, a.name AS admin, n.name AS nut, r.packages, r.credit_paid, r.description, r.requester_id, r.approved
                FROM request r
                JOIN admin a ON r.admin_id = a.id
                JOIN nut n ON r.nut_id = n.id
            """)
            return await cursor.fetchall()

    async def get_by_id(self, row_id: int):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT * FROM request WHERE id=?", (row_id,))
            return await cursor.fetchone()

    async def set_approved(self, row_id: int, approved: bool):
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE request SET approved=? WHERE id=?", (1 if approved else 0, row_id))
            await db.commit()

