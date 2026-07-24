# Importing the models here registers them on Base.metadata,
# so `import app.models` is enough for create_all() to see every table.
from app.models.user import User
from app.models.profile import Profile
from app.models.outfit import Outfit
from app.models.swipe_log import SwipeLog

__all__ = ["User", "Profile", "Outfit", "SwipeLog"]
