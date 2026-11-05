import {DragEvent,FocusEvent,KeyboardEvent,useEffect,useMemo,useRef,useState} from 'react';
import {Add,ArrowBack,AutoFixHighOutlined,CalendarMonthOutlined,CancelOutlined,CheckCircleOutline,ChevronRight,CloudDownloadOutlined,DeleteOutline,DragIndicatorOutlined,EditOutlined,ExpandMore,FormatIndentDecreaseOutlined,FormatIndentIncreaseOutlined,PendingActionsOutlined,PlayCircleOutline,SaveOutlined,WarningAmberOutlined} from '@mui/icons-material';
import {Alert,Box,Breadcrumbs,Button,Card,CardContent,Checkbox,Chip,Dialog,DialogActions,DialogContent,DialogTitle,IconButton,InputAdornment,LinearProgress,Link as MuiLink,MenuItem,Skeleton,Stack,Table,TableBody,TableCell,TableContainer,TableHead,TableRow,TextField,Tooltip,Typography} from '@mui/material';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {Link,useNavigate,useParams} from 'react-router-dom';
import {Activity,ActivityInput,api,CffImportResult,CffPreview,Project,Subproject} from '../api';

const empty:ActivityInput={name:'',start_date:'',finish_date:'',resource_names:null,execution_percentage:0,planned_value:0,actual_value:0,delivery_status:'EM_PLANEJAMENTO',predecessor_id:null};
const deliveryStatusOptions=[
  {value:'EM_PLANEJAMENTO' as const,label:'Em planejamento',color:'#c78013',icon:<PendingActionsOutlined fontSize="small"/>},
  {value:'EM_EXECUCAO' as const,label:'Em execução',color:'#2d6fac',icon:<PlayCircleOutline fontSize="small"/>},
  {value:'ENCERRADA' as const,label:'Encerrada',color:'#16805b',icon:<CheckCircleOutline fontSize="small"/>},
  {value:'CANCELADA' as const,label:'Cancelada',color:'#667085',icon:<CancelOutlined fontSize="small"/>},
];
const date=(value:string)=>new Intl.DateTimeFormat('pt-BR',{timeZone:'UTC'}).format(new Date(`${value}T00:00:00Z`));
const iso=(value:string)=>new Date(`${value}T00:00:00Z`);
const nextBusinessDay=(value:string)=>{const d=iso(value);do{d.setUTCDate(d.getUTCDate()+1)}while(d.getUTCDay()===0||d.getUTCDay()===6);return d.toISOString().slice(0,10)};
const duration=(start:string,finish:string)=>{let current=iso(start);const end=iso(finish);let total=0;while(current<=end){if(current.getUTCDay()!==0&&current.getUTCDay()!==6)total++;current.setUTCDate(current.getUTCDate()+1)}return total};
const finishForBusinessDays=(start:string,days:number)=>{const d=iso(start);let counted=(d.getUTCDay()!==0&&d.getUTCDay()!==6)?1:0;while(counted<days){d.setUTCDate(d.getUTCDate()+1);if(d.getUTCDay()!==0&&d.getUTCDay()!==6)counted++}return d.toISOString().slice(0,10)};
const money=(value:number|string|null)=>value==null?'-':new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(value));
type EditableField='name'|'start_date'|'finish_date'|'resource_names'|'execution_percentage'|'planned_value'|'actual_value'|'predecessor_id';
type InlineEdit={activityId:number;field:EditableField};
type DropPosition='before'|'after'|'inside';

