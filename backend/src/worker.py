import os
from pathlib import Path
from redis import Redis
from sqlalchemy import select
from src.config.database import Session
from src.models.run import Run
from src.models import user,study,observation,candidate,quota,review,audit
from src.services.execute import execute
redis=Redis.from_url(os.environ['REDIS_URL'])
Path('/app/artifacts').mkdir(exist_ok=True)
# Recover jobs interrupted after dequeue. A project runs exactly one worker.
with Session() as db:
    pending=list(db.scalars(select(Run).where(Run.status.in_(['queued','running']))))
    for run in pending: redis.rpush('analysis-queue',run.id)
while True:
    Path('/tmp/worker-heartbeat').touch()
    job=redis.blpop('analysis-queue',timeout=2)
    if not job: continue
    with Session() as db: execute(db,int(job[1]))
