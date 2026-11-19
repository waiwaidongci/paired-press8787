import {studies,runs} from '../api/research.js';
export const store={studies:[],runs:[],studyId:0,runId:0,rows:[],candidates:[],quotas:[]};
export async function load(){[store.studies,store.runs]=await Promise.all([studies.list(),runs.list()]);if(!store.studyId)store.studyId=store.studies[0]?.id||0;}
export async function loadRows(){if(!store.studyId){store.rows=[];store.candidates=[];store.quotas=[];return;}[store.rows,store.candidates,store.quotas]=await Promise.all([studies.rows(store.studyId),studies.candidates(store.studyId),studies.quotas(store.studyId)]);}
export const currentStudy=()=>store.studies.find(s=>s.id===store.studyId);
