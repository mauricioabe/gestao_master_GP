export const VIEW_PROJECTS='VIEW_PROJECTS';
export const MANAGE_PROJECTS='MANAGE_PROJECTS';
export const MANAGE_SUBPROJECTS='MANAGE_SUBPROJECTS';
export const MANAGE_SCHEDULE='MANAGE_SCHEDULE';
export const MANAGE_DOCUMENTS='MANAGE_DOCUMENTS';
export const MANAGE_USERS='MANAGE_USERS';

export const roleNames:Record<string,string>={
  GESTOR_PROGRAMA:'Gestor do programa',
  GERENTE_PROJETOS:'Gerente de projetos',
  COORDENADOR_PROJETOS:'Coordenador de Projetos',
  CHEFE_ASS_PJT:'Chefe Ass Pjt',
  ANALISTA_PROJETOS:'Analista de projetos',
  ANALISTA_LICITACOES:'Analista de licitações',
  ANALISTA_CONTRATOS:'Analista de contratos',
  AUDITOR_INTERNO:'Auditor interno',
  EQUIPE_PROJETO:'Equipe de projeto',
  SUPERVISOR_PROJETO:'Supervisor do projeto',
};

export function currentPermissions():string[]{
  try{const value=JSON.parse(localStorage.getItem('permissions')||'[]');return Array.isArray(value)?value:[]}catch{return []}
}
export const can=(permission:string)=>currentPermissions().includes(permission);
export const isAuthenticated=()=>Boolean(localStorage.getItem('token'));
export function clearSession(){['token','role','userName','permissions'].forEach(key=>localStorage.removeItem(key))}
