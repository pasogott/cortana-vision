✅ Full DB Reset (Delete EVERYTHING & Re-init)

This wipes all OCR + video records and recreates schema.

Inside your host
docker exec -it cortana-api bash

Inside container
python


Then run:

from app.database import Base, engine

print("Dropping all tables…")
Base.metadata.drop_all(bind=engine)

print("Recreating tables…")
Base.metadata.create_all(bind=engine)

print("✅ DB reset complete")


Exit:

exit()
exit