export default function ScheduleActivities({mode='milestones'}:{mode?:'milestones'|'project'}){
  const {subprojectId}=useParams();
  const id=Number(subprojectId);
  const official=mode==='project';
  const collectionPath=official?`/subprojects/${id}/project-activities`:`/subprojects/${id}/activities`;
  const activityQueryKey=['activities',mode,id];
  const navigate=useNavigate();
  const queryClient=useQueryClient();
  const [open,setOpen]=useState(false);
  const [editing,setEditing]=useState<Activity|null>(null);
  const [form,setForm]=useState<ActivityInput>(empty);
  const [error,setError]=useState('');
  const [collapsed,setCollapsed]=useState<Set<number>>(()=>new Set());
  const [inlineEdit,setInlineEdit]=useState<InlineEdit|null>(null);
  const [inlineValue,setInlineValue]=useState('');
  const [cffOpen,setCffOpen]=useState(false);
  const [selectedCff,setSelectedCff]=useState<Set<number>>(()=>new Set());
  const [cffParentId,setCffParentId]=useState<number|''>('');
  const [cffResult,setCffResult]=useState('');
  const [draggedId,setDraggedId]=useState<number|null>(null);
  const [dragOver,setDragOver]=useState<{id:number;position:DropPosition}|null>(null);
  const draggedIdRef=useRef<number|null>(null);
  const skipInlineBlur=useRef(false);
  // Duracao do formulario no momento em que o inicio entra em edicao.
  const formDuration=useRef(0);
  const subproject=useQuery({queryKey:['subproject',id],queryFn:()=>api.get<Subproject>(`/subprojects/${id}`).then(r=>r.data),enabled:Boolean(id)});
  const activities=useQuery({queryKey:activityQueryKey,queryFn:()=>api.get<Activity[]>(collectionPath).then(r=>r.data),enabled:Boolean(id)});
const project=useQuery({queryKey:['project',subproject.data?.project_id],queryFn:()=>api.get<Project>(`/projects/${subproject.data!.project_id}`).then(r=>r.data),enabled:Boolean(subproject.data?.project_id)});
const milestoneProgress=useQuery({queryKey:['activities',mode,id,'progress'],queryFn:()=>api.get<{project_progress:number;subproject_progress:number}>(`/subprojects/${id}/activities/progress`).then(r=>r.data),enabled:Boolean(id)&&!official});
const cff=useQuery({queryKey:['cff',id],queryFn:()=>api.get<CffPreview>(`/subprojects/${id}/cff`).then(r=>r.data),enabled:Boolean(id)&&official&&cffOpen});
// Milestones exibem consolidado proprio; o cronograma oficial usa o progresso do projeto.
const projectRowProgress=official?project.data?.progress??0:milestoneProgress.data?.project_progress??0;
const subprojectRowProgress=official?subproject.data?.execution_percentage??0:milestoneProgress.data?.subproject_progress??0;
const refreshProgress=()=>Promise.all([queryClient.invalidateQueries({queryKey:activityQueryKey}),queryClient.invalidateQueries({queryKey:['subproject',id]}),queryClient.invalidateQueries({queryKey:['project']}),queryClient.invalidateQueries({queryKey:['projects']})]);
  const items=activities.data||[];
  const cffParents=items.filter(item=>item.source_system!=='RADAR_CFF');
  const byId=useMemo(()=>new Map(items.map(item=>[item.id,item])),[items]);
  const draggedBlockIds=useMemo(()=>{const block=new Set<number>();if(draggedId===null)return block;for(const item of items){let current:Activity|undefined=item;const visited=new Set<number>();while(current&&!visited.has(current.id)){visited.add(current.id);if(current.id===draggedId){block.add(item.id);break}current=current.parent_id?byId.get(current.parent_id):undefined}}return block},[draggedId,items,byId]);
const visibleItems=useMemo(()=>items.filter(item=>{let parentId=item.parent_id;const visited=new Set<number>();while(parentId&&byId.has(parentId)&&!visited.has(parentId)){if(collapsed.has(parentId))return false;visited.add(parentId);parentId=byId.get(parentId)!.parent_id}return true}),[items,byId,collapsed]);
  const importableCff=cff.data?.stages.filter(stage=>stage.importable)||[];
  const toggleCff=(stageId:number)=>setSelectedCff(current=>{const next=new Set(current);next.has(stageId)?next.delete(stageId):next.add(stageId);return next});
  const toggleAllCff=()=>setSelectedCff(current=>current.size===importableCff.length?new Set():new Set(importableCff.map(stage=>stage.id)));
  const conflicts=useMemo(()=>items.filter(item=>{const predecessor=item.predecessor_id?byId.get(item.predecessor_id):null;return predecessor&&item.start_date<nextBusinessDay(predecessor.finish_date)}),[items,byId]);
  const selectedPredecessor=form.predecessor_id?byId.get(form.predecessor_id):null;
  const formConflict=Boolean(selectedPredecessor&&form.start_date&&form.start_date<nextBusinessDay(selectedPredecessor.finish_date));
  useEffect(()=>{if(open&&!editing&&subproject.data){setForm({...empty,start_date:subproject.data.planned_start_date,finish_date:subproject.data.planned_start_date})}},[open,editing,subproject.data]);
  useEffect(()=>{if(cff.data)setSelectedCff(new Set(cff.data.stages.filter(stage=>stage.importable&&!stage.imported).map(stage=>stage.id)))},[cff.data]);
  const close=()=>{setOpen(false);setEditing(null);setForm(empty);setError('')};
  const showCreate=()=>{setEditing(null);setOpen(true)};
  const showEdit=(item:Activity)=>{setEditing(item);setForm({name:item.name,start_date:item.start_date,finish_date:item.finish_date,resource_names:item.resource_names,execution_percentage:item.execution_percentage,planned_value:item.planned_value,actual_value:item.actual_value,delivery_status:item.delivery_status,predecessor_id:item.predecessor_id});setOpen(true)};
  const save=useMutation({mutationFn:()=>editing?api.put(`/activities/${editing.id}`,form):api.post(collectionPath,form),onSuccess:async()=>{close();await refreshProgress()},onError:(err:any)=>setError(err.response?.data?.detail?.[0]?.msg||err.response?.data?.detail||'Nao foi possivel salvar a atividade.')});
  const remove=useMutation({mutationFn:(activityId:number)=>api.delete(`/activities/${activityId}`),onSuccess:()=>refreshProgress(),onError:(err:any)=>setError(err.response?.data?.detail||'Nao foi possivel excluir a atividade.')});
const hierarchy=useMutation({mutationFn:({activityId,action}:{activityId:number;action:'indent'|'outdent'})=>api.post<Activity[]>(`/activities/${activityId}/${action}`),onSuccess:async response=>{queryClient.setQueryData(activityQueryKey,response.data);await refreshProgress()},onError:(err:any)=>setError(err.response?.data?.detail||'Nao foi possivel alterar o nivel da atividade.')});
  const reorder=useMutation({mutationFn:({activityId,targetId,position}:{activityId:number;targetId:number;position:DropPosition})=>api.post<Activity[]>(`/activities/${activityId}/reorder`,{target_id:targetId,position}),onSuccess:async response=>{queryClient.setQueryData(activityQueryKey,response.data);setError('');await refreshProgress()},onError:(err:any)=>setError(err.response?.data?.detail||'Nao foi possivel mover a atividade.'),onSettled:()=>{setDraggedId(null);setDragOver(null)}});
  const importCff=useMutation({
    mutationFn:()=>api.post<CffImportResult>(`/subprojects/${id}/cff/import`,{stage_ids:Array.from(selectedCff),parent_activity_id:cffParentId}),
    onSuccess:async response=>{
      queryClient.setQueryData(activityQueryKey,response.data.activities);
      setCffResult(`${response.data.imported} importada(s), ${response.data.updated} atualizada(s) e ${response.data.skipped} sem alteracao.`);
      await Promise.all([refreshProgress(),queryClient.invalidateQueries({queryKey:['cff',id]})]);
    },
    onError:(err:any)=>setCffResult(err.response?.data?.detail||'Nao foi possivel importar o CFF.')
  });
  const inlineSave=useMutation({
    mutationFn:({item,field,value}:{item:Activity;field:EditableField;value:string})=>{
      const payload:ActivityInput={name:item.name,start_date:item.start_date,finish_date:item.finish_date,resource_names:item.resource_names,execution_percentage:item.execution_percentage,planned_value:item.planned_value,actual_value:item.actual_value,delivery_status:item.delivery_status,predecessor_id:item.predecessor_id};
      if(field==='execution_percentage')payload.execution_percentage=Math.max(0,Math.min(100,Number(value)||0));
      else if(field==='planned_value'||field==='actual_value')payload[field]=Math.max(0,Number(value)||0);
      else if(field==='predecessor_id')payload.predecessor_id=value?Number(value):null;
      else if(field==='resource_names')payload.resource_names=value.trim()||null;
      else if(field==='name')payload.name=value.trim();
      else payload[field]=value;
      // Inicio apos o termino desloca o termino mantendo a duracao em dias uteis.
      if(field==='start_date'&&payload.start_date>payload.finish_date)payload.finish_date=finishForBusinessDays(payload.start_date,Math.max(1,item.duration_days));
      if(!payload.name)throw new Error('O nome da atividade e obrigatorio.');
      if(payload.finish_date<payload.start_date)throw new Error('A data de termino nao pode ser anterior a data de inicio.');
      return api.put<Activity>(`/activities/${item.id}`,payload);
    },
    onSuccess:async()=>{setInlineEdit(null);setInlineValue('');setError('');await refreshProgress()},
    onError:(err:any)=>setError(err.response?.data?.detail?.[0]?.msg||err.response?.data?.detail||err.message||'Nao foi possivel alterar a atividade.')
  });
  const inlineOriginalValue=(item:Activity,field:EditableField)=>field==='predecessor_id'?String(item.predecessor_id||''):field==='execution_percentage'?String(item.execution_percentage):String(item[field]??'');
  const startInline=(item:Activity,field:EditableField)=>{
    if(inlineSave.isPending||(item.is_summary&&!['name','resource_names'].includes(field)))return;
    setError('');
    setInlineEdit({activityId:item.id,field});
    setInlineValue(inlineOriginalValue(item,field));
  };
  const cancelInline=()=>{setInlineEdit(null);setInlineValue('')};
  const commitInline=(value=inlineValue)=>{
    if(!inlineEdit||inlineSave.isPending)return;
    const item=byId.get(inlineEdit.activityId);
    if(!item)return cancelInline();
    if(value===inlineOriginalValue(item,inlineEdit.field))return cancelInline();
    inlineSave.mutate({item,field:inlineEdit.field,value});
  };
  const inlineKeyDown=(event:KeyboardEvent<HTMLInputElement>)=>{
    if(event.key==='Enter'){event.preventDefault();event.currentTarget.blur()}
    if(event.key==='Escape'){event.preventDefault();skipInlineBlur.current=true;cancelInline();event.currentTarget.blur()}
  };
  const inlineBlur=(event:FocusEvent<HTMLInputElement>)=>{
    if(skipInlineBlur.current){skipInlineBlur.current=false;return}
    // O input date pode publicar a ultima alteracao junto com o blur. Ler o
    // valor do elemento evita salvar o estado React da renderizacao anterior.
    commitInline(event.currentTarget.value);
  };
  const inlineEditor=(item:Activity,field:EditableField)=>{
    const common={autoFocus:true,variant:'standard' as const,size:'small' as const,fullWidth:true,value:inlineValue,disabled:inlineSave.isPending,onChange:(event:React.ChangeEvent<HTMLInputElement>)=>setInlineValue(event.target.value),onKeyDown:inlineKeyDown,onBlur:inlineBlur};
    if(field==='predecessor_id')return <TextField {...common} select onChange={event=>{const value=event.target.value;setInlineValue(value);skipInlineBlur.current=true;inlineSave.mutate({item,field,value})}}>{<MenuItem value="">Nenhuma</MenuItem>}{items.filter(candidate=>candidate.id!==item.id&&!candidate.is_summary).map(candidate=>
<MenuItem key={candidate.id} value={candidate.id}>{candidate.wbs_code} - {candidate.name}</MenuItem>)}</TextField>;
    if(field==='planned_value'||field==='actual_value')return <TextField {...common} type="number" inputProps={{min:0,step:.01}} InputProps={{startAdornment:<InputAdornment position="start">R$</InputAdornment>}}/>;
    return <TextField {...common} type={field==='start_date'||field==='finish_date'?'date':field==='execution_percentage'?'number':'text'} inputProps={field==='execution_percentage'?{min:0,max:100}:undefined}/>;
  };
  const toggleCollapsed=(activityId:number)=>setCollapsed(current=>{const next=new Set(current);next.has(activityId)?next.delete(activityId):next.add(activityId);return next});
  const recalculate=useMutation({mutationFn:()=>api.post<Activity[]>(`${collectionPath}/recalculate`),onSuccess:async()=>{setError('');await refreshProgress()},onError:(err:any)=>setError(err.response?.data?.detail||'Nao foi possivel ajustar as dependencias.')});
  const adjustOne=useMutation({mutationFn:({item,predecessor}:{item:Activity;predecessor:Activity})=>{const days=duration(item.start_date,item.finish_date);const start=nextBusinessDay(predecessor.finish_date);return api.put(`/activities/${item.id}`,{name:item.name,start_date:start,finish_date:finishForBusinessDays(start,days),resource_names:item.resource_names,execution_percentage:item.execution_percentage,planned_value:item.planned_value,actual_value:item.actual_value,delivery_status:item.delivery_status,predecessor_id:item.predecessor_id})},onSuccess:()=>refreshProgress(),onError:(err:any)=>setError(err.response?.data?.detail||'Nao foi possivel ajustar a atividade.')});
  const adjustForm=()=>{if(!selectedPredecessor)return;const days=duration(form.start_date||selectedPredecessor.finish_date,form.finish_date||form.start_date||selectedPredecessor.finish_date);const start=nextBusinessDay(selectedPredecessor.finish_date);setForm({...form,start_date:start,finish_date:finishForBusinessDays(start,days)});setError('')};
  const submit=()=>{setError('');if(!form.name.trim()||!form.start_date||!form.finish_date){setError('Informe o nome, a data de inicio e a data de termino.');return}if(formConflict){setError('A atividade sucessora deve iniciar depois do termino da predecessora. Use Ajustar datas.');return}save.mutate()};
  const removeItem=(item:Activity)=>{if(window.confirm(`Excluir a atividade "${item.name}"?`))remove.mutate(item.id)};
  const targetBelongsToBlock=(sourceId:number,targetId:number)=>{let current=byId.get(targetId);const visited=new Set<number>();while(current&&!visited.has(current.id)){if(current.id===sourceId)return true;visited.add(current.id);current=current.parent_id?byId.get(current.parent_id):undefined}return false};
  const dropPositionFor=(event:DragEvent<HTMLTableRowElement>,source:Activity,target:Activity):DropPosition=>{const rect=event.currentTarget.getBoundingClientRect();const ratio=(event.clientY-rect.top)/rect.height;if(source.depth>target.depth&&(target.is_summary||target.depth===0)&&ratio>=.25&&ratio<=.75)return'inside';return ratio<.5?'before':'after'};
  const dragSourceId=(event:DragEvent<HTMLElement>)=>{const transferred=Number(event.dataTransfer.getData('text/plain'));return Number.isInteger(transferred)&&transferred>0?transferred:draggedIdRef.current};
  const dragStart=(event:DragEvent<HTMLElement>,item:Activity)=>{if(reorder.isPending){event.preventDefault();return}setInlineEdit(null);draggedIdRef.current=item.id;setDraggedId(item.id);setDragOver(null);event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',String(item.id))};
  const dragOverRow=(event:DragEvent<HTMLTableRowElement>,target:Activity)=>{const sourceId=draggedIdRef.current;if(sourceId===null||targetBelongsToBlock(sourceId,target.id)){setDragOver(null);return}const source=byId.get(sourceId);if(!source){setDragOver(null);return}event.preventDefault();event.dataTransfer.dropEffect='move';const position=dropPositionFor(event,source,target);setDragOver(current=>current?.id===target.id&&current.position===position?current:{id:target.id,position})};
  const dropRow=(event:DragEvent<HTMLTableRowElement>,target:Activity)=>{event.preventDefault();event.stopPropagation();const sourceId=dragSourceId(event);const source=sourceId===null?undefined:byId.get(sourceId);if(!source||targetBelongsToBlock(source.id,target.id)){setDragOver(null);return}const position=dropPositionFor(event,source,target);reorder.mutate({activityId:source.id,targetId:target.id,position})};
  const dragEnd=()=>{draggedIdRef.current=null;if(!reorder.isPending){setDraggedId(null);setDragOver(null)}};
  if(subproject.isLoading)return <Skeleton variant="rounded" height={500}/>;
  if(subproject.isError||!subproject.data)return <Alert severity="error">Subprojeto nao encontrado.</Alert>;
  const s=subproject.data;
  return <Box>
    <Breadcrumbs sx={{mb:2}}>
<MuiLink component={Link} to="/">Dashboard</MuiLink>
<MuiLink component={Link} to="/subprojetos">Subprojetos</MuiLink>
<Typography>{official?'Cronograma do Projeto':'Milestones'}</Typography>
</Breadcrumbs>
    <Stack direction={{xs:'column',sm:'row'}} justifyContent="space-between" alignItems={{sm:'center'}} gap={2} mb={3}>
<Box>
<Stack direction="row" gap={1.2} alignItems="center">
<CalendarMonthOutlined color="primary" sx={{fontSize:34}}/>
<Typography variant="h4">{official?'Cronograma do Projeto':'Milestones'}</Typography>
</Stack>
<Typography color="text.secondary">{s.project_name} → {s.name}</Typography>
</Box>
<Stack direction="row" gap={1} flexWrap="wrap">
<Button startIcon={<ArrowBack/>} onClick={()=>navigate(`/subprojetos/${id}`)}>Voltar</Button>{conflicts.length>0&&<Button color="warning" variant="outlined" startIcon={<AutoFixHighOutlined/>} disabled={recalculate.isPending} onClick={()=>recalculate.mutate()}>Ajustar dependencias ({conflicts.length})</Button>}{official&&<Button variant="outlined" startIcon={<CloudDownloadOutlined/>} onClick={()=>{setCffResult('');setCffParentId('');setCffOpen(true)}}>Importar CFF</Button>}<Button variant="contained" startIcon={<Add/>} onClick={showCreate}>{official?'Nova atividade':'Novo milestone'}</Button>
</Stack>
</Stack>
    {conflicts.length>0&&<Alert severity="warning" sx={{mb:2}} action={<Button color="inherit" size="small" startIcon={<AutoFixHighOutlined/>} onClick={()=>recalculate.mutate()}>Recalcular</Button>}>Existem {conflicts.length} atividade(s) iniciando antes ou no mesmo dia do termino da predecessora. O ajuste preserva a duracao e propaga as datas pela cadeia.</Alert>}
    {error&&!open&&<Alert severity="error" onClose={()=>setError('')} sx={{mb:2}}>{error}</Alert>}
{official?<Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'1fr 1fr'},gap:2,mb:2}}>
<Card>
<CardContent>
<Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
<Typography fontWeight={850}>Execucao do projeto</Typography>
<Typography variant="h5" fontWeight={900} color="primary.main">{project.data?.progress??0}%</Typography>
</Stack>
<LinearProgress variant="determinate" value={project.data?.progress??0} sx={{height:9,borderRadius:5}}/>
<Typography variant="caption" color="text.secondary">Media ponderada pelo escopo das atividades do cronograma oficial.</Typography>
</CardContent>
</Card>
<Card>
<CardContent>
<Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
<Typography fontWeight={850}>Execucao do subprojeto</Typography>
<Typography variant="h5" fontWeight={900} color="secondary.main">{s.execution_percentage}%</Typography>
</Stack>
<LinearProgress color="secondary" variant="determinate" value={s.execution_percentage} sx={{height:9,borderRadius:5}}/>
<Typography variant="caption" color="text.secondary">Consolidacao das atividades oficiais deste subprojeto.</Typography>
</CardContent>
</Card>
</Box>:<Alert severity="info" sx={{mb:2}}>Cronograma independente de marcos, utilizado como fonte para o relatorio semanal. Seus percentuais nao alteram a execucao oficial do projeto.</Alert>}
    <Card>
