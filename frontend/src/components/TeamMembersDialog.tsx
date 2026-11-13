import {useState} from 'react';
import {Alert,Autocomplete,Button,Dialog,DialogActions,DialogContent,DialogTitle,FormControlLabel,MenuItem,Stack,Switch,TextField} from '@mui/material';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {api,AssignmentUser} from '../api';
import {Member,errorMessage} from '../logbooks';

export default function TeamMembersDialog({onClose}:{onClose:()=>void}){
  const client=useQueryClient();
  const [selected,setSelected]=useState('');
  const [userId,setUserId]=useState<number|null>(null);
  const [active,setActive]=useState(true);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const members=useQuery({queryKey:['team-members'],queryFn:()=>api.get<Member[]>('/team-members').then(r=>r.data)});
  const users=useQuery({queryKey:['user-assignment-options'],queryFn:()=>api.get<AssignmentUser[]>('/users/assignment-options').then(r=>r.data)});
  const member=members.data?.find(m=>m.id===Number(selected));
  const options=[...(users.data||[])];
  if(member?.user&&!options.some(u=>u.id===member.user_id))options.push(member.user);
  const user=options.find(u=>u.id===userId)||null;
  const save=async()=>{
    setError('');setBusy(true);
    try{
      const body={...(userId?{user_id:userId}:{}),active};
      if(selected)await api.put(`/team-members/${selected}`,body);
      else await api.post('/team-members',body);
      await client.invalidateQueries({queryKey:['team-members']});
      await client.invalidateQueries({queryKey:['logbooks']});
      onClose();
    }catch(e){setError(errorMessage(e))}finally{setBusy(false)}
  };
  return <Dialog open fullWidth maxWidth="sm" onClose={()=>!busy&&onClose()}>
    <DialogTitle>Integrantes responsáveis</DialogTitle>
    <DialogContent><Stack spacing={2} mt={1}>
      {error&&<Alert severity="error">{error}</Alert>}
      {(members.isError||users.isError)&&<Alert severity="error">Não foi possível carregar os integrantes e usuários.</Alert>}
      <TextField select label="Integrante" value={selected} disabled={busy} onChange={e=>{
        setSelected(e.target.value);setError('');
        const chosen=members.data?.find(m=>m.id===Number(e.target.value));
        setUserId(chosen?.user_id||null);setActive(chosen?.member_active??true);
      }}>
        <MenuItem value="">Adicionar usuário cadastrado</MenuItem>
        {members.data?.map(m=><MenuItem key={m.id} value={m.id}>{m.display_name}{!m.active?' (inativo)':''}</MenuItem>)}
      </TextField>
      <Autocomplete options={options} value={user} loading={users.isLoading} disabled={busy||Boolean(member?.user_id)}
        getOptionLabel={u=>u.assignment_label} isOptionEqualToValue={(a,b)=>a.id===b.id}
        getOptionDisabled={u=>!u.active||Boolean(members.data?.some(m=>m.user_id===u.id&&m.id!==member?.id))}
        onChange={(_,value)=>setUserId(value?.id||null)} noOptionsText="Nenhum usuário ativo cadastrado"
        renderInput={params=><TextField {...params} required={!selected} label="Usuário cadastrado no sistema"/>}/>
      {member&&!member.user_id&&!user&&<Alert severity="info">Integrante anterior ao vínculo de usuários. Selecione um usuário para associá-lo; o histórico será preservado.</Alert>}
      {user&&!user.active&&<Alert severity="warning">Usuário inativo. O vínculo existente será preservado.</Alert>}
      <TextField label="Posto / Graduação" value={user?.rank||(!user?member?.rank:'')||''} InputProps={{readOnly:true}}/>
      <TextField label="Nome completo" value={user?.name||member?.full_name||''} InputProps={{readOnly:true}}/>
      <TextField label="Nome de guerra" value={user?.war_name||(!user?member?.war_name:'')||''} InputProps={{readOnly:true}}/>
      {user&&<TextField label="Perfil de acesso" value={user.profile_name} InputProps={{readOnly:true}}/>}
      <FormControlLabel label="Integrante ativo" control={<Switch checked={active} disabled={busy} onChange={e=>setActive(e.target.checked)}/>}/>
    </Stack></DialogContent>
    <DialogActions><Button disabled={busy} onClick={onClose}>Fechar</Button>
      <Button disabled={busy||members.isLoading||users.isLoading||members.isError||users.isError||(!selected&&!userId)} variant="contained" onClick={save}>{busy?'Salvando...':'Salvar integrante'}</Button>
    </DialogActions>
  </Dialog>;
}
