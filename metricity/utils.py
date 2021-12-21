"""General utility functions and classes for Metricity."""
from datetime import datetime, timezone

import discord
from sqlalchemy.engine import Dialect
from sqlalchemy.types import DateTime, TypeDecorator

from metricity.models import Message, Thread


class TZDateTime(TypeDecorator):
    """
    A db type that supports the use of aware datetimes in user-land.

    Source from SQLAlchemy docs:
    https://docs.sqlalchemy.org/en/14/core/custom_types.html#store-timezone-aware-timestamps-as-timezone-naive-utc

    Editted to include docstrings and type hints.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime, dialect: Dialect) -> datetime:
        """Convert the value to aware before saving to db."""
        if value is not None:
            if not value.tzinfo:
                raise TypeError("tzinfo is required")
            value = value.astimezone(timezone.utc).replace(
                tzinfo=None
            )
        return value

    def process_result_value(self, value: datetime, dialect: Dialect) -> datetime:
        """Convert the value to aware before passing back to user-land."""
        if value is not None:
            value = value.replace(tzinfo=timezone.utc)
        return value


async def insert_thread(thread: discord.Thread) -> None:
    """Insert the given thread to the database."""
    await Thread.create(
        id=str(thread.id),
        parent_channel_id=str(thread.parent_id),
        name=thread.name,
        archived=thread.archived,
        auto_archive_duration=thread.auto_archive_duration,
        locked=thread.locked,
        type=thread.type.name,
    )


async def sync_message(message: discord.Message, from_thread: bool) -> None:
    """Sync the given message with the database."""
    if await Message.get(str(message.id)):
        return

    args = {
        "id": str(message.id),
        "channel_id": str(message.channel.id),
        "author_id": str(message.author.id),
        "created_at": message.created_at
    }

    if from_thread:
        thread = message.channel
        args["channel_id"] = str(thread.parent_id)
        args["thread_id"] = str(thread.id)
        if not await Thread.get(str(thread.id)):
            await insert_thread(thread)

    await Message.create(**args)
