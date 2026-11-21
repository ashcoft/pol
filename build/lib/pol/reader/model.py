"""Small, transport-agnostic feed model shared by every reader module."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Item:
    title: str = ''
    link: str = ''
    id: str = ''
    summary: str = ''
    content: str = ''
    date: datetime | None = None
    author: str = ''
    images: list[str] = field(default_factory=list)
    enclosures: list[dict[str, Any]] = field(default_factory=list)

    def body(self, clip=False) -> str:
        """Return the richest content available, keeping the summary when asked."""
        if not self.content:
            return self.summary
        if clip and self.summary and self.summary not in self.content:
            return self.summary + self.content
        return self.content

    def as_dict(self) -> dict[str, Any]:
        return {
            'title': self.title,
            'link': self.link,
            'id': self.id,
            'summary': self.summary,
            'content': self.content,
            'date': self.date.isoformat() if self.date else None,
            'author': self.author,
            'images': list(self.images),
            'enclosures': list(self.enclosures),
        }


@dataclass
class Feed:
    title: str = ''
    link: str = ''
    description: str = ''
    language: str = ''
    url: str = ''
    format: str = 'rss'
    items: list[Item] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            'title': self.title,
            'link': self.link,
            'description': self.description,
            'language': self.language,
            'url': self.url,
            'format': self.format,
            'items': [item.as_dict() for item in self.items],
        }
