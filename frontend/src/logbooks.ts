import {api,AssignmentUser} from './api';

export type Member={id:number;rank:string;full_name:string;war_name:string;active:boolean;member_active:boolean;display_name:string;user_id:number|null;user:AssignmentUser|null};
export type Attachment={id:number;file_name:string;mime_type:string;file_size:number;description:string};
export type Occurrence={id:number;logbook_id:number;title:string;content:string;type:string;references_text:string;event_date:string;created_at:string;updated_at:string;created_by:number;author_name:string;subject_principal:string;logbook_status:string;attachments:Attachment[]};
export type BookLink={id:number;source_logbook_id:number;target_logbook_id:number;source_title:string;target_title:string;link_type:string;observations:string};
export type Book={id:number;subject_principal:string;description:string;scope:string;status:string;registration_date:string;closure_date:string|null;responsible_id:number;responsible:Member;relator_ids:number[];relators:Member[];tags:string;project_ids:number[];subproject_ids:number[];projects:{id:number;code:string;name:string}[];subprojects:{id:number;code:string;name:string;project_id:number}[];item_count:number;last_event_date:string|null;items:Occurrence[];links:BookLink[]};
export type BookInput=Pick<Book,'subject_principal'|'description'|'status'|'registration_date'|'closure_date'|'relator_ids'|'tags'|'project_ids'|'subproject_ids'>;
export const statuses:Record<string,{label:string;color:'primary'|'warning'|'success'|'error'}>={aberto:{label:'Aberto',color:'primary'},aguardando_validacao:{label:'Apreciação',color:'warning'},fechado:{label:'Fechado',color:'success'},cancelado:{label:'Cancelado',color:'error'}};
export const types:Record<string,{label:string;color:string}>={nota:{label:'Nota geral / Observação',color:'#4e73df'},decisao:{label:'Decisão / Aprovação',color:'#28a745'},pendencia:{label:'Pendência / Ação necessária',color:'#ffc107'},risco:{label:'Risco / Alerta crítico',color:'#dc3545'},evidencia:{label:'Evidência / Fato comprovado',color:'#17a2b8'}};
export const linkTypes:Record<string,string>={relacionado:'Relacionado',depende_de:'Depende de',bloqueia:'Bloqueia',originado_de:'Originado de',subassunto_de:'Subassunto de'};
export const scopes:Record<string,string>={global:'Global',projeto:'Projeto',multi_projeto:'Multi-projeto'};
export const terminal=(status:string)=>['fechado','cancelado'].includes(status);
export const day=(value:string|null)=>value?new Intl.DateTimeFormat('pt-BR',{timeZone:'UTC'}).format(new Date(`${value}T00:00:00Z`)):'—';
export const dateTime=(value:string)=>new Intl.DateTimeFormat('pt-BR',{dateStyle:'short',timeStyle:'short',timeZone:'America/Sao_Paulo'}).format(new Date(value));
export function localDateTime(value=new Date().toISOString()){
  const parts=new Intl.DateTimeFormat('sv-SE',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(value));
  const part=(key:string)=>parts.find(p=>p.type===key)?.value||'';
  return `${part('year')}-${part('month')}-${part('day')}T${part('hour')}:${part('minute')}`;
}
export const errorMessage=(error:any)=>typeof error?.response?.data?.detail==='string'?error.response.data.detail:'Não foi possível concluir a operação. Confira os campos e tente novamente.';
export async function downloadAttachment(attachment:Attachment){
  const response=await api.get(`/logbook-attachments/${attachment.id}/download`,{responseType:'blob'});
  const url=URL.createObjectURL(response.data);const anchor=document.createElement('a');anchor.href=url;anchor.download=attachment.file_name;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