<CardContent sx={{p:0}}>
<Box sx={{px:2,py:1,bgcolor:'#f8fafc',borderBottom:'1px solid',borderColor:'divider'}}>
<Typography variant="caption" color="text.secondary">Clique diretamente em uma célula para editar. Arraste pela EAP para reordenar; solte no centro de outro entregável para mudar o vínculo. Atividades pai levam todo o bloco.</Typography>
</Box>
<TableContainer>
<Table size="small">
<TableHead>
<TableRow sx={{bgcolor:'#eef3f8'}}>
<TableCell sx={{fontWeight:900,width:100}}>EAP</TableCell>
<TableCell sx={{fontWeight:900,minWidth:280}}>Nome</TableCell>
<TableCell sx={{fontWeight:900,width:100}}>Duracao</TableCell>
<TableCell sx={{fontWeight:900,width:120}}>Inicio</TableCell>
<TableCell sx={{fontWeight:900,width:120}}>Termino</TableCell>
<TableCell sx={{fontWeight:900,minWidth:180}}>Recursos</TableCell>
<TableCell sx={{fontWeight:900,width:145}}>Previsto</TableCell>
<TableCell sx={{fontWeight:900,width:145}}>Realizado</TableCell>
<TableCell sx={{fontWeight:900,width:150}}>Execucao</TableCell>
<TableCell sx={{fontWeight:900,width:130}}>Predecessoras</TableCell>
<TableCell sx={{fontWeight:900,width:245}} align="right">Acoes</TableCell>
</TableRow>
</TableHead>
<TableBody>
      <TableRow sx={{bgcolor:'#f7f9fc'}}>
