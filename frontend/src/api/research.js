import {request,post} from './client.js';
export const studies={list:()=>request('/studies'),create:x=>post('/studies',x),rows:id=>request(`/studies/${id}/observations`),save:(id,x,row)=>row?request(`/studies/${id}/observations/${row}`,{method:'PUT',body:JSON.stringify(x)}):post(`/studies/${id}/observations`,x),remove:(id,row)=>request(`/studies/${id}/observations/${row}`,{method:'DELETE'}),
 candidates:id=>request(`/studies/${id}/candidates`),addCandidate:(id,x)=>post(`/studies/${id}/candidates`,x),removeCandidate:(id,cid)=>request(`/studies/${id}/candidates/${cid}`,{method:'DELETE'}),
 quotas:id=>request(`/studies/${id}/quotas`),saveQuota:(id,x)=>post(`/studies/${id}/quotas`,x),removeQuota:(id,qid)=>request(`/studies/${id}/quotas/${qid}`,{method:'DELETE'})};
export const runs={list:()=>request('/runs'),create:x=>post('/runs',x),get:id=>request(`/runs/${id}`),review:(id,note)=>post(`/runs/${id}/review`,{note}),export:id=>request(`/runs/${id}/export`)};
