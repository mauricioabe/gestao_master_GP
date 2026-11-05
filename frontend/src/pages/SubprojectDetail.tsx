import {useEffect,useMemo,useRef,useState} from 'react';
import {AccountTreeOutlined,ArrowBack,AssessmentOutlined,CalendarMonthOutlined,CancelOutlined,CheckCircleOutline,DescriptionOutlined,EditOutlined,EventNoteOutlined,FilterAltOutlined,Inventory2Outlined,PaymentsOutlined,PendingActionsOutlined,PersonOutline,PlayCircleOutline,ScheduleOutlined,ShieldOutlined,TrendingUpOutlined,ViewSidebarOutlined,WarningAmberOutlined} from '@mui/icons-material';
import {Alert,Box,Breadcrumbs,Button,Card,CardContent,Chip,Dialog,DialogActions,DialogContent,DialogTitle,Divider,InputAdornment,LinearProgress,Link as MuiLink,MenuItem,Pagination,Skeleton,Stack,TextField,Tooltip,Typography} from '@mui/material';
import {useQuery} from '@tanstack/react-query';
import {Link,useNavigate,useParams} from 'react-router-dom';
import {Activity,api,CffPreview,Subproject} from '../api';
import StatusChip from '../components/StatusChip';
import SubprojectContracts from '../components/SubprojectContracts';