<TableCell>
<strong>1</strong>
</TableCell>
<TableCell>
<Typography fontWeight={900}>{s.project_name}</Typography>
</TableCell>
<TableCell/>
<TableCell/>
<TableCell/>
<TableCell/>
<TableCell/>
<TableCell/>
<TableCell>
<Stack direction="row" alignItems="center" gap={1}>
<LinearProgress variant="determinate" value={projectRowProgress} sx={{width:75,height:7,borderRadius:4}}/>
<Typography fontWeight={900}>{projectRowProgress}%</Typography>
</Stack>
</TableCell>
<TableCell/>
<TableCell/>
</TableRow>
      <TableRow sx={{bgcolor:'#fbfcfe'}}>
<TableCell>
<strong>{s.wbs_code}</strong>
</TableCell>
<TableCell>
<Typography fontWeight={900} sx={{pl:2}}>{s.name}</Typography>
</TableCell>
<TableCell/>
<TableCell/>
<TableCell/>
<TableCell/>
<TableCell/>
<TableCell/>
<TableCell>
<Stack direction="row" alignItems="center" gap={1}>
<LinearProgress color="secondary" variant="determinate" value={subprojectRowProgress} sx={{width:75,height:7,borderRadius:4}}/>
<Typography fontWeight={900}>{subprojectRowProgress}%</Typography>
</Stack>
</TableCell>
<TableCell/>
<TableCell/>
</TableRow>
      {activities.isLoading?<TableRow>
<TableCell colSpan={11}>
<Skeleton height={45}/>
</TableCell>
</TableRow>:items.length?visibleItems.map(item=>{
        const predecessor=item.predecessor_id?byId.get(item.predecessor_id):null;
        const invalid=Boolean(predecessor&&item.start_date<nextBusinessDay(predecessor.finish_date));
        const editingField=(field:EditableField)=>inlineEdit?.activityId===item.id&&inlineEdit.field===field;
        const editableSx={cursor:'text','&:hover':{bgcolor:'action.hover'}};
        const dropPosition=dragOver?.id===item.id?dragOver.position:null;
        const baseBackground=item.is_summary?'#f4f7fa':invalid?'#fff8e1':undefined;
        return <TableRow key={item.id} hover onDragOver={event=>dragOverRow(event,item)} onDrop={event=>dropRow(event,item)} sx={{bgcolor:dropPosition==='inside'?'rgba(13, 71, 128, .11)':baseBackground,opacity:draggedBlockIds.has(item.id)?.48:1,transition:'opacity .15s, background-color .15s',...(dropPosition==='before'?{'& > td':{borderTop:'3px solid',borderTopColor:'primary.main'}}:{}),...(dropPosition==='after'?{'& > td':{borderBottom:'3px solid',borderBottomColor:'primary.main'}}:{}),...(dropPosition==='inside'?{'& > td:first-of-type':{borderLeft:'4px solid',borderLeftColor:'primary.main'}}:{})}}>
          <TableCell><Stack direction="row" alignItems="center" gap={.5}><Tooltip title={item.is_summary?'Arrastar atividade e todo o bloco':'Arrastar atividade'}><Box component="span" draggable={!reorder.isPending} onDragStart={event=>dragStart(event,item)} onDragEnd={dragEnd} sx={{display:'inline-flex',color:'text.secondary',cursor:reorder.isPending?'wait':'grab','&:active':{cursor:'grabbing'}}}><DragIndicatorOutlined fontSize="small"/></Box></Tooltip>{item.wbs_code}</Stack></TableCell>
          <TableCell onClick={()=>!editingField('name')&&startInline(item,'name')} sx={editableSx}>
            {editingField('name')?inlineEditor(item,'name'):<Stack direction="row" alignItems="center" gap={.5} sx={{pl:1+item.depth*3}}>{item.is_summary?<IconButton size="small" onClick={event=>{event.stopPropagation();toggleCollapsed(item.id)}}>{collapsed.has(item.id)?<ChevronRight fontSize="small"/>:<ExpandMore fontSize="small"/>}</IconButton>:<Box sx={{width:28}}/>}{invalid&&<Tooltip title="Conflito de dependencia">
<WarningAmberOutlined color="warning" fontSize="small"/>
</Tooltip>}<Typography fontWeight={item.is_summary?900:650}>{item.name}</Typography>
</Stack>}
          </TableCell>
          <TableCell title="Calculada automaticamente">{item.duration_days}d</TableCell>
          <TableCell onClick={()=>!editingField('start_date')&&startInline(item,'start_date')} sx={item.is_summary?undefined:{...editableSx,...(invalid?{color:'error.main',fontWeight:800}: {})}}>{editingField('start_date')?inlineEditor(item,'start_date'):date(item.start_date)}</TableCell>
          <TableCell onClick={()=>!editingField('finish_date')&&startInline(item,'finish_date')} sx={item.is_summary?undefined:editableSx}>{editingField('finish_date')?inlineEditor(item,'finish_date'):date(item.finish_date)}</TableCell>
          <TableCell onClick={()=>!editingField('resource_names')&&startInline(item,'resource_names')} sx={editableSx}>{editingField('resource_names')?inlineEditor(item,'resource_names'):(item.resource_names||'-')}</TableCell>
          <TableCell onClick={()=>!editingField('planned_value')&&startInline(item,'planned_value')} sx={item.is_summary?undefined:editableSx}>{editingField('planned_value')?inlineEditor(item,'planned_value'):money(item.planned_value)}</TableCell>
          <TableCell onClick={()=>!editingField('actual_value')&&startInline(item,'actual_value')} sx={item.is_summary?undefined:editableSx}>{editingField('actual_value')?inlineEditor(item,'actual_value'):money(item.actual_value)}</TableCell>
          <TableCell onClick={()=>!editingField('execution_percentage')&&startInline(item,'execution_percentage')} sx={item.is_summary?undefined:editableSx}>{editingField('execution_percentage')?inlineEditor(item,'execution_percentage'):<Stack direction="row" alignItems="center" gap={1}>
<LinearProgress variant="determinate" value={item.execution_percentage} sx={{width:75,height:7,borderRadius:4}}/>
<Typography variant="caption" fontWeight={800}>{item.execution_percentage}%</Typography>
</Stack>}</TableCell>
          <TableCell onClick={()=>!editingField('predecessor_id')&&startInline(item,'predecessor_id')} sx={item.is_summary?undefined:editableSx}>{editingField('predecessor_id')?inlineEditor(item,'predecessor_id'):(item.predecessor_wbs||'-')}</TableCell>
          <TableCell align="right">{invalid&&predecessor&&<Tooltip title="Ajustar para o dia posterior a predecessora">
<IconButton color="warning" onClick={()=>adjustOne.mutate({item,predecessor})}>
<AutoFixHighOutlined/>
</IconButton>
</Tooltip>}<Tooltip title="Desindentar">
<span>
<IconButton color="primary" disabled={item.depth===0||hierarchy.isPending} onClick={()=>hierarchy.mutate({activityId:item.id,action:'outdent'})}>
<FormatIndentDecreaseOutlined/>
</IconButton>
</span>
</Tooltip>
<Tooltip title="Identar sob a tarefa anterior">
<span>
<IconButton color="primary" disabled={!items.some(previous=>previous.sort_order<item.sort_order&&previous.depth===item.depth)||hierarchy.isPending} onClick={()=>hierarchy.mutate({activityId:item.id,action:'indent'})}>
<FormatIndentIncreaseOutlined/>
</IconButton>
</span>
</Tooltip>
<Tooltip title="Editar atividade">
<IconButton color="primary" onClick={()=>showEdit(item)}>
<EditOutlined/>
</IconButton>
</Tooltip>
<Tooltip title="Excluir atividade">
<IconButton color="error" onClick={()=>removeItem(item)}>
<DeleteOutline/>
</IconButton>
</Tooltip>
</TableCell>
        </TableRow>
      }):<TableRow>
<TableCell colSpan={11} sx={{py:6,textAlign:'center'}}>
<Typography fontWeight={800}>Nenhuma atividade cadastrada</Typography>
<Typography color="text.secondary" mb={2}>Adicione a primeira atividade ao cronograma deste subprojeto.</Typography>
<Button variant="outlined" startIcon={<Add/>} onClick={showCreate}>Adicionar atividade</Button>
</TableCell>
</TableRow>}
    </TableBody>
