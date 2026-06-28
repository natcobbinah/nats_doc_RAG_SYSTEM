from flask_login import UserMixin
from sqlalchemy.orm import relationship
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Boolean
from app.config import db
from app.models.oauth.resource_owner import user_roles, RoleName


class Role(db.Model):
    __tablename__ = "role"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Enum(RoleName), unique=True, nullable=False)  # e.g., "User", "Admin"
    description = db.Column(db.String(200))

    users = db.relationship(
        "User",
        secondary=user_roles,
        back_populates="roles"
    )

    def __repr__(self):
        return f"<Role {self.name}>"