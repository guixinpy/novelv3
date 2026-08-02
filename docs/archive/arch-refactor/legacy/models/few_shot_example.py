import uuid

from sqlalchemy import JSON, Column, Float, String, Text

from app.db import Base


class FewShotExample(Base):
    __tablename__ = "few_shot_examples"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_type = Column(String, nullable=False)
    genre = Column(String, nullable=False)
    tags = Column(JSON, default=list)
    input = Column(Text, nullable=False)
    output = Column(Text, nullable=False)
    rating = Column(Float, default=1.0)
