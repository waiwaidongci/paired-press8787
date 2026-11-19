import {DOMAIN} from '../constants/domain.js';
import {store,load,currentStudy} from '../stores/research.js';
import {runs} from '../api/research.js';
import {studySelect} from '../components/common/study-select.js';
import {runList} from '../components/common/run-list.js';
import {bindForm} from '../hooks/forms.js';
import {esc} from '../utils/format.js';
export function render(){const writable=localStorage.getItem('research-role')!=='viewer';const s=currentStudy();
 const summary=s?`<p>当前选择：读数 ${s.row_count} 条 · 候选组合 ${s.candidate_count} / ${DOMAIN.max_candidates} 组 · 限额 ${s.quota_count} 项 · 数据版本 v${s.data_version}</p>${s.candidate_count>DOMAIN.max_candidates?`<p class="error">候选组合 ${s.candidate_count} 组超过上限 ${DOMAIN.max_candidates} 组，排队将被拒绝；请先到来源页精简。</p>`:''}`:'<p>请先在来源页创建研究并登记读数。</p>';
 return `<div class="eyebrow">02 / METHOD WORKSHEET</div><h1>${DOMAIN.field_label}</h1><p class="lead">${DOMAIN.algorithm}</p><div class="method-note">${DOMAIN.note}</div>${writable?`<form id="run-form" class="worksheet">${studySelect()}<label>本次研究名称<input name="name" required minlength="2" value="${esc(DOMAIN.names[0])} · 核算"></label>${summary}<p>提交时在同一事务内冻结全部读数、可补测组合与限额，生成 SHA256 与数据版本号；冻结期间并发改录被串行化。后台 worker 独立执行。</p><button type="submit">冻结输入并排队计算 →</button></form>`:'<p class="method-note">观察员可阅读研究记录，分析师与负责人可以发起计算。</p>'}<h2>计算记录</h2>${runList()}`;}
export function bind(refresh){bindForm('run-form',async data=>{const r=await runs.create({study_id:+data.study_id,name:data.name,parameters:{}});store.runId=r.id;await load();location.hash='results/'+r.id;});const sel=document.getElementById('study-select');if(sel)sel.onchange=()=>{store.studyId=+sel.value;refresh();};}
