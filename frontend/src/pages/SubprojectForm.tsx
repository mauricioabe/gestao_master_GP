import {useEffect,useRef,useState} from 'react';
import {ArrowBack,SaveOutlined} from '@mui/icons-material';
import {Alert,Box,Breadcrumbs,Button,Card,CardContent,Divider,Link as MuiLink,MenuItem,Skeleton,Stack,TextField,Typography} from '@mui/material';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {Link,useNavigate,useParams} from 'react-router-dom';
import {api,Contract,Project,Subproject,SubprojectInput} from '../api';
import {ContractPicker,fetchLinkedContracts,linkedContractsKey,saveLinkedContracts} from '../components/SubprojectContracts';

const empty:SubprojectInput={project_id:0,parent_id:null,code:'',name:'',short_name:null,description:null,objective:'',main_product:'',expected_deliverables:null,scope:null,out_of_scope:null,expected_benefits:null,manager:'',responsible_unit:'',status:'PLANEJAMENTO',priority:'MEDIA',planned_start_date:'',planned_end_date:'',real_start_date:null,real_end_date:null,execution_percentage:0,budget:null,key_milestones:null,schedule_status:null,justification:null};
const statuses=[['PLANEJAMENTO','Em planejamento'],['PLANEJADO','Planejado'],['EM_ANDAMENTO','Em andamento'],['SUSPENSO','Suspenso'],['SOBRESTADO','Sobrestado'],['ATRASADO','Atrasado'],['CONCLUIDO','Concluido'],['CANCELADO','Cancelado'],['ENCERRADO','Encerrado']];
const needsJustification=new Set(['SUSPENSO','SOBRESTADO','CANCELADO']);

function Section({number,title,children}:{number:number;title:string;children:React.ReactNode}){return <Box><Typography variant="h6" sx={{pb:1.2,mb:2,borderBottom:'1px solid #dce5ef'}}>{number}. {title}</Typography>{children}</Box>}

