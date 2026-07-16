from sqlalchemy import create_engine

from app.config.settings import settings

engine_kwargs = {"pool_pre_ping": True}
if "sqlite" not in settings.database_url:
    engine_kwargs.update({"pool_size": 10, "max_overflow": 20})
else:
    engine_kwargs.update({"connect_args": {"check_same_thread": False}})

engine = create_engine(settings.database_url, **engine_kwargs)
