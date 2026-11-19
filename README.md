# 栖木印刷换班色差归因簿

试印换班后色差变大，分不清是纸样、测量员还是仪器的影响。登记同一工艺的复测读数、可补测组合与每人每台仪器限额，按三项加性效应（纸样＋测量员＋仪器，无交互）精确判定能辨清的两两差异，并在限额内给出补测单。原生 HTML/CSS/JavaScript 多模块工作席，所有计算由 Python 完成。

## 模拟业务
栖木研究协作组，12名分析师与业务人员，日常使用 `shift-chroma-202611-1.csv` 手工抄表。当前三个痛点：观测与口径不可追溯、补测安排凭经验、旧补测单与最新数据脱节。上游提供独立合成业务观测；本应用接管数据登记、可辨性判定、补测规划与输入冻结；下游负责人形成复核意见，观察员获取复核后的CSV。

核心业务实体：PressStudy / ReReading / CandidateCombo / Quota / PlanRun / Review。源码 model/schema/service/controller/route 与前端 api/store/pages 完成链路，不依赖浏览器本地假数据。

## 功能与方法
- 试印研究与复测读数（纸样×测量员×仪器×ΔE）、可补测组合、每人每台仪器限额的录入/编辑/删除；重名记录与非法数值明确拒绝。
- 三项加性模型的可估性判定：两两差异可辨当且仅当对比向量落在设计矩阵行空间内，全程有理数精确计算；可辨差异给出最小二乘估计与标准误。
- 限额内补测规划：在不超过24组候选中精确搜索子集，先最大化可辨的测量员/仪器两两差异数，相同则取测量次数更少者，每个组合至多安排一次；未登记限额的组合按0处理不可安排。搜索在两个大素数有限域上独立进行并互相印证（不一致时回退全程有理数搜索），最终方案的可辨性一律经有理数复核。
- 每次运行在同一事务内冻结读数、候选组合、限额与数据版本，生成SHA256。Redis任务由独立worker计算，写DB与共享产物卷。
- 允许并发改录；源数据每次改动递增数据版本，旧补测单立即失效；worker完成前复核版本，计算晚到也只能标记stale，不能重新发出旧单。失效单不能复核、不能导出。
- 负责人复核不可覆盖；审计记录登录、数据改动、排队、复核与导出；240请求/分钟限流、全局可恢复错误。

## 快速启动
```bash
cp .env.example .env
docker compose up -d --build
docker compose exec -T backend python -m scripts.seed_demo
```
访问 http://localhost:18242 ，API http://localhost:19242/docs 。数据库映射 17742。无需Node构建。可以从中文和带空格目录启动。清理 `docker compose down -v --remove-orphans` 会删除本题演示数据卷。

|角色|账号|密码|权限与典型动作|
|---|---|---|---|
|admin 负责人|admin@demo.local|Research2026!|全部读写、批准复核、下载|
|analyst 分析师|analyst@demo.local|Research2026!|数据修改、创建任务、读取结果及下载；不能复核|
|viewer 观察员|viewer@demo.local|Research2026!|只读；仅可导出已复核结果|

## 一天的工作剧本
1. 09:00 admin登录，查“栖木·换班归因·米白纸”。
2. 09:10 analyst核对 `shift-chroma-202611-1.csv` 的seed记录。
3. 09:15 来源录入页检查复测读数、可补测组合与限额，必要时编辑；注意每次保存都会递增数据版本。
4. 09:20 分析执行页确认冻结范围（读数/候选/限额/版本），命名本轮研究。
5. 09:21 冻结输入并排队，worker实算，结果页自动刷新。
6. 09:25 阅读两两差异可辨性、限额内补测单、限额占用与SHA256；发现失败先修数据重跑。
7. 09:35 admin打开业务复核，写明限制与下一步动作，归档后不可覆盖。
8. 09:40 viewer读取复核意见并下载CSV，在操作留痕页核对下载事件。
9. 任意时刻改录源数据后，旧补测单立即失效；请重新排队获取当前数据的补测单。

## 技术与目录
|部分|实现|
|---|---|
|前端|原生ES modules、HTML/CSS、Nginx1.27，无前端框架|
|API|Python3.11、FastAPI0.115、SQLAlchemy2、JWT、PBKDF2密码|
|计算|NumPy2.2（仅最小二乘数值）、Fraction有理数精确判定、双素数有限域加速搜索|
|数据库|PostgreSQL16|
|任务|Redis7持久队列，Python独立worker，心跳healthcheck|

`frontend/src/`分api、stores、types、components/common、hooks、pages、router、utils、constants；`backend/src/`分config、models、schemas、services、controllers、routes、middlewares、utils、constants；`backend/scripts/seed_demo.py`自然键插入、重复不覆盖修改；`backend/migrations/README.md`说明schema版本；`backend/tests/`为pytest核对（算法oracle与端到端流程）。

环境变量 `.env.example`：COMPOSE_PROJECT_NAME、FRONTEND_PORT、BACKEND_PORT、DB_PORT、DB_PASSWORD、JWT_SECRET、SEED_DEMO。开发时在本地venv安装backend/requirements.txt，设置DATABASE_URL、REDIS_URL、JWT_SECRET再运行uvicorn；前端开发经Nginx代理 `/api/` 到不带前缀的API。

共享枚举：角色admin/analyst/viewer和队列queued/running/completed/failed/stale；后端`src/constants/enums.py`、认证与worker使用相同值；前端`src/types/enums.js`、状态与角色界面使用相同值。Google Fonts：Noto Serif SC + IBM Plex Mono；断网使用serif/monospace回退。

## 算法输入、失败态与复现
输入为冻结的复测读数、可补测组合、限额与数据版本，输出核心数值、两两差异可辨性、补测单、限额占用与解释；本方法无分析参数，提交非空参数明确拒绝。空批次拒绝；不完整字段/非有限数/负色差拒绝；候选组合超过24组拒绝排队。补测规划是NP难的子集搜索，24组上限保证有界；搜索先按单兵增益排序，两阶段（最多可辨差异→最少测量次数）精确求解，双素数有限域互证、有理数复核最终方案，输入相同可复现。独立oracle：缺格设计单项补测不可辨、成对补测合起来可辨；连通设计全部可辨且补测单为空；同增益取少测；限额为0的组合不可安排；估计值与手算最小二乘一致。

已知边界：小型本地研究应用，使用合成数据，不含企业SSO与外发邮件；补测单由人工复核，不自动执行业务决策；单worker恢复queued/running任务，数据库与Redis间未采用分布式事务； adversarial 候选分布下精确搜索最坏约数秒级（24组上限内）。以当前测试目录TESTING.md记录实际验证结果。

MIT License。