export default function SubprojectForm(){
  const {id,projectId}=useParams();
  const editing=Boolean(id);
  const navigate=useNavigate();
  const queryClient=useQueryClient();
  const [form,setForm]=useState<SubprojectInput>({...empty,project_id:Number(projectId)||0});
  const [error,setError]=useState('');
  const projects=useQuery({queryKey:['projects'],queryFn:()=>api.get<Project[]>('/projects').then(r=>r.data)});
  const item=useQuery({queryKey:['subproject',id],queryFn:()=>api.get<Subproject>(`/subprojects/${id}`).then(r=>r.data),enabled:editing});
  useEffect(()=>{if(item.data){const {id:_,wbs_code:__,sort_order:___,active:____,project_name:_____,project_code:______,parent_name:_______,children_count:________,created_at:_________,updated_at:__________,...input}=item.data;setForm(input)}},[item.data]);
  const selectedProject=projects.data?.find(project=>project.id===form.project_id);
  const set=(field:keyof SubprojectInput,value:any)=>setForm(old=>({...old,[field]:value}));
  const [contracts,setContracts]=useState<Contract[]>([]);
  const linked=useQuery({queryKey:linkedContractsKey(Number(id)),queryFn:()=>fetchLinkedContracts(Number(id)),enabled:editing});
  // Carrega os vinculos uma unica vez para nao sobrescrever a selecao em andamento.
  const contractsLoaded=useRef(!editing);
  useEffect(()=>{if(linked.data&&!contractsLoaded.current){contractsLoaded.current=true;setContracts(linked.data.contracts)}},[linked.data]);
  const mutation=useMutation({
    mutationFn:async(payload:SubprojectInput)=>{
      const response=editing?await api.put<Subproject>(`/subprojects/${id}`,payload):await api.post<Subproject>('/subprojects',payload);
      try{await saveLinkedContracts(response.data.id,contracts)}
      catch(err:any){
        // O subprojeto ja foi gravado; reabre a edicao para que os contratos sejam ajustados.
        navigate(`/subprojetos/${response.data.id}/editar`,{replace:true});
        throw new Error(`Subprojeto salvo, mas os contratos nao foram vinculados: ${err.response?.data?.detail||'erro ao consultar o Radar Financeiro'}`);
      }
      return response;
    },
    onSuccess:async response=>{await Promise.all([queryClient.invalidateQueries({queryKey:['subprojects']}),queryClient.invalidateQueries({queryKey:['subproject-contracts']})]);navigate(`/subprojetos/${response.data.id}`)},
    onError:(err:any)=>setError(err.response?.data?.detail?.[0]?.msg||err.response?.data?.detail||err.message||'Nao foi possivel salvar o subprojeto.')
  });
  const save=()=>{
    setError('');
    if(!form.project_id||!form.name.trim()||!form.objective.trim()||!form.main_product.trim()||!form.manager.trim()||!form.responsible_unit.trim()){setError('Preencha todos os campos obrigatorios.');return}
    const today=new Date().toISOString().slice(0,10);
const payload:SubprojectInput={...form,parent_id:editing?form.parent_id:null,code:form.code||`SUB-${Date.now().toString(36).toUpperCase()}`,short_name:editing?form.short_name:null,expected_deliverables:editing?form.expected_deliverables:null,expected_benefits:editing?form.expected_benefits:null,planned_start_date:form.planned_start_date||selectedProject?.start_date||today,planned_end_date:form.planned_end_date||selectedProject?.end_date||selectedProject?.start_date||today,real_start_date:editing?form.real_start_date:null,real_end_date:editing?form.real_end_date:(form.status==='CONCLUIDO'?today:null),execution_percentage:editing?form.execution_percentage:0,key_milestones:editing?form.key_milestones:null,schedule_status:editing?form.schedule_status:null};
    if(needsJustification.has(form.status)&&!form.justification?.trim()){setError('Informe a justificativa para a situacao selecionada.');return}
    mutation.mutate(payload);
  };
  if(editing&&item.isLoading)return <Skeleton variant="rounded" height={600}/>;
  return <Box>
    <Breadcrumbs sx={{mb:2}}><MuiLink component={Link} to="/">Dashboard</MuiLink><MuiLink component={Link} to="/subprojetos">Subprojetos</MuiLink><Typography>{editing?'Editar':'Novo'}</Typography></Breadcrumbs>
    <Stack direction={{xs:'column',sm:'row'}} justifyContent="space-between" alignItems={{sm:'center'}} gap={2} mb={2.5}><Box><Typography variant="h4">{editing?'Editar subprojeto':'Novo subprojeto'}</Typography><Typography color="text.secondary">{selectedProject?`Subordinado a ${selectedProject.code} — ${selectedProject.name}`:'Selecione o Projeto SAD superior.'}</Typography></Box><Button startIcon={<ArrowBack/>} onClick={()=>navigate('/subprojetos')}>Voltar</Button></Stack>
    {error&&<Alert severity="error" sx={{mb:2}} onClose={()=>setError('')}>{error}</Alert>}
    <Card><CardContent sx={{p:{xs:2,md:3.5}}}>
      <Section number={1} title="Identificacao"><Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:'1fr 2fr'},gap:2}}><TextField select label="Projeto SAD superior *" value={form.project_id||''} disabled={editing||Boolean(projectId)} onChange={e=>set('project_id',Number(e.target.value))}><MenuItem value="">Selecione...</MenuItem>{projects.data?.map(project=><MenuItem key={project.id} value={project.id}>{project.code} — {project.name}</MenuItem>)}</TextField><TextField label="Nome oficial *" value={form.name} onChange={e=>set('name',e.target.value)}/><TextField label="Descricao geral" multiline minRows={3} value={form.description||''} onChange={e=>set('description',e.target.value||null)} sx={{gridColumn:{md:'span 2'}}}/></Box></Section>
      <Divider sx={{my:4}}/>
      <Section number={2} title="Objetivo, produto e escopo"><Stack spacing={2}><TextField label="Objetivo *" multiline minRows={3} value={form.objective} onChange={e=>set('objective',e.target.value)}/><TextField label="Produto principal *" value={form.main_product} onChange={e=>set('main_product',e.target.value)}/><Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:'1fr 1fr'},gap:2}}><TextField label="Escopo" multiline minRows={3} value={form.scope||''} onChange={e=>set('scope',e.target.value||null)}/><TextField label="Fora do escopo" multiline minRows={3} value={form.out_of_scope||''} onChange={e=>set('out_of_scope',e.target.value||null)}/></Box></Stack></Section>
      <Divider sx={{my:4}}/>
      <Section number={3} title="Gerencia e situacao"><Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:'repeat(4,1fr)'},gap:2}}><TextField label="Gerente do subprojeto *" value={form.manager} onChange={e=>set('manager',e.target.value)} sx={{gridColumn:{md:'span 2'}}}/><TextField label="Unidade responsavel *" value={form.responsible_unit} onChange={e=>set('responsible_unit',e.target.value)}/><TextField select label="Prioridade" value={form.priority} onChange={e=>set('priority',e.target.value)}><MenuItem value="BAIXA">Baixa</MenuItem><MenuItem value="MEDIA">Media</MenuItem><MenuItem value="ALTA">Alta</MenuItem><MenuItem value="CRITICA">Critica</MenuItem></TextField><TextField select label="Situacao" value={form.status} onChange={e=>set('status',e.target.value)}>{statuses.map(([value,label])=><MenuItem key={value} value={value}>{label}</MenuItem>)}</TextField><TextField label="Orcamento (R$)" type="number" value={form.budget??''} onChange={e=>set('budget',e.target.value===''?null:Number(e.target.value))}/>{needsJustification.has(form.status)&&<TextField label="Justificativa *" multiline minRows={2} value={form.justification||''} onChange={e=>set('justification',e.target.value||null)} sx={{gridColumn:{md:'span 2'}}}/>}</Box></Section>
      <Divider sx={{my:4}}/>
      <Section number={4} title="Contratos vinculados">{editing&&linked.isLoading?<Skeleton variant="rounded" height={56}/>:<ContractPicker projectId={form.project_id} value={contracts} onChange={setContracts}/>}</Section>
      <Divider sx={{my:3}}/><Stack direction="row" justifyContent="flex-end" gap={1.5}><Button variant="outlined" onClick={()=>navigate('/subprojetos')}>Cancelar</Button><Button variant="contained" startIcon={<SaveOutlined/>} disabled={mutation.isPending} onClick={save}>{mutation.isPending?'Salvando...':'Salvar subprojeto'}</Button></Stack>
    </CardContent></Card>
  </Box>;
}
