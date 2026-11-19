import {DOMAIN} from '../constants/domain.js';
import {store} from '../stores/research.js';
import {esc} from '../utils/format.js';
import {runList} from '../components/common/run-list.js';
import {table} from '../components/common/table.js';
export function render(){return `<div class="eyebrow">FIELD NOTES / ${DOMAIN.direction}</div><section class="hero"><div><h1>${DOMAIN.title}</h1><p class="lead">${DOMAIN.scenario}</p><a class="button" href="#analysis">发起新的研究 →</a></div><aside><span class="folio">${DOMAIN.id.slice(-2)}</span><p>${DOMAIN.algorithm}</p><small>精确有理计算 · 真实Python计算 · 输入快照可追溯</small></aside></section><section class="strip"><span>${store.studies.length} 个${DOMAIN.study_label}</span><span>${store.studies.reduce((n,s)=>n+s.row_count,0)} 条${DOMAIN.row_label}</span><span>${store.studies.reduce((n,s)=>n+s.candidate_count,0)} 组可补测组合</span><span>${store.runs.length} 次计算记录</span></section><h2>研究进度 <small>从来源到复核的同一条链路</small></h2>${runList()}<h2>来源索引</h2>${table([DOMAIN.study_label,'来源文件','读数','候选','限额','数据版本'],store.studies.map(s=>[s.name,s.source_filename,s.row_count,s.candidate_count,s.quota_count,'v'+s.data_version]))}`;}
export function bind(){}
