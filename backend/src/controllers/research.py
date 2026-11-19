from src.services import studies,runs
# Controllers keep endpoint contracts separate from persistence and calculation.
def overview(db): return {'studies':studies.list_studies(db),'runs':runs.list_runs(db)}
def create_study(db,data,user): return studies.create(db,data,user)
def list_rows(db,id): return studies.observations(db,id)
def save_row(db,id,data,user,row_id=None): return studies.save_observation(db,id,data,user,row_id)
def list_candidates(db,id): return studies.candidates(db,id)
def save_candidate(db,id,data,user): return studies.save_candidate(db,id,data,user)
def list_quotas(db,id): return studies.quotas(db,id)
def save_quota(db,id,data,user): return studies.save_quota(db,id,data,user)
def create_run(db,data,user): return runs.create(db,data,user)
def review_run(db,id,data,user): return runs.approve(db,id,data,user)
