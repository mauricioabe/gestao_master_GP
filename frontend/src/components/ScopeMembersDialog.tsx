import {useState} from 'react';
import {AddOutlined,GroupsOutlined,PersonRemoveOutlined} from '@mui/icons-material';
import {Alert,Autocomplete,Box,Button,Chip,Dialog,DialogActions,DialogContent,DialogTitle,IconButton,Skeleton,Stack,TextField,Tooltip,Typography} from '@mui/material';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {api,AssignmentUser,Project,Subproject} from '../api';
import {can,MANAGE_PROJECTS,MANAGE_SUBPROJECTS} from '../auth';
import {errorMessage} from '../logbooks';

export type MemberScope={type:'project'|'subproject';id:number;name:string};
type ScopeMember=AssignmentUser&{added_at:string};

export default function ScopeMembersDialog({initialScope,onClose}:{initialScope?:MemberScope;onClose:()=>void}){
  const client=useQueryClient();
  const [scope,setScope]=useState<MemberScope|null>(initialScope||null);
  const [selected,setSelected]=useState<AssignmentUser|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [removing,setRemoving]=useState<ScopeMember|null>(null);
  const [removeError,setRemoveError]=useState('');
  const projects=useQuery({queryKey:['projects'],queryFn:()=>api.get<Project[]>('/projects').then(r=>r.data),enabled:!initialScope});
  const subprojects=useQuery({queryKey:['subprojects'],queryFn:()=>api.get<Subproject[]>('/subprojects').then(r=>r.data),enabled:!initialScope});
  const scopes:MemberScope[]=[...(projects.data||[]).map(p=>({type:'project' as const,id:p.id,name:`${p.code} · ${p.name}`})),...(subprojects.data||[]).map(s=>({type:'subproject' as const,id:s.id,name:`${s.project_code} / ${s.code} · ${s.name}`}))];
  const path=scope?`/${scope.type==='project'?'projects':'subprojects'}/${scope.id}/members`:'';
  const canManage=scope&&can(scope.type==='project'?MANAGE_PROJECTS:MANAGE_SUBPROJECTS);
  const members=useQuery({queryKey:['scope-members',scope?.type,scope?.id],queryFn:()=>api.get<ScopeMember[]>(path).then(r=>r.data),enabled:!!scope});
  const users=useQuery({queryKey:['user-assignment-options'],queryFn:()=>api.get<AssignmentUser[]>('/users/assignment-options').then(r=>r.data),enabled:!!canManage});
  const choices=(users.data||[]).filter(u=>!members.data?.some(m=>m.id===u.id));
  const refresh=async()=>{
    await client.invalidateQueries({queryKey:['scope-members',scope?.type,scope?.id]});
    await client.invalidateQueries({queryKey:['team-members']});
    await client.invalidateQueries({queryKey:['relator-options']});
  };
  const add=async()=>{
    if(!selected)return;
    setBusy(true);setError('');
    try{await api.post(path,{user_id:selected.id});setSelected(null);await refresh()}
    catch(e){setError(errorMessage(e))}finally{setBusy(false)}
  };
  return <>
    <Dialog open fullWidth maxWidth="md" onClose={()=>!busy&&onClose()}>
      <DialogTitle><Stack direction="row" gap={1} alignItems="center"><GroupsOutlined color="primary"/>Integrantes{scope?` do ${scope.type==='project'?'projeto':'subprojeto'}`:''}</Stack></DialogTitle>
      <DialogContent><Stack spacing={2} mt={1}>
        {!initialScope&&<Autocomplete options={scopes} value={scope} disabled={busy} loading={projects.isLoading||subprojects.isLoading}
          groupBy={s=>s.type==='project'?'Projetos':'Subprojetos'} getOptionLabel={s=>s.name}
          isOptionEqualToValue={(a,b)=>a.id===b.id&&a.type===b.type}
          onChange={(_,value)=>{setScope(value);setSelected(null);setError('')}}
          renderInput={params=><TextField {...params} required label="Projeto ou subprojeto"/>}/>}
        {initialScope&&<Typography fontWeight={800} color="primary.main">{scope?.name}</Typography>}
        {!initialScope&&(projects.isError||subprojects.isError)&&<Alert severity="error">Não foi possível carregar os projetos e subprojetos.</Alert>}
        {error&&<Alert severity="error" onClose={()=>setError('')}>{error}</Alert>}
        {!scope?<Alert severity="info">Selecione o projeto ou subprojeto para consultar e definir seus integrantes.</Alert>:<>
          {canManage&&<Stack direction={{xs:'column',sm:'row'}} gap={1} alignItems={{sm:'flex-start'}}>
            <Autocomplete sx={{flex:1,minWidth:0}} options={choices} value={selected} loading={users.isLoading} disabled={busy||members.isLoading||members.isError}
              getOptionLabel={u=>u.assignment_label} isOptionEqualToValue={(a,b)=>a.id===b.id}
              onChange={(_,value)=>setSelected(value)} noOptionsText="Nenhum outro usuário ativo disponível"
              renderInput={params=><TextField {...params} label="Usuário cadastrado no sistema"/>}/>
            <Button variant="contained" startIcon={<AddOutlined/>} disabled={!selected||busy||members.isError} onClick={add}>{busy?'Salvando...':'Adicionar integrante'}</Button>
          </Stack>}
          {canManage&&users.isError&&<Alert severity="error">Não foi possível carregar os usuários.</Alert>}
          {members.isLoading?<Skeleton variant="rounded" height={150}/>:members.isError?<Alert severity="error">Não foi possível carregar os integrantes deste {scope.type==='project'?'projeto':'subprojeto'}.</Alert>:<>
            <Typography variant="subtitle2">{members.data?.length||0} integrante(s) vinculado(s)</Typography>
            {!members.data?.length&&<Alert severity="info">Nenhum integrante vinculado a este {scope.type==='project'?'projeto':'subprojeto'}.</Alert>}
            <Stack spacing={1}>{members.data?.map(member=><Box key={member.id} sx={{p:1.5,border:'1px solid',borderColor:'divider',borderRadius:2}}>
              <Stack direction="row" alignItems="center" gap={1}>
                <Box flex={1} minWidth={0}><Typography fontWeight={800} sx={{overflowWrap:'anywhere'}}>{member.assignment_label}</Typography>
                  <Typography variant="body2" color="text.secondary">{member.person_type==='MILITAR'?member.name:member.profile_name}</Typography>
                </Box>
                <Chip size="small" label={member.active?'Ativo':'Inativo'} color={member.active?'success':'default'}/>
                {canManage&&<Tooltip title="Remover vínculo"><IconButton aria-label={`Remover vínculo de ${member.display_name}`} disabled={busy} onClick={()=>{setRemoving(member);setRemoveError('')}}><PersonRemoveOutlined/></IconButton></Tooltip>}
              </Stack>
            </Box>)}</Stack>
          </>}
        </>}
      </Stack></DialogContent>
      <DialogActions><Button disabled={busy} onClick={onClose}>Fechar</Button></DialogActions>
    </Dialog>
    <Dialog open={!!removing} fullWidth maxWidth="xs" onClose={()=>!busy&&setRemoving(null)}>
      <DialogTitle>Remover vínculo de integrante?</DialogTitle>
      <DialogContent>{removeError&&<Alert severity="error" sx={{mb:2}}>{removeError}</Alert>}Remover {removing?.display_name} da equipe de {scope?.name}?</DialogContent>
      <DialogActions><Button disabled={busy} onClick={()=>setRemoving(null)}>Cancelar</Button>
        <Button color="error" variant="contained" disabled={busy} onClick={async()=>{
          if(!removing)return;setBusy(true);setRemoveError('');
          try{await api.delete(`${path}/${removing.id}`);setRemoving(null);await refresh()}
          catch(e){setRemoveError(errorMessage(e))}finally{setBusy(false)}
        }}>{busy?'Removendo...':'Remover vínculo'}</Button>
      </DialogActions>
    </Dialog>
  </>;
}
