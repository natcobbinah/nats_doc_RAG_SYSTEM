from app.config import db
from app.models import Role, RoleName
from app.logging_utils import log, LogLevel

def seed_roles():
    log(type=LogLevel.INFO, message=f"Seeding default roles into the database")
    
    """Ensure default roles exist in the database."""
    default_roles = [
        (RoleName.USER, "Regular user with limited access"),
        (RoleName.ADMIN, "Administrator role with full access"),
    ]

    for name, desc in default_roles:
        role = Role.query.filter_by(name=name).first()
        if not role:
            db.session.add(Role(name=name, description=desc))

    db.session.commit()