import {store} from '../../stores/research.js';
import {table} from './table.js';
import {status} from './status.js';
import {esc} from '../../utils/format.js';
export function runList(){return table(['编号 / 运行','状态','数据版本','冻结输入','复核'],store.runs.map(r=>[{html:`<a href="#results/${r.id}">#${r.id} ${esc(r.name)}</a>`},{html:status(r.status)+(r.status==='completed'&&!r.valid?' <span class="status stale">已失效</span>':'')},`v${r.data_version}`,r.snapshot.readings.length+'条 · '+r.checksum.slice(0,12),r.review?'已复核':'待负责人复核']));}
