import {useEffect,useMemo,useState} from 'react';
import {ArrowBack,SaveOutlined} from '@mui/icons-material';
import {Alert,Autocomplete,Box,Breadcrumbs,Button,Card,CardContent,Divider,FormHelperText,Link as MuiLink,MenuItem,Skeleton,Stack,TextField,Typography} from '@mui/material';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {Link,useNavigate,useParams} from 'react-router-dom';
import {api,Contract,Project,ProjectInput,ProjectOptions} from '../api';
import DocumentDropzone from '../components/DocumentDropzone';

const phaseOptions=[
  ['NAO_INICIADO','Nao iniciado'],['PRE_PROJETO','Pre-projeto'],['PLANEJAMENTO','Planejamento'],
  ['EXECUCAO','Execucao'],['ENCERRAMENTO','Encerramento'],['ENCERRADO','Encerrado'],['SUSPENSO','Suspenso'],
];
const empty:ProjectInput={code:'',name:'',description:null,manager:'',status:'PLANEJAMENTO',phase:'NAO_INICIADO',priority:'MEDIA',start_date:null,end_date:null,progress:0,budget:null,cma:null,geographic_scope:null,objectives:null,contracts:[],oms:[],documents:[]};
const statusForPhase=(phase:string)=>phase==='EXECUCAO'?'EM_EXECUCAO':phase==='ENCERRADO'?'CONCLUIDO':phase==='SUSPENSO'?'SUSPENSO':'PLANEJAMENTO';

const toInput=(project:Project):ProjectInput=>({
  code:project.code,name:project.name,description:project.description,manager:project.manager,status:project.status,
  phase:project.phase,priority:project.priority,start_date:project.start_date,end_date:project.end_date,
  progress:project.progress,budget:project.budget,cma:project.cma,geographic_scope:project.geographic_scope,
  objectives:project.objectives,
  contracts:project.contracts.map(({external_contract_id,contract_number,contract_object,supplier_name,global_value,status,start_date,end_date})=>({external_contract_id,contract_number,contract_object,supplier_name,global_value,status,start_date,end_date})),
  oms:project.oms.map(({name})=>({name})),documents:project.documents.map(({name,url})=>({name,url})),
});

function Section({number,title,children}:{number:number;title:string;children:React.ReactNode}){return <Box><Stack direction="row" alignItems="center" gap={1.2} mb={2}><Box sx={{width:30,height:30,borderRadius:'50%',display:'grid',placeItems:'center',bgcolor:'#eaf2fc',color:'primary.main',fontWeight:900,fontSize:13}}>{String(number).padStart(2,'0')}</Box><Typography variant="h6">{title}</Typography></Stack>{children}</Box>}

