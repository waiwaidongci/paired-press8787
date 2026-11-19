import math
from src.config.domain import DOMAIN

FIELDS=DOMAIN['fields']
TEXT_KEYS=[k for k,_,kind in FIELDS if kind=='text']
LABELS={k:label for k,label,_ in FIELDS}
MAX_CANDIDATES=DOMAIN['max_candidates']

def _text(key,value):
    if not isinstance(value,str): raise ValueError(LABELS[key]+'必须为文本')
    value=value.strip()
    if not 1<=len(value)<=40: raise ValueError(LABELS[key]+'须为1到40个字符')
    return value

def validate_values(values):
    expected={f[0] for f in FIELDS}
    if not isinstance(values,dict) or set(values)!=expected: raise ValueError('字段必须为 '+', '.join(expected))
    out={}
    for key,label,kind in FIELDS:
        v=values[key]
        if kind=='text': out[key]=_text(key,v)
        else:
            if isinstance(v,bool): raise ValueError(label+'必须是数值')
            v=float(v)
            if not math.isfinite(v) or abs(v)>1e9: raise ValueError(label+'必须为有限业务数值')
            if v<0: raise ValueError(label+'不得为负')
            out[key]=v
    return out

def validate_combo(data):
    if not isinstance(data,dict): raise ValueError('组合必须为对象')
    return {k:_text(k,data.get(k)) for k in TEXT_KEYS}

def validate_quota(data):
    if not isinstance(data,dict): raise ValueError('限额必须为对象')
    out={'operator':_text('operator',data.get('operator')),'instrument':_text('instrument',data.get('instrument'))}
    v=data.get('max_count')
    if isinstance(v,bool) or not isinstance(v,(int,float)) or int(v)!=v or not 0<=int(v)<=MAX_CANDIDATES: raise ValueError(f'限额必须为0到{MAX_CANDIDATES}的整数')
    out['max_count']=int(v)
    return out

def validate_parameters(params):
    if not isinstance(params,dict) or params: raise ValueError('本方法没有分析参数，请提交空参数对象')
    return {}
