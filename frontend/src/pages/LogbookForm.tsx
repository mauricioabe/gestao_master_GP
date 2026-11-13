import {useRef,useState} from 'react';
import {Alert,Autocomplete,Box,Button,Card,CardContent,Chip,MenuItem,Skeleton,Stack,TextField,Typography} from '@mui/material';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {Link,useNavigate,useParams,useSearchParams} from 'react-router-dom';
import {api,Project,Subproject} from '../api';
import {Book,BookInput,Member,statuses,terminal,localDateTime,errorMessage} from '../logbooks';
import {ConfirmDialog} from '../components/LogbookShared';
import ScopeMembersDialog from '../components/ScopeMembersDialog';

export default function LogbookForm(){
  const {id}=useParams();const [params]=useSearchParams();const sub=Number(params.get('subprojeto'))||undefined;
  const book=useQuery({queryKey:['logbooks','detail',id],queryFn:()=>api.get<Book>(`/logbooks/${id}`).then(r=>r.data),enabled:!!id});
  const projects=useQuery({queryKey:['projects'],queryFn:()=>api.get<Project[]>('/projects').then(r=>r.data)});
  const subs=useQuery({queryKey:['subprojects'],queryFn:()=>api.get<Subproject[]>('/subprojects').then(r=>r.data)});
  if((id&&book.isLoading)||projects.isLoading||subs.isLoading)return <Skeleton variant="rounded" height={500}/>;
  if((id&&(book.isError||!book.data))||projects.isError||subs.isError)return <Alert severity="error">Não foi possível carregar os dados do formulário.</Alert>;
  if(book.data&&terminal(book.data.status))return <Alert severity="info">Este assunto está encerrado e disponível somente para consulta. <Link to={`/diarios/${id}`}>Abrir histórico</Link></Alert>;
  return <Editor key={id||'new'} book={book.data} projects={projects.data||[]} subs={subs.data||[]} contextSub={sub}/>;
}

