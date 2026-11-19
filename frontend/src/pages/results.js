import {store} from '../stores/research.js';
import {runs} from '../api/research.js';
import {esc,fmt} from '../utils/format.js';
import {table} from '../components/common/table.js';
import {status} from '../components/common/status.js';
import {runList} from '../components/common/run-list.js';
import {download} from '../utils/download.js';
function sections(r){const res=r.result;return `<section class="result-intro"><strong>${esc(res.interpretation)}</strong><p>${esc(res.caveat)}</p></section><h2>核心数值</h2>${table(['业务指标','计算值'],Object.entries(res.metrics).map(([k,v])=>[k,fmt(v)]))}<h2>两两差异可辨性 <small>三项加性模型下的精确判定</small></h2>${table(res.pairs.columns,res.pairs.rows)}<h2>补测单 <small>限额内 ${res.plan.rows.length} 次补测 · 每个组合至多一次</small></h2>${res.plan.rows.length?table(res.plan.columns,res.plan.rows):'<p class="method-note">补测单为空：当前数据已可辨全部目标差异，或限额内没有能改善可辨性的组合。</p>'}<h2>限额占用</h2>${table(res.quotas.columns,res.quotas.rows)}<h2>${esc(res.table_title||'冻结读数明细')}</h2>${table(res.readings.columns,res.readings.rows)}`;}
export async function render(id){if(!id)return `<h1>计算结果与补测单</h1><p>选择一次运行查看冻结输入、可辨性判定与限额内补测单。</p>${runList()}`;
 const r=await runs.get(id);store.runId=r.id;
 const invalid=r.status==='completed'&&!r.valid;
 const head=`<div class="eyebrow">03 / RESULTS ARCHIVE · RUN ${r.id}</div><h1>${esc(r.name)} ${status(r.status)}${invalid?' <span class="status stale">已失效</span>':''}</h1><div class="checksum">INPUT SHA256 ${r.checksum}</div><p>冻结数据版本 v${r.data_version} · 当前版本 v${r.current_data_version} · 读数 ${r.snapshot.readings.length} 条 · 候选 ${r.snapshot.candidates.length} 组 · 限额 ${r.snapshot.quotas.length} 项 · ${esc(r.created_at)} · ${r.review?'负责人已复核':'尚未复核'}</p>`;
 if(r.status==='failed')return head+`<div class="error">计算失败：${esc(r.error)}。请到来源页修复数据，然后创建新运行。</div>`;
 if(r.status==='stale')return head+`<div class="error">计算完成前源数据已更新（v${r.data_version} → v${r.current_data_version}），该补测单作废，不能复核或导出。请基于当前数据重新排队。</div><details><summary>查看作废的历史计算（仅供追溯）</summary>${sections(r)}</details>`;
 if(!r.result)return head+'<p class="method-note">任务正在队列中。此页每2秒更新，结果写入数据库后展示。</p>';
 if(invalid)return head+`<div class="error">源数据已更新到 v${r.current_data_version}，这份 v${r.data_version} 的补测单已失效，不能复核或导出。请重新排队获取当前数据的补测单。</div><details><summary>查看失效的历史补测单（仅供追溯）</summary>${sections(r)}</details>`;
 return head+sections(r)+`<div class="toolbar"><button id="export">下载核算 CSV</button><a class="button secondary" href="#review/${r.id}">打开业务复核 →</a></div><details><summary>本次冻结的参数与源记录</summary><pre>${esc(JSON.stringify({parameters:r.parameters,snapshot:r.snapshot},null,2))}</pre></details>`;}
export function bind(){const button=document.getElementById('export');if(button)button.onclick=async()=>{try{download(await runs.export(store.runId),'research-'+store.runId+'.csv');}catch(e){document.getElementById('notice').textContent=e.message;}};}