</Table>
</TableContainer>
</CardContent>
</Card>
    <Dialog open={cffOpen} onClose={()=>!importCff.isPending&&setCffOpen(false)} fullWidth maxWidth="xl">
      <DialogTitle>Importar Cronograma Físico-Financeiro (CFF)</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2}>
          <Alert severity="info">Origem: contratos vinculados ao subprojeto no Radar Financeiro-Orçamentário. Início e término recebem a Carta de Aprestamento. A execução será 100% somente quando a OB estiver confirmada, ativa e com rateio financeiro válido. OB apenas informada no CFF, cancelada, devolvida ou com rateio divergente permanece em 0%.</Alert>
          <TextField select required label="Importar abaixo de" value={cffParentId} onChange={event=>setCffParentId(event.target.value?Number(event.target.value):'')} helperText="Escolha a entrega ou atividade da EAP que receberá as etapas do CFF como subtarefas.">
            <MenuItem value=""><em>Selecione o local na EAP</em></MenuItem>
            {cffParents.map(item=><MenuItem key={item.id} value={item.id}><Box component="span" sx={{pl:item.depth*2}}>{item.wbs_code} — {item.name}</Box></MenuItem>)}
          </TextField>
          {cff.isLoading?<Skeleton variant="rounded" height={260}/>:cff.isError?<Alert severity="error">Não foi possível consultar o CFF no Radar Financeiro.</Alert>:cff.data?.linked_contracts===0?<Alert severity="warning">Este subprojeto não possui contratos vinculados. Vincule um contrato antes de importar o CFF.</Alert>:cff.data?.cff_files===0?<Alert severity="warning">Nenhum CFF ativo foi localizado para os contratos vinculados.</Alert>:<>
            <Stack direction="row" gap={1} flexWrap="wrap"><Chip label={`${cff.data?.linked_contracts||0} contrato(s) vinculado(s)`}/><Chip label={`${cff.data?.cff_files||0} CFF ativo(s)`}/><Chip color="primary" label={`${selectedCff.size} etapa(s) selecionada(s)`}/></Stack>
            <TableContainer sx={{maxHeight:480,border:'1px solid',borderColor:'divider',borderRadius:2}}><Table stickyHeader size="small"><TableHead><TableRow><TableCell padding="checkbox"><Checkbox checked={importableCff.length>0&&selectedCff.size===importableCff.length} indeterminate={selectedCff.size>0&&selectedCff.size<importableCff.length} onChange={toggleAllCff}/></TableCell><TableCell>Etapa</TableCell><TableCell>Nome da atividade</TableCell><TableCell>Valor previsto</TableCell><TableCell>Valor pago</TableCell><TableCell>Início importado</TableCell><TableCell>Término importado</TableCell><TableCell>Ordem Bancária</TableCell><TableCell>Validação</TableCell><TableCell>Execução</TableCell></TableRow></TableHead><TableBody>{cff.data?.stages.map(stage=><TableRow key={stage.id} hover selected={selectedCff.has(stage.id)}><TableCell padding="checkbox"><Checkbox checked={selectedCff.has(stage.id)} onChange={()=>toggleCff(stage.id)}/></TableCell><TableCell>{stage.stage_number||'-'}</TableCell><TableCell sx={{minWidth:320}}>{stage.name}</TableCell><TableCell>{money(stage.stage_value)}</TableCell><TableCell>{money(stage.paid_value)}</TableCell><TableCell>{date(stage.import_start_date)}</TableCell><TableCell>{date(stage.import_finish_date)}</TableCell><TableCell>{stage.bank_order||'-'}</TableCell><TableCell><Tooltip title={stage.payment_message}><Chip size="small" color={stage.payment_status==='CONFIRMADA'?'success':stage.payment_status==='DIVERGENTE'?'error':'warning'} label={stage.payment_status.replaceAll('_',' ')}/></Tooltip></TableCell><TableCell><Chip size="small" color={stage.execution_percentage===100?'success':'default'} label={`${stage.execution_percentage}%`}/></TableCell></TableRow>)}</TableBody></Table></TableContainer>
          </>}
          {cffResult&&<Alert severity={cffResult.startsWith('Nao')||cffResult.startsWith('Não')?'error':'success'}>{cffResult}</Alert>}
        </Stack>
      </DialogContent>
      <DialogActions><Button onClick={()=>setCffOpen(false)} disabled={importCff.isPending}>Fechar</Button><Button variant="contained" startIcon={<CloudDownloadOutlined/>} disabled={selectedCff.size===0||!cffParentId||importCff.isPending} onClick={()=>importCff.mutate()}>{importCff.isPending?'Importando...':'Importar selecionadas'}</Button></DialogActions>
    </Dialog>
    <Dialog open={open} onClose={close} fullWidth maxWidth="md">