function Editor({book,projects,subs,contextSub}:{book?:Book;projects:Project[];subs:Subproject[];contextSub?:number}){
  const navigate=useNavigate();const client=useQueryClient();const [error,setError]=useState('');const [busy,setBusy]=useState(false);const [deleting,setDeleting]=useState(false);const [memberDialog,setMemberDialog]=useState(false);
  const [submitted,setSubmitted]=useState(false);
  const [incompleteDate,setIncompleteDate]=useState('');
  const relatorsField=useRef<HTMLDivElement>(null);
  const context=contextSub?`?subprojeto=${contextSub}`:'';const back=book?`/diarios/${book.id}${context}`:contextSub?`/subprojetos/${contextSub}/diario`:'/diarios';
  const [form,setForm]=useState<BookInput>(book?{subject_principal:book.subject_principal,description:book.description,status:book.status,registration_date:book.registration_date,closure_date:book.closure_date,relator_ids:book.relator_ids.length?book.relator_ids:[book.responsible_id],tags:book.tags,project_ids:book.project_ids,subproject_ids:book.subproject_ids}:{subject_principal:'',description:'',status:'aberto',registration_date:localDateTime().slice(0,10),closure_date:null,relator_ids:[],tags:'',project_ids:[],subproject_ids:contextSub?[contextSub]:[]});
  const projectOptions=[...projects,...(book?.projects.filter(p=>!projects.some(x=>x.id===p.id))||[])];
  const subOptions=[...subs,...(book?.subprojects.filter(s=>!subs.some(x=>x.id===s.id))||[])];
  const effective=new Set([...form.project_ids,...subOptions.filter(s=>form.subproject_ids.includes(s.id)).map(s=>s.project_id)]);
  const memberFilters=new URLSearchParams();
  [...new Set(form.project_ids)].sort((a,b)=>a-b).forEach(id=>memberFilters.append('project_ids',String(id)));
  [...new Set(form.subproject_ids)].sort((a,b)=>a-b).forEach(id=>memberFilters.append('subproject_ids',String(id)));
  const hasMemberScope=memberFilters.size>0;
  const relatorOptions=useQuery({queryKey:['relator-options',memberFilters.toString()],queryFn:()=>api.get<Member[]>('/logbooks/relator-options',{params:memberFilters}).then(r=>r.data)});
  const errors={
    subject:!form.subject_principal.trim()?'Informe o assunto principal.':'',
    registration:!form.registration_date?'Informe a data de registro.':'',
    relators:!form.relator_ids.length?'Selecione pelo menos um relator para salvar o diário.':'',
    closure:form.status==='fechado'&&!form.closure_date?'Informe a data de fim para fechar o diário.':form.closure_date&&form.closure_date<form.registration_date?'A data de fim não pode anteceder a data de registro.':'',
  };
  const sameScope=!!book&&JSON.stringify([...form.project_ids].sort())===JSON.stringify([...book.project_ids].sort())&&JSON.stringify([...form.subproject_ids].sort())===JSON.stringify([...book.subproject_ids].sort());
  const selectableRelators=[...(relatorOptions.data||[])];
  if(book&&sameScope)for(const member of book.relators)if(!selectableRelators.some(m=>m.id===member.id))selectableRelators.push(member);
  const selectedRelators=selectableRelators.filter(m=>form.relator_ids.includes(m.id));
  const save=async(e:React.FormEvent<HTMLFormElement>)=>{
    e.preventDefault();if(busy)return;setSubmitted(true);setError('');setIncompleteDate('');
    const partialDate=Array.from(e.currentTarget.querySelectorAll<HTMLInputElement>('input[type="date"]')).find(input=>input.validity.badInput);
    if(partialDate){setIncompleteDate(partialDate.name);setError('Complete a data informada ou limpe o campo de data de fim, caso não se aplique.');partialDate.focus();return}
    const invalid=Object.values(errors).find(Boolean);
    if(invalid){
      setError(invalid);
      if(invalid===errors.relators){
        relatorsField.current?.scrollIntoView({behavior:'smooth',block:'center'});
        relatorsField.current?.querySelector<HTMLElement>('[role="combobox"]')?.focus();
      }
      return;
    }
    setBusy(true);
    try{const result=book?await api.put<Book>(`/logbooks/${book.id}`,form):await api.post<Book>('/logbooks',form);await client.invalidateQueries({queryKey:['logbooks']});await client.invalidateQueries({queryKey:['logbook-timeline']});navigate(`/diarios/${result.data.id}${context}`)}catch(e){setError(errorMessage(e))}finally{setBusy(false)}
  };
  return <Box component="form" noValidate onSubmit={save}><Stack spacing={3}><Typography variant="h4">{book?'Editar assunto':'Novo assunto'} · Diário de Bordo</Typography>{error&&<Alert severity="error">{error}</Alert>}<Card><CardContent><Typography variant="h6" mb={2}>Informações do assunto</Typography><Stack spacing={2.5}><TextField error={submitted&&!!errors.subject} helperText={submitted?errors.subject:undefined} required label="Assunto principal" value={form.subject_principal} inputProps={{maxLength:255}} onChange={e=>setForm({...form,subject_principal:e.target.value})}/><Stack direction={{xs:'column',md:'row'}} gap={2}><TextField name="registration_date" error={(submitted&&!!errors.registration)||incompleteDate==='registration_date'} helperText={incompleteDate==='registration_date'?'Complete a data de registro.':submitted?errors.registration:undefined} required type="date" label="Data de registro" value={form.registration_date} onChange={e=>{setForm({...form,registration_date:e.target.value});setIncompleteDate('')}} InputLabelProps={{shrink:true}}/><TextField select label="Status" value={form.status} onChange={e=>setForm({...form,status:e.target.value})} sx={{minWidth:190}}>{Object.entries(statuses).map(([v,s])=><MenuItem key={v} value={v}>{s.label}</MenuItem>)}</TextField><TextField name="closure_date" error={(submitted&&!!errors.closure)||incompleteDate==='closure_date'} helperText={incompleteDate==='closure_date'?'Complete a data de fim ou limpe o campo.':submitted?errors.closure:undefined} required={form.status==='fechado'} type="date" label="Data de fim" value={form.closure_date||''} onChange={e=>{setForm({...form,closure_date:e.target.value||null});setIncompleteDate('')}} inputProps={{min:form.registration_date}} InputLabelProps={{shrink:true}}/></Stack><Stack direction={{xs:'column',sm:'row'}} gap={1}><Autocomplete ref={relatorsField} multiple disableCloseOnSelect filterSelectedOptions options={selectableRelators} value={selectedRelators} loading={relatorOptions.isLoading} disabled={busy} getOptionLabel={m=>`${m.display_name}${!m.active?' (inativo)':''}`} getOptionDisabled={m=>!m.active} isOptionEqualToValue={(a,b)=>a.id===b.id} onChange={(_,values)=>{setForm({...form,relator_ids:values.map(m=>m.id)});setError('')}} noOptionsText="Nenhum outro integrante vinculado disponível" fullWidth renderInput={params=><TextField {...params} required label="Relatores" error={(submitted&&!!errors.relators)||relatorOptions.isError} helperText={relatorOptions.isLoading?'Carregando relatores...':relatorOptions.isError?'Não foi possível carregar os relatores.':submitted&&errors.relators?errors.relators:!selectableRelators.length?'Adicione integrantes ao projeto ou subprojeto em Gerenciar integrantes.':hasMemberScope?'Selecione um ou mais integrantes dos projetos ou subprojetos vinculados.':'Selecione um ou mais integrantes de equipes de projetos ou subprojetos.'}/>} /><Button type="button" sx={{minWidth:170}} onClick={()=>setMemberDialog(true)}>Gerenciar integrantes</Button></Stack><TextField label="Tags" helperText="Separe as palavras-chave por vírgulas" value={form.tags} inputProps={{maxLength:4000}} onChange={e=>setForm({...form,tags:e.target.value})}/><TextField multiline minRows={4} label="Descrição / Observações gerais" value={form.description} inputProps={{maxLength:100000}} onChange={e=>setForm({...form,description:e.target.value})}/></Stack></CardContent></Card><Card><CardContent><Typography variant="h6" mb={2}>Vinculação de projetos e subprojetos</Typography><Stack spacing={2.5}><Autocomplete multiple disableCloseOnSelect options={projectOptions} value={projectOptions.filter(p=>form.project_ids.includes(p.id))} getOptionLabel={p=>`${p.code} · ${p.name}`} isOptionEqualToValue={(a,b)=>a.id===b.id} onChange={(_,values)=>setForm({...form,project_ids:values.map(v=>v.id),relator_ids:[]})} renderInput={params=><TextField {...params} label="Projetos SAD"/>}/><Autocomplete multiple disableCloseOnSelect options={subOptions} value={subOptions.filter(s=>form.subproject_ids.includes(s.id))} getOptionLabel={s=>`${s.code} · ${s.name}`} isOptionEqualToValue={(a,b)=>a.id===b.id} onChange={(_,values)=>setForm({...form,subproject_ids:values.map(v=>v.id),relator_ids:[]})} renderInput={params=><TextField {...params} label="Subprojetos"/>}/><Alert severity="info">Sem vínculos, o assunto terá abrangência Global. Subprojetos do mesmo projeto contam como um único projeto para determinar a abrangência.</Alert><Chip sx={{alignSelf:'flex-start'}} label={`Abrangência automática: ${!effective.size?'Global':effective.size===1?'Projeto':'Multi-projeto'}`}/></Stack></CardContent></Card>{['fechado','cancelado'].includes(form.status)&&<Alert severity="warning">Ao salvar como {form.status==='fechado'?'Fechado':'Cancelado'}, o assunto ficará disponível somente para consulta, incluindo seus registros e anexos.</Alert>}<Stack direction="row" justifyContent="space-between" gap={2} flexWrap="wrap">{book?<Button color="error" disabled={busy} onClick={()=>setDeleting(true)}>Excluir assunto</Button>:<Box/>}<Stack direction="row" gap={1}><Button component={Link} to={back} disabled={busy}>Cancelar</Button><Button type="submit" variant="contained" disabled={busy}>{busy?'Salvando...':'Salvar diário'}</Button></Stack></Stack></Stack>{memberDialog&&<ScopeMembersDialog initialScope={contextSub?{type:'subproject',id:contextSub,name:subs.find(s=>s.id===contextSub)?.name||`Subprojeto ${contextSub}`}:form.subproject_ids.length===1?{type:'subproject',id:form.subproject_ids[0],name:subOptions.find(s=>s.id===form.subproject_ids[0])?.name||'Subprojeto'}:form.project_ids.length===1?{type:'project',id:form.project_ids[0],name:projectOptions.find(p=>p.id===form.project_ids[0])?.name||'Projeto'}:undefined} onClose={()=>setMemberDialog(false)}/>} {deleting&&book&&<ConfirmDialog title="Excluir assunto?" onClose={()=>setDeleting(false)} onConfirm={async()=>{await api.delete(`/logbooks/${book.id}`);await client.invalidateQueries({queryKey:['logbooks']});await client.invalidateQueries({queryKey:['logbook-timeline']});navigate(contextSub?`/subprojetos/${contextSub}/diario`:'/diarios')}}>O assunto, seus registros e anexos serão excluídos permanentemente.</ConfirmDialog>}</Box>;
}