export default function ProjectForm(){
  const {id}=useParams();
  const editing=Boolean(id);
  const navigate=useNavigate();
  const queryClient=useQueryClient();
  const [form,setForm]=useState<ProjectInput>(empty);
  const [error,setError]=useState('');
  const project=useQuery({queryKey:['project',id],queryFn:()=>api.get<Project>(`/projects/${id}`).then(r=>r.data),enabled:editing});
  const options=useQuery({queryKey:['project-options'],queryFn:()=>api.get<ProjectOptions>('/project-options').then(r=>r.data)});
  const contracts=useQuery({queryKey:['contracts'],queryFn:()=>api.get<Contract[]>('/contracts',{params:{limit:200}}).then(r=>r.data)});
  useEffect(()=>{if(project.data)setForm(toInput(project.data))},[project.data]);
  const set=(field:keyof ProjectInput,value:any)=>setForm(old=>({...old,[field]:value}));
  const duration=useMemo(()=>{if(!form.start_date||!form.end_date)return '';const days=(new Date(form.end_date).getTime()-new Date(form.start_date).getTime())/86400000;return days>=0?String(Math.floor(days/365.25)):''},[form.start_date,form.end_date]);
  const mutation=useMutation({
    mutationFn:(payload:ProjectInput)=>editing?api.put(`/projects/${id}`,payload):api.post('/projects',payload),
    onSuccess:async response=>{await Promise.all([queryClient.invalidateQueries({queryKey:['projects']}),queryClient.invalidateQueries({queryKey:['dashboard']})]);navigate(`/projetos/${response.data.id}`)},
    onError:(err:any)=>setError(err.response?.data?.detail?.[0]?.msg||err.response?.data?.detail||'Nao foi possivel salvar o projeto.'),
  });
  const save=()=>{
    setError('');
    if(!form.name.trim()||!form.code.trim()||!form.manager.trim()||!form.start_date||!form.cma){setError('Preencha os campos obrigatorios: nome, sigla, responsavel, data de inicio e CMA.');return}
    if(form.phase==='EXECUCAO'&&!form.budget){setError('O orcamento e obrigatorio para projetos em execucao.');return}
    const incomplete=form.documents.some(doc=>(doc.name&&!doc.url)||(!doc.name&&doc.url));
    if(incomplete){setError('Informe o nome e o link de cada documento.');return}
    mutation.mutate({...form,status:statusForPhase(form.phase),documents:form.documents.filter(d=>d.name&&d.url)});
  };
  if(editing&&project.isLoading)return <Skeleton variant="rounded" height={600}/>;
  if(project.isError)return <Alert severity="error">Projeto nao encontrado.</Alert>;
  return <Box>
    <Breadcrumbs sx={{mb:2}}><MuiLink component={Link} to="/" underline="hover">Dashboard</MuiLink><MuiLink component={Link} to="/projetos" underline="hover">Projetos SAD</MuiLink><Typography>{editing?'Editar Projeto':'Novo Projeto'}</Typography></Breadcrumbs>
    <Stack direction={{xs:'column',sm:'row'}} justifyContent="space-between" alignItems={{sm:'center'}} gap={2} mb={2}><Box><Typography variant="h4">{editing?'Editar Projeto SAD/SISFRON':'Novo Projeto SAD/SISFRON'}</Typography><Typography color="text.secondary">Cadastro institucional e vinculos do projeto.</Typography></Box><Button startIcon={<ArrowBack/>} onClick={()=>navigate('/projetos')}>Voltar</Button></Stack>
    {error&&<Alert severity="error" sx={{mb:2}} onClose={()=>setError('')}>{error}</Alert>}
    <Card><CardContent sx={{p:{xs:2,md:3.5}}}>
      <Section number={1} title="Identificacao e classificacao"><Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:'2fr 1fr 1fr 1fr'},gap:2}}><TextField label="Nome do projeto *" value={form.name} onChange={e=>set('name',e.target.value)} placeholder="Nome completo do projeto"/><TextField label="Sigla *" value={form.code} onChange={e=>set('code',e.target.value.toUpperCase())} placeholder="Ex: SISFRON"/><TextField select label="Fase atual *" value={form.phase} onChange={e=>set('phase',e.target.value)}>{phaseOptions.map(([value,label])=><MenuItem key={value} value={value}>{label}</MenuItem>)}</TextField><TextField label="Orcamento (R$)" type="number" value={form.budget??''} onChange={e=>set('budget',e.target.value===''?null:Number(e.target.value))} inputProps={{min:0,step:0.01}}/><TextField label="Responsavel *" value={form.manager} onChange={e=>set('manager',e.target.value)} sx={{gridColumn:{md:'span 2'}}}/><TextField select label="Prioridade" value={form.priority} onChange={e=>set('priority',e.target.value)}><MenuItem value="BAIXA">Baixa</MenuItem><MenuItem value="MEDIA">Media</MenuItem><MenuItem value="ALTA">Alta</MenuItem><MenuItem value="CRITICA">Critica</MenuItem></TextField><TextField label="Progresso (%)" type="number" value={form.progress} onChange={e=>set('progress',Math.max(0,Math.min(100,Number(e.target.value))))} inputProps={{min:0,max:100}}/><TextField label="Descricao resumida" multiline minRows={2} value={form.description||''} onChange={e=>set('description',e.target.value||null)} sx={{gridColumn:{md:'span 4'}}}/></Box></Section>
      <Divider sx={{my:4}}/>
      <Section number={2} title="Cronograma"><Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:'repeat(3,1fr)'},gap:2}}><TextField label="Data de inicio *" type="date" InputLabelProps={{shrink:true}} value={form.start_date||''} onChange={e=>set('start_date',e.target.value||null)}/><TextField label="Data de fim" type="date" InputLabelProps={{shrink:true}} value={form.end_date||''} onChange={e=>set('end_date',e.target.value||null)}/><TextField label="Duracao (anos)" value={duration} disabled/></Box></Section>
      <Divider sx={{my:4}}/>
      <Section number={3} title="Escopo territorial e militar"><Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:'1fr 1fr'},gap:2}}><TextField select label="Cmdo Militar de Area *" value={form.cma||''} onChange={e=>set('cma',e.target.value||null)}><MenuItem value="">Selecione...</MenuItem>{options.data?.cmas.map(c=><MenuItem key={c.code} value={c.code}>{c.name} ({c.code})</MenuItem>)}</TextField><TextField label="Abrangencia geografica" multiline minRows={2} value={form.geographic_scope||''} onChange={e=>set('geographic_scope',e.target.value||null)} placeholder="Descreva a area de atuacao..."/><Autocomplete multiple freeSolo options={options.data?.oms||[]} value={form.oms.map(o=>o.name)} onChange={(_,values)=>set('oms',values.map(name=>({name})))} renderInput={params=><TextField {...params} label="OM atendidas" placeholder="Selecione ou informe uma OM" helperText="E possivel selecionar varias organizacoes militares."/>} sx={{gridColumn:{md:'span 2'}}}/></Box></Section>
      <Divider sx={{my:4}}/>
      <Section number={4} title="Contratos vinculados"><Autocomplete multiple options={contracts.data||[]} loading={contracts.isLoading} value={form.contracts} isOptionEqualToValue={(a,b)=>a.external_contract_id===b.external_contract_id} getOptionLabel={o=>`${o.contract_number||o.external_contract_id} — ${o.supplier_name||'Fornecedor nao informado'}`} onChange={(_,values)=>set('contracts',values)} renderInput={params=><TextField {...params} label="Contratos do Radar Financeiro" placeholder="Pesquise e selecione"/>} renderOption={(props,option)=><li {...props} key={option.external_contract_id}><Box><Typography variant="body2" fontWeight={800}>{option.contract_number||option.external_contract_id} · {option.supplier_name||'Sem fornecedor'}</Typography><Typography variant="caption" color="text.secondary">{option.contract_object||'Objeto nao informado'}</Typography></Box></li>}/><FormHelperText sx={{ml:1}}>A consulta e somente leitura; os vinculos sao gravados exclusivamente na base de projetos.</FormHelperText></Section>
      <Divider sx={{my:4}}/>
      <Section number={5} title="Detalhes e documentacao"><TextField fullWidth label="Objetivo do projeto" multiline minRows={4} value={form.objectives||''} onChange={e=>set('objectives',e.target.value||null)} placeholder="Descreva os objetivos principais..." sx={{mb:2.5}}/><Card variant="outlined" sx={{boxShadow:'none'}}><CardContent><Typography fontWeight={800} mb={1.5}>Documentos vinculados</Typography><DocumentDropzone documents={form.documents} onChange={documents=>set('documents',documents)}/></CardContent></Card></Section>
      <Divider sx={{my:3}}/><Stack direction="row" justifyContent="flex-end" gap={1.5}><Button variant="outlined" onClick={()=>navigate('/projetos')}>Cancelar</Button><Button variant="contained" startIcon={<SaveOutlined/>} disabled={mutation.isPending} onClick={save}>{mutation.isPending?'Salvando...':'Salvar projeto'}</Button></Stack>
    </CardContent></Card>
  </Box>;
}