<DialogTitle>{editing?'Editar atividade':'Nova atividade'}</DialogTitle>
<DialogContent dividers>
<Stack spacing={2} pt={1}>
<TextField autoFocus label="Nome da atividade *" value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/>
<Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'1fr 1fr'},gap:2}}>
<TextField label="Inicio *" type="date" InputLabelProps={{shrink:true}} value={form.start_date} onChange={e=>setForm({...form,start_date:e.target.value})} onFocus={()=>{formDuration.current=form.start_date&&form.finish_date?duration(form.start_date,form.finish_date):0}} onBlur={e=>{const start=e.currentTarget.value;if(start&&form.finish_date&&start>form.finish_date)setForm(current=>({...current,start_date:start,finish_date:finishForBusinessDays(start,Math.max(1,formDuration.current))}))}}/>
<TextField label="Termino *" type="date" InputLabelProps={{shrink:true}} value={form.finish_date} onChange={e=>setForm({...form,finish_date:e.target.value})}/>
</Box>
<TextField label="Nomes dos recursos" placeholder="Ex.: Equipe SAD, empresa contratada" value={form.resource_names||''} onChange={e=>setForm({...form,resource_names:e.target.value||null})}/>
<Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'1fr 1fr'},gap:2}}>
<TextField label="Previsto" type="number" inputProps={{min:0,step:.01}} InputProps={{startAdornment:<InputAdornment position="start">R$</InputAdornment>}} value={form.planned_value} onChange={e=>setForm({...form,planned_value:Math.max(0,Number(e.target.value)||0)})}/>
<TextField label="Realizado" type="number" inputProps={{min:0,step:.01}} InputProps={{startAdornment:<InputAdornment position="start">R$</InputAdornment>}} value={form.actual_value} onChange={e=>setForm({...form,actual_value:Math.max(0,Number(e.target.value)||0)})}/>
</Box>
<Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:'.65fr 1fr 1.35fr'},gap:2}}>
<TextField label="Execução (%)" type="number" inputProps={{min:0,max:100}} value={form.execution_percentage} onChange={e=>setForm({...form,execution_percentage:Math.max(0,Math.min(100,Number(e.target.value)))})}/>
<TextField select label="Situação da entrega" value={form.delivery_status} onChange={e=>setForm({...form,delivery_status:e.target.value as ActivityInput['delivery_status']})} SelectProps={{renderValue:value=>{const option=deliveryStatusOptions.find(item=>item.value===value);return option?<Stack direction="row" alignItems="center" gap={1} sx={{color:option.color}}>{option.icon}<Typography color="text.primary">{option.label}</Typography></Stack>:String(value)}}}>{deliveryStatusOptions.map(option=><MenuItem key={option.value} value={option.value}><Stack direction="row" alignItems="center" gap={1.2} sx={{color:option.color}}>{option.icon}<Typography color="text.primary">{option.label}</Typography></Stack></MenuItem>)}</TextField>
<TextField select label="Atividade predecessora" value={form.predecessor_id||''} onChange={e=>setForm({...form,predecessor_id:e.target.value?Number(e.target.value):null})}>
<MenuItem value="">Nenhuma</MenuItem>{items.filter(item=>item.id!==editing?.id&&!item.is_summary).map(item=>
<MenuItem key={item.id} value={item.id}>{item.wbs_code} - {item.name}</MenuItem>)}</TextField>
</Box>{formConflict&&selectedPredecessor&&<Alert severity="warning" action={<Button color="inherit" size="small" startIcon={<AutoFixHighOutlined/>} onClick={adjustForm}>Ajustar datas</Button>}>A predecessora termina em {date(selectedPredecessor.finish_date)}. O inicio minimo desta atividade e {date(nextBusinessDay(selectedPredecessor.finish_date))}.</Alert>}{error&&<Alert severity="error">{error}</Alert>}</Stack>
</DialogContent>
<DialogActions>
<Button onClick={close}>Cancelar</Button>
<Button variant="contained" startIcon={<SaveOutlined/>} disabled={save.isPending} onClick={submit}>{save.isPending?'Salvando...':'Salvar atividade'}</Button>
</DialogActions>
</Dialog>
  </Box>;
}
