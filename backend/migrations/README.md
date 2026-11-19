Schema v2 is defined by the SQLAlchemy models and created at startup via Base.metadata.create_all. For this local small application no destructive migration is run. Back up named db-data before modifying schemas.

v1 → v2：研究新增 data_version（源数据版本，改录即递增）；运行新增 data_version（排队时冻结的版本，用于判定补测单是否失效）；新增 candidates（可补测组合）与 quotas（每人每台仪器限额）两表；运行状态新增 stale（计算完成前源数据已更新，补测单作废）。