const DAY=86_400_000;
const date=(value:string|null)=>value?new Intl.DateTimeFormat('pt-BR',{timeZone:'UTC'}).format(new Date(`${value}T00:00:00Z`)):'Não informada';
const money=(value:number|string|null)=>value==null?'Não informado':new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(value));
const utc=(value:string)=>new Date(`${value}T00:00:00Z`);
const iso=(value:Date)=>value.toISOString().slice(0,10);
const currentDate=()=>{const now=new Date();return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`};
const monday=(value:Date)=>{const result=new Date(value);const day=result.getUTCDay();result.setUTCDate(result.getUTCDate()-(day===0?6:day-1));return result};
const addDays=(value:Date,days:number)=>{const result=new Date(value);result.setUTCDate(result.getUTCDate()+days);return result};
const clamp=(value:number,min:number,max:number)=>Math.max(min,Math.min(max,value));

function Info({icon,label,value}:{icon:React.ReactNode;label:string;value:React.ReactNode}){return <Stack direction="row" gap={1.2}>
  <Box color="primary.main">{icon}</Box><Box><Typography variant="caption" color="text.secondary" fontWeight={800}>{label}</Typography><Typography fontWeight={750}>{value||'Não informado'}</Typography></Box>
</Stack>}

type Report={id:'schedule'|'performance'|'financial';title:string;summary:string;detail:string;severity:'success'|'warning'|'error'|'info';value:string;items:string[]};

function Kpi({label,value,helper,icon,color='#0a3b72',compactValue=false}:{label:string;value:string;helper:string;icon:React.ReactNode;color?:string;compactValue?:boolean}){return <Card sx={{height:'100%',position:'relative',overflow:'hidden','&:before':{content:'""',position:'absolute',inset:'0 auto 0 0',width:4,bgcolor:color}}}>
  <CardContent sx={{p:'18px!important'}}><Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1}><Box minWidth={0}><Typography variant="caption" color="text.secondary" fontWeight={850} textTransform="uppercase" letterSpacing={.5}>{label}</Typography><Typography variant="h5" mt={.4} sx={compactValue?{fontSize:{xs:17,sm:18,lg:17,xl:19},lineHeight:1.25,whiteSpace:'nowrap',letterSpacing:'-.02em'}:undefined}>{value}</Typography><Typography variant="caption" color="text.secondary">{helper}</Typography></Box><Box sx={{width:38,height:38,borderRadius:2,display:'grid',placeItems:'center',color,backgroundColor:`${color}12`,flexShrink:0}}>{icon}</Box></Stack></CardContent>
</Card>}

function WeeklyGantt({activities,subproject,reportsVisible,onToggleReports}:{activities:Activity[];subproject:Subproject;reportsVisible:boolean;onToggleReports:()=>void}){
  const scrollRef=useRef<HTMLDivElement|null>(null);
  const [page,setPage]=useState(1);
  const [statusFilter,setStatusFilter]=useState<'TODAS'|Activity['delivery_status']>('TODAS');
  const todayIso=currentDate();
  const today=utc(todayIso);
  const allRows=activities.filter(activity=>!activity.is_summary);
  const activityStatus=(activity:Activity):Activity['delivery_status']=>activity.delivery_status||(activity.execution_percentage===100?'ENCERRADA':activity.execution_percentage>0?'EM_EXECUCAO':'EM_PLANEJAMENTO');
  const rows=statusFilter==='TODAS'?allRows:allRows.filter(activity=>activityStatus(activity)===statusFilter);
  const statusOptions=[{value:'TODAS' as const,label:'Todas as situações'},{value:'ENCERRADA' as const,label:'Encerrada'},{value:'EM_EXECUCAO' as const,label:'Em execução'},{value:'CANCELADA' as const,label:'Cancelada'},{value:'EM_PLANEJAMENTO' as const,label:'Em planejamento'}];
  const pageSize=18;
  const pageCount=Math.max(1,Math.ceil(rows.length/pageSize));
  const range=useMemo(()=>{
    const starts=(allRows.length?allRows.map(row=>row.start_date):[todayIso]).map(utc);
    const start=new Date(Math.min(...starts.map(Number)));
    const finishes=[todayIso,subproject.planned_end_date,...allRows.map(row=>row.finish_date)].map(utc);
    const finish=addDays(monday(new Date(Math.max(...finishes.map(Number)))),6);
    const weeks=Math.max(1,Math.ceil((Number(finish)-Number(start)+DAY)/(7*DAY)));
    return {start,finish,weeks};
  },[allRows,subproject.planned_end_date,todayIso]);
  const weekWidth=76;const labelWidth=390;const timelineWidth=range.weeks*weekWidth;
  const position=(value:string)=>(Number(utc(value))-Number(range.start))/(7*DAY)*weekWidth;
  const todayPosition=(Number(today)-Number(range.start))/(7*DAY)*weekWidth;
  const latestActivity=allRows.length?Math.max(...allRows.map(row=>Number(utc(row.finish_date)))):Number(today);
  const gapToToday=(Number(today)-latestActivity)/(7*DAY);
  const focusDate=latestActivity<Number(today)?(gapToToday<=26?(latestActivity+Number(today))/2:latestActivity):Number(today);
  const focusPosition=(focusDate-Number(range.start))/(7*DAY)*weekWidth;
  const visibleRows=rows.slice((page-1)*pageSize,page*pageSize);
  useEffect(()=>{if(page>pageCount)setPage(pageCount)},[page,pageCount]);
  useEffect(()=>setPage(1),[statusFilter]);
  useEffect(()=>{
    const container=scrollRef.current;
    if(!container||focusPosition<0||focusPosition>timelineWidth)return;
    container.scrollLeft=Math.max(0,labelWidth+focusPosition-container.clientWidth*.62);
  },[focusPosition,timelineWidth]);
  return <Card sx={{overflow:'hidden',width:'100%',maxWidth:'100%',minWidth:0,boxSizing:'border-box'}}>
    <CardContent sx={{p:0}}>
      <Stack direction={{xs:'column',sm:'row'}} justifyContent="space-between" gap={1} sx={{px:2.5,pt:2.3,pb:1.7}}>
        <Box><Typography variant="h6">Sprint</Typography><Typography variant="body2" color="text.secondary">Planejamento, avanço e desvios das atividades oficiais</Typography></Box>
        <Stack direction="row" gap={.75} alignItems="center" flexWrap="wrap"><TextField select size="small" label="Filtrar atividades" value={statusFilter} onChange={event=>setStatusFilter(event.target.value as typeof statusFilter)} sx={{minWidth:205,'& .MuiInputBase-root':{bgcolor:'#fff'}}} InputProps={{startAdornment:<InputAdornment position="start"><FilterAltOutlined sx={{fontSize:18,color:'primary.main'}}/></InputAdornment>}}>{statusOptions.map(option=><MenuItem key={option.value} value={option.value}>{option.label} ({option.value==='TODAS'?allRows.length:allRows.filter(activity=>activityStatus(activity)===option.value).length})</MenuItem>)}</TextField><Chip size="small" sx={{bgcolor:'#e9f2fc',color:'primary.main',fontWeight:800}} label={`${range.weeks} semanas`}/><Button size="small" startIcon={<ViewSidebarOutlined/>} onClick={onToggleReports}>{reportsVisible?'Ocultar reports':'Exibir reports'}</Button><Button component={Link} to={`/subprojetos/${subproject.id}/cronograma-projeto`} size="small" endIcon={<ArrowBack sx={{transform:'rotate(180deg)'}}/>}>Abrir cronograma</Button></Stack>
      </Stack>
      <Box ref={scrollRef} sx={{width:'100%',maxWidth:'100%',minWidth:0,overflowX:'auto',overflowY:'hidden',borderTop:'1px solid',borderColor:'divider',boxSizing:'border-box','&::-webkit-scrollbar':{height:10},'&::-webkit-scrollbar-track':{bgcolor:'#eef3f8',borderRadius:5},'&::-webkit-scrollbar-thumb':{bgcolor:'#9fb2c7',borderRadius:5,border:'2px solid #eef3f8'}}}>
        <Box sx={{minWidth:labelWidth+timelineWidth}}>
          <Box sx={{height:44,display:'flex',bgcolor:'#f6f9fc',borderBottom:'1px solid',borderColor:'divider'}}>
            <Box sx={{width:labelWidth,flexShrink:0,px:2,display:'flex',alignItems:'center',position:'sticky',left:0,zIndex:4,bgcolor:'#f6f9fc',borderRight:'1px solid #dfe7f0'}}><Typography variant="caption" fontWeight={900} color="text.secondary">ATIVIDADE</Typography></Box>
            <Box sx={{width:timelineWidth,position:'relative',display:'flex'}}>{Array.from({length:range.weeks},(_,index)=>{const start=addDays(range.start,index*7);return <Box key={index} sx={{width:weekWidth,flexShrink:0,px:1,display:'flex',flexDirection:'column',justifyContent:'center',borderRight:'1px solid #e3eaf2'}}><Typography variant="caption" fontWeight={900}>S{index+1}</Typography><Typography variant="caption" color="text.secondary" fontSize={10}>{date(iso(start))}</Typography></Box>})}</Box>
          </Box>
          {visibleRows.length?visibleRows.map((activity,index)=>{
            const left=position(activity.start_date);const width=Math.max(9,position(activity.finish_date)-left+weekWidth/7);
            const status=activityStatus(activity);
            const statusMeta={ENCERRADA:{label:'Encerrada',color:'#16805b'},EM_EXECUCAO:{label:'Em execução',color:'#2d6fac'},CANCELADA:{label:'Cancelada',color:'#667085'},EM_PLANEJAMENTO:{label:'Em planejamento',color:'#c78013'}}[status];
            const color=statusMeta.color;
            const statusIcon=status==='ENCERRADA'?<CheckCircleOutline/>:status==='EM_EXECUCAO'?<PlayCircleOutline/>:status==='CANCELADA'?<CancelOutlined/>:<PendingActionsOutlined/>;
            return <Box key={activity.id} sx={{height:60,display:'flex',borderBottom:index===visibleRows.length-1?0:'1px solid #edf1f5'}}>
              <Box sx={{width:labelWidth,flexShrink:0,px:2,display:'flex',alignItems:'center',gap:1,position:'sticky',left:0,zIndex:3,bgcolor:'#fff',borderRight:'1px solid #dfe7f0'}}><Typography variant="caption" color="text.secondary" sx={{width:48,flexShrink:0}}>{activity.wbs_code}</Typography><Tooltip title={statusMeta.label} arrow><Box sx={{display:'flex',color,width:20,flexShrink:0,'& svg':{fontSize:18}}}>{statusIcon}</Box></Tooltip><Tooltip title={<Box sx={{py:.5}}><Typography variant="body2" fontWeight={800} color="inherit">{activity.name}</Typography><Box sx={{display:'inline-flex',alignItems:'center',gap:.5,mt:.7,px:.8,py:.25,borderRadius:1,bgcolor:statusMeta.color,color:'#fff',fontSize:11,fontWeight:900}}><Box sx={{display:'flex','& svg':{fontSize:14}}}>{statusIcon}</Box>{statusMeta.label}</Box><Divider sx={{my:.8,borderColor:'rgba(255,255,255,.25)'}}/><Stack direction="row" gap={2}><Box><Typography variant="caption" sx={{color:'rgba(255,255,255,.7)'}}>Início</Typography><Typography variant="body2" fontWeight={700}>{date(activity.start_date)}</Typography></Box><Box><Typography variant="caption" sx={{color:'rgba(255,255,255,.7)'}}>Término</Typography><Typography variant="body2" fontWeight={700}>{date(activity.finish_date)}</Typography></Box></Stack><Divider sx={{my:.8,borderColor:'rgba(255,255,255,.25)'}}/><Stack direction="row" gap={2}><Box><Typography variant="caption" sx={{color:'rgba(255,255,255,.7)'}}>Valor previsto</Typography><Typography variant="body2" fontWeight={700}>{money(activity.planned_value)}</Typography></Box><Box><Typography variant="caption" sx={{color:'rgba(255,255,255,.7)'}}>Valor realizado</Typography><Typography variant="body2" fontWeight={700}>{money(activity.actual_value)}</Typography></Box></Stack></Box>} placement="right" arrow slotProps={{tooltip:{sx:{maxWidth:440,p:1.25}}}}><Typography variant="body2" fontWeight={750} sx={{lineHeight:1.25,display:'-webkit-box',WebkitLineClamp:2,WebkitBoxOrient:'vertical',overflow:'hidden',overflowWrap:'anywhere'}}>{activity.name}</Typography></Tooltip></Box>
              <Box sx={{width:timelineWidth,position:'relative',backgroundImage:'repeating-linear-gradient(90deg,transparent 0,transparent 75px,#edf1f5 75px,#edf1f5 76px)'}}>
                <Box title={`${activity.name}: ${date(activity.start_date)} a ${date(activity.finish_date)} · ${activity.execution_percentage}%`} sx={{position:'absolute',left,top:18,width,height:24,borderRadius:1.5,bgcolor:`${color}25`,border:`1px solid ${color}55`,overflow:'hidden',boxShadow:'0 2px 5px rgba(7,29,61,.08)'}}><Box sx={{height:'100%',width:`${activity.execution_percentage}%`,bgcolor:color,opacity:.88}}/><Typography variant="caption" sx={{position:'absolute',inset:0,display:'flex',alignItems:'center',px:1,color:activity.execution_percentage>52?'#fff':'#17324f',fontWeight:900,fontSize:10}}>{activity.execution_percentage}%</Typography></Box>
                {todayPosition>=0&&todayPosition<=timelineWidth&&<Box sx={{position:'absolute',left:todayPosition,top:0,bottom:0,width:2,bgcolor:'#d79a22',zIndex:2}}/>}
              </Box>
            </Box>}) : <Box sx={{py:6,textAlign:'center'}}><CalendarMonthOutlined color="disabled" sx={{fontSize:38}}/><Typography fontWeight={800}>{allRows.length?'Nenhuma atividade nesta situação':'Cronograma ainda não possui atividades'}</Typography><Typography variant="body2" color="text.secondary" mb={1.5}>{allRows.length?'Selecione outra situação para visualizar as atividades.':'Cadastre atividades para visualizar a distribuição semanal.'}</Typography>{allRows.length?<Button variant="outlined" size="small" onClick={()=>setStatusFilter('TODAS')}>Limpar filtro</Button>:<Button component={Link} to={`/subprojetos/${subproject.id}/cronograma-projeto`} variant="outlined" size="small">Montar cronograma</Button>}</Box>}
        </Box>
      </Box>
      {visibleRows.length>0&&<Stack direction={{xs:'column',md:'row'}} gap={1.5} justifyContent="space-between" alignItems={{xs:'flex-start',md:'center'}} sx={{px:2.5,py:1.5,borderTop:'1px solid',borderColor:'divider',bgcolor:'#fbfcfe'}}><Stack direction="row" gap={2} flexWrap="wrap">{[['#16805b','Encerrada'],['#2d6fac','Em execução'],['#667085','Cancelada'],['#c78013','Em planejamento'],['#d79a22','Hoje']].map(([color,label])=><Stack key={label} direction="row" gap={.7} alignItems="center"><Box sx={{width:9,height:9,borderRadius:'50%',bgcolor:color}}/><Typography variant="caption" color="text.secondary">{label}</Typography></Stack>)}</Stack><Stack direction={{xs:'column',sm:'row'}} gap={1.5} alignItems={{xs:'flex-start',sm:'center'}}><Typography variant="caption" color="text.secondary">Exibindo {(page-1)*pageSize+1}–{Math.min(page*pageSize,rows.length)} de {rows.length} atividades</Typography>{pageCount>1&&<Pagination count={pageCount} page={page} onChange={(_,nextPage)=>setPage(nextPage)} color="primary" size="small" shape="rounded" showFirstButton showLastButton aria-label="Paginação das atividades do Gantt"/>}</Stack></Stack>}
    </CardContent>
  </Card>;
}

function ImportantReports({reports,onOpen}:{reports:Report[];onOpen:(report:Report)=>void}){return <Card sx={{height:'100%'}}><CardContent sx={{p:2.5}}>
  <Stack direction="row" justifyContent="space-between" alignItems="center" mb={.5}><Box><Typography variant="h6">Reports importantes</Typography><Typography variant="body2" color="text.secondary">Análises que requerem acompanhamento</Typography></Box><DescriptionOutlined color="primary"/></Stack>
  <Stack spacing={1.2} mt={2}>{reports.map(report=>{const palette={success:'#16805b',warning:'#c78013',error:'#c33b3b',info:'#2d6fac'};const color=palette[report.severity];return <Box key={report.id} role="button" tabIndex={0} onClick={()=>onOpen(report)} onKeyDown={event=>(event.key==='Enter'||event.key===' ')&&onOpen(report)} sx={{p:1.5,border:'1px solid',borderColor:'#e2e9f1',borderLeft:`4px solid ${color}`,borderRadius:2,cursor:'pointer',transition:'.18s','&:hover':{transform:'translateY(-1px)',boxShadow:'0 6px 18px rgba(7,29,61,.09)',borderColor:'#cbd8e6'}}}>
    <Stack direction="row" justifyContent="space-between" gap={1}><Typography fontWeight={850}>{report.title}</Typography><Chip size="small" label={report.value} sx={{height:22,bgcolor:`${color}14`,color,fontWeight:900}}/></Stack><Typography variant="body2" color="text.secondary" mt={.5}>{report.summary}</Typography><Typography variant="caption" color="primary.main" fontWeight={850} mt={1} display="block">Visualizar report →</Typography>
  </Box>})}</Stack>
</CardContent></Card>}

export function SubprojectCockpit(){
  const {id}=useParams();const [report,setReport]=useState<Report|null>(null);const [reportsVisible,setReportsVisible]=useState(true);
  const item=useQuery({queryKey:['subproject',id],queryFn:()=>api.get<Subproject>(`/subprojects/${id}`).then(r=>r.data)});
  const cff=useQuery({queryKey:['cff',id],queryFn:()=>api.get<CffPreview>(`/subprojects/${id}/cff`).then(r=>r.data),enabled:Boolean(id)});
  const projectActivities=useQuery({queryKey:['activities','project',id],queryFn:()=>api.get<Activity[]>(`/subprojects/${id}/project-activities`).then(r=>r.data),enabled:Boolean(id)});
  if(item.isLoading)return <Skeleton variant="rounded" height={500}/>;
  if(item.isError||!item.data)return <Alert severity="error">Subprojeto não encontrado.</Alert>;
  const s=item.data;const activities=projectActivities.data||[];const operational=activities.filter(activity=>!activity.is_summary);const today=new Date().toISOString().slice(0,10);
  const delayed=operational.filter(activity=>activity.finish_date<today&&activity.execution_percentage<100);
  const completed=operational.filter(activity=>activity.execution_percentage===100).length;
  const cffBudget=cff.data?.stages.reduce((total,stage)=>total+Number(stage.stage_value||0),0)??null;
  const cffRealized=cff.data?.stages.reduce((total,stage)=>total+(stage.payment_status==='CONFIRMADA'?Number(stage.paid_value||0):0),0)??0;
  const cffFinancialProgress=cffBudget?(cffRealized/cffBudget)*100:0;
  const totalDays=Math.max(1,Math.round((Number(utc(s.planned_end_date))-Number(utc(s.planned_start_date)))/DAY)+1);
  const elapsedDays=clamp(Math.round((Number(utc(today))-Number(utc(s.planned_start_date)))/DAY)+1,0,totalDays);
  const elapsedPercentage=elapsedDays/totalDays*100;
  const scheduleVariance=s.execution_percentage-elapsedPercentage;
  const reports:Report[]=[
    {id:'schedule',title:'Saúde do cronograma',value:delayed.length?`${delayed.length} atraso${delayed.length>1?'s':''}`:'Em dia',severity:delayed.length?'error':'success',summary:delayed.length?'Há atividades com prazo vencido e execução pendente.':'Nenhuma atividade vencida foi identificada.',detail:'Atividades que exigem atenção imediata por desvio de prazo.',items:delayed.length?delayed.map(activity=>`${activity.wbs_code} · ${activity.name} — término em ${date(activity.finish_date)}, ${activity.execution_percentage}% concluído`):['Todas as atividades com prazo vencido estão concluídas.']},
    {id:'performance',title:'Ritmo de execução',value:`${s.execution_percentage}%`,severity:scheduleVariance<-10?'warning':'info',summary:scheduleVariance<-10?`Execução ${Math.abs(scheduleVariance).toFixed(0)} p.p. abaixo do tempo decorrido.`:`${completed} de ${operational.length} atividades concluídas.`,detail:'Comparação entre a execução informada e o percentual de tempo já consumido.',items:[`Execução consolidada: ${s.execution_percentage}%`,`Tempo planejado consumido: ${elapsedPercentage.toFixed(1)}%`,`Atividades concluídas: ${completed} de ${operational.length}`]},
    {id:'financial',title:'Posição financeira',value:cffBudget?`${cffFinancialProgress.toFixed(1)}%`:'Sem CFF',severity:cffBudget&&cffFinancialProgress<elapsedPercentage-20?'warning':'info',summary:cffBudget?`${money(cffRealized)} efetivamente pago de ${money(cffBudget)} previsto.`:'Não há base CFF disponível para consolidação.',detail:'Consolidação dos pagamentos confirmados e rateados nas etapas do CFF.',items:cffBudget?[`Previsto no CFF: ${money(cffBudget)}`,`Pago efetivamente: ${money(cffRealized)}`,`Índice pago/previsto: ${cffFinancialProgress.toFixed(1)}%`]:['Vincule contratos e importe o CFF para habilitar esta análise.']}
  ];
  return <Box>
    <Breadcrumbs sx={{mb:2}}><MuiLink component={Link} to="/">Dashboard</MuiLink><MuiLink component={Link} to="/subprojetos">Subprojetos</MuiLink><MuiLink component={Link} to={`/subprojetos/${s.id}`}>{s.name}</MuiLink><Typography>Cockpit</Typography></Breadcrumbs>
    <Stack direction={{xs:'column',md:'row'}} justifyContent="space-between" gap={2} mb={2.5}><Box><Stack direction="row" alignItems="center" gap={1} flexWrap="wrap"><Typography variant="h4">{s.name}</Typography><StatusChip status={s.status}/></Stack><Typography color="text.secondary">EAP {s.wbs_code} · Projeto {s.project_code}</Typography></Box><Stack direction="row" gap={1} flexWrap="wrap"><Button component={Link} to={`/subprojetos/${s.id}`} startIcon={<ArrowBack/>}>Informações</Button><Button component={Link} to={`/subprojetos/${s.id}/cronograma`} variant="outlined" startIcon={<EventNoteOutlined/>}>Milestones</Button><Button component={Link} to={`/subprojetos/${s.id}/cronograma-projeto`} variant="outlined" startIcon={<CalendarMonthOutlined/>}>Cronograma</Button><Button component={Link} to={`/subprojetos/${s.id}/editar`} variant="contained" startIcon={<EditOutlined/>}>Editar</Button></Stack></Stack>

    <Box sx={{p:{xs:2,md:2.5},mb:2.5,borderRadius:3,background:'linear-gradient(120deg,#fafdff 0%,#edf4fb 100%)',border:'1px solid #dbe6f1'}}><Stack direction={{xs:'column',md:'row'}} justifyContent="space-between" gap={2} alignItems={{md:'center'}}><Box><Typography variant="overline" color="primary.main" fontWeight={900} letterSpacing={1}>COCKPIT DO SUBPROJETO</Typography><Typography variant="h5">Visão executiva e temporal</Typography><Typography color="text.secondary" variant="body2">Atualizado com os dados oficiais do cronograma e do CFF</Typography></Box><Box sx={{minWidth:{md:320}}}><Stack direction="row" justifyContent="space-between"><Typography variant="body2" fontWeight={800}>Progresso consolidado</Typography><Typography fontWeight={900} color="primary.main">{s.execution_percentage}%</Typography></Stack><LinearProgress variant="determinate" value={s.execution_percentage} sx={{height:9,borderRadius:5,mt:.8,bgcolor:'#d9e4ef'}}/></Box></Stack></Box>

    <Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'repeat(2,1fr)',xl:'repeat(4,1fr)'},gap:1.5,mb:2.5}}><Kpi label="Período" value={`${date(s.planned_start_date)} — ${date(s.planned_end_date)}`} helper={`${Math.ceil(totalDays/7)} semanas planejadas`} icon={<CalendarMonthOutlined/>} compactValue/><Kpi label="Execução" value={`${s.execution_percentage}%`} helper={`${completed} de ${operational.length} atividades concluídas`} icon={<TrendingUpOutlined/>} color="#16805b"/><Kpi label="Situação do prazo" value={delayed.length?`${delayed.length} em atraso`:(s.schedule_status||'Em dia')} helper={`${elapsedPercentage.toFixed(0)}% do período consumido`} icon={delayed.length?<WarningAmberOutlined/>:<CheckCircleOutline/>} color={delayed.length?'#c33b3b':'#16805b'}/><Kpi label="Financeiro CFF" value={cffBudget?`${cffFinancialProgress.toFixed(1)}%`:'Sem dados'} helper={cffBudget?`${money(cffRealized)} pagos efetivamente`:'CFF ainda não consolidado'} icon={<PaymentsOutlined/>} color="#d79a22"/></Box>

    <Box sx={{display:'grid',width:'100%',maxWidth:'100%',minWidth:0,boxSizing:'border-box',gridTemplateColumns:{xs:'minmax(0,1fr)',xl:reportsVisible?'minmax(0,2.2fr) minmax(320px,.8fr)':'minmax(0,1fr)'},gap:2.5,mb:3,px:reportsVisible?0:{xs:.75,sm:1,lg:1.5}}}><WeeklyGantt activities={activities} subproject={s} reportsVisible={reportsVisible} onToggleReports={()=>setReportsVisible(visible=>!visible)}/>{reportsVisible&&<ImportantReports reports={reports} onOpen={setReport}/>}</Box>

    <Dialog open={Boolean(report)} onClose={()=>setReport(null)} fullWidth maxWidth="sm"><DialogTitle sx={{pb:1}}><Stack direction="row" gap={1.2} alignItems="center"><Box sx={{width:38,height:38,borderRadius:2,bgcolor:'#eaf2fc',color:'primary.main',display:'grid',placeItems:'center'}}>{report?.id==='schedule'?<ScheduleOutlined/>:report?.id==='financial'?<PaymentsOutlined/>:<TrendingUpOutlined/>}</Box><Box><Typography variant="h6">{report?.title}</Typography><Typography variant="caption" color="text.secondary">Report executivo · {date(today)}</Typography></Box></Stack></DialogTitle><DialogContent dividers><Typography color="text.secondary" mb={2}>{report?.detail}</Typography><Stack spacing={1}>{report?.items.map((line,index)=><Box key={index} sx={{p:1.5,borderRadius:2,bgcolor:'#f5f8fb',border:'1px solid #e4ebf2'}}><Typography variant="body2" fontWeight={700}>{line}</Typography></Box>)}</Stack></DialogContent><DialogActions><Button onClick={()=>setReport(null)}>Fechar</Button><Button component={Link} to={`/subprojetos/${s.id}/cronograma-projeto`} variant="contained" startIcon={<CalendarMonthOutlined/>}>Ver cronograma</Button></DialogActions></Dialog>
  </Box>;
}

export default function SubprojectDetail(){
  const {id}=useParams();const navigate=useNavigate();
  const item=useQuery({queryKey:['subproject',id],queryFn:()=>api.get<Subproject>(`/subprojects/${id}`).then(r=>r.data)});
  const cff=useQuery({queryKey:['cff',id],queryFn:()=>api.get<CffPreview>(`/subprojects/${id}/cff`).then(r=>r.data),enabled:Boolean(id)});
  if(item.isLoading)return <Skeleton variant="rounded" height={500}/>;
  if(item.isError||!item.data)return <Alert severity="error">Subprojeto não encontrado.</Alert>;
  const s=item.data;
  const cffBudget=cff.data?.stages.reduce((total,stage)=>total+Number(stage.stage_value||0),0)??null;
  const cffRealized=cff.data?.stages.reduce((total,stage)=>total+(stage.payment_status==='CONFIRMADA'?Number(stage.paid_value||0):0),0)??null;
  const cffFinancialProgress=cffBudget&&cffRealized!=null?(cffRealized/cffBudget)*100:0;
  return <Box>
    <Breadcrumbs sx={{mb:2}}><MuiLink component={Link} to="/">Dashboard</MuiLink><MuiLink component={Link} to="/subprojetos">Subprojetos</MuiLink><Typography>{s.name}</Typography></Breadcrumbs>
    <Stack direction={{xs:'column',md:'row'}} justifyContent="space-between" gap={2} mb={3}>
      <Box><Stack direction="row" alignItems="center" gap={1} flexWrap="wrap"><Typography variant="h4">{s.name}</Typography><StatusChip status={s.status}/></Stack><Typography color="text.secondary">EAP {s.wbs_code} · Projeto {s.project_code}</Typography></Box>
      <Stack direction="row" gap={1} flexWrap="wrap"><Button startIcon={<ArrowBack/>} onClick={()=>navigate('/subprojetos')}>Voltar</Button><Button component={Link} to={`/subprojetos/${s.id}/cockpit`} variant="outlined" startIcon={<AssessmentOutlined/>}>Cockpit</Button><Button component={Link} to={`/subprojetos/${s.id}/cronograma`} variant="outlined" startIcon={<EventNoteOutlined/>}>Milestones</Button><Button component={Link} to={`/subprojetos/${s.id}/cronograma-projeto`} variant="outlined" startIcon={<CalendarMonthOutlined/>}>Cronograma</Button><Button component={Link} to={`/subprojetos/${s.id}/editar`} variant="contained" startIcon={<EditOutlined/>}>Editar</Button></Stack>
    </Stack>
    <Stack direction="row" alignItems="center" gap={1} mb={1.5}><AssessmentOutlined color="primary"/><Typography variant="h5">Informações do subprojeto</Typography></Stack>
    <Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',lg:'1.4fr .8fr'},gap:2.5}}><Stack spacing={2.5}>
      <Card><CardContent><Typography variant="h6" mb={2}>Posição hierárquica</Typography><Stack direction="row" gap={1.5} alignItems="center"><Box sx={{p:1.5,borderRadius:2,bgcolor:'#eaf2fc'}}><AccountTreeOutlined color="primary"/></Box><Box><Typography fontWeight={900}>{s.project_name}</Typography><Typography color="text.secondary" variant="body2">Projeto {s.project_code} → {s.parent_name?`${s.parent_name} → `:''}{s.name}</Typography></Box></Stack></CardContent></Card>
      <Card><CardContent><Typography variant="h6" mb={2}>Objetivo e escopo</Typography><Typography fontWeight={800}>Objetivo</Typography><Typography sx={{whiteSpace:'pre-wrap'}}>{s.objective}</Typography><Divider sx={{my:2}}/><Typography fontWeight={800}>Escopo</Typography><Typography color={s.scope?'text.primary':'text.secondary'} sx={{whiteSpace:'pre-wrap'}}>{s.scope||'Não informado'}</Typography>{s.out_of_scope&&<><Typography fontWeight={800} mt={2}>Fora do escopo</Typography><Typography sx={{whiteSpace:'pre-wrap'}}>{s.out_of_scope}</Typography></>}</CardContent></Card>
      <SubprojectContracts subprojectId={s.id}/>
    </Stack><Stack spacing={2.5}><Card><CardContent><Stack spacing={2}><Info icon={<Inventory2Outlined/>} label="Produto principal" value={s.main_product}/><Info icon={<PersonOutline/>} label="Gerente" value={s.manager}/><Info icon={<ShieldOutlined/>} label="Unidade responsável" value={s.responsible_unit}/><Info icon={<PaymentsOutlined/>} label="Orçamento" value={money(s.budget)}/><Divider/><Typography variant="overline" color="text.secondary" fontWeight={900}>Indicadores financeiros do CFF</Typography><Info icon={<PaymentsOutlined/>} label="Previsto" value={cff.isLoading?'Carregando...':cff.isError?'Indisponível':money(cffBudget)}/><Info icon={<PaymentsOutlined/>} label="Pago efetivamente" value={cff.isLoading?'Carregando...':cff.isError?'Indisponível':money(cffRealized)}/>{cff.data&&<Box><Stack direction="row" justifyContent="space-between" mb={.6}><Typography variant="caption" color="text.secondary" fontWeight={800}>Pago sobre o previsto</Typography><Typography variant="caption" fontWeight={900}>{cffFinancialProgress.toLocaleString('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:1})}%</Typography></Stack><LinearProgress variant="determinate" value={Math.min(100,cffFinancialProgress)} sx={{height:7,borderRadius:4}}/></Box>}</Stack></CardContent></Card>{s.justification&&<Alert severity="warning"><Typography fontWeight={800}>Justificativa da situação</Typography>{s.justification}</Alert>}</Stack></Box>
  </Box>;
}
