from app.database import Base, engine
from app.models import Video, Frame

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("✅ Done.")
