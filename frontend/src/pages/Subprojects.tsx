import {useMemo,useState} from 'react';
import {AccountTreeOutlined,Add,CalendarMonthOutlined,DeleteOutline,EditOutlined,Search,VisibilityOutlined} from '@mui/icons-material';
import {Alert,Box,Breadcrumbs,Button,Card,CardContent,Dialog,DialogActions,DialogContent,DialogTitle,IconButton,InputAdornment,Link as MuiLink,MenuItem,Skeleton,Stack,Table,TableBody,TableCell,TableContainer,TableHead,TableRow,TextField,Tooltip,Typography} from '@mui/material';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {Link} from 'react-router-dom';
import {api,Project,Subproject} from '../api';
import StatusChip from '../components/StatusChip';


export default function Subprojects(){
  const queryClient=useQueryClient();
  const [projectId,setProjectId]=useState('');
  const [search,setSearch]=useState('');
  const [status,setStatus]=useState('');
  const [deleting,setDeleting]=useState<Subproject|null>(null);
  const projects=useQuery({queryKey:['projects'],queryFn:()=>api.get<Project[]>('/projects').then(r=>r.data)});
  const items=useQuery({queryKey:['subprojects',projectId,search,status],queryFn:()=>api.get<Subproject[]>('/subprojects',{params:{project_id:projectId||undefined,search:search||undefined,status:status||undefined}}).then(r=>r.data)});
  const grouped=useMemo(()=>{const map=new Map<number,Subproject[]>();for(const item of items.data||[])map.set(item.project_id,[...(map.get(item.project_id)||[]),item]);return map},[items.data]);
  const remove=useMutation({mutationFn:(id:number)=>api.delete(`/subprojects/${id}`),onSuccess:async()=>{setDeleting(null);await queryClient.invalidateQueries({queryKey:['subprojects']})}});
  return <Box>
    <Breadcrumbs sx={{mb:2}}>
<MuiLink component={Link} to="/">Dashboard</MuiLink>
<Typography>Subprojetos</Typography>
</Breadcrumbs>
    <Stack direction={{xs:'column',sm:'row'}} justifyContent="space-between" alignItems={{sm:'center'}} gap={2} mb={3}>
<Box>
<Typography variant="h4">Estrutura de Subprojetos</Typography>
<Typography color="text.secondary">Organizacao hierarquica EAP/WBS abaixo dos Projetos SAD/SISFRON.</Typography>
</Box>
<Button component={Link} to="/subprojetos/novo" variant="contained" startIcon={<Add/>}>Novo subprojeto</Button>
</Stack>
    <Card sx={{mb:2}}>
<CardContent sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:'1.2fr 1.5fr 1fr'},gap:1.5}}>
<TextField select label="Projeto SAD" value={projectId} onChange={e=>setProjectId(e.target.value)}>
<MenuItem value="">Todos os projetos</MenuItem>{projects.data?.map(p=>
<MenuItem key={p.id} value={p.id}>{p.code} — {p.name}</MenuItem>)}</TextField>
<TextField label="Buscar subprojeto" value={search} onChange={e=>setSearch(e.target.value)} InputProps={{startAdornment:<InputAdornment position="start">
<Search/>
</InputAdornment>}}/>
<TextField select label="Situacao" value={status} onChange={e=>setStatus(e.target.value)}>
<MenuItem value="">Todas</MenuItem>
<MenuItem value="PLANEJAMENTO">Planejamento</MenuItem>
<MenuItem value="EM_ANDAMENTO">Em andamento</MenuItem>
<MenuItem value="SUSPENSO">Suspenso</MenuItem>
<MenuItem value="ATRASADO">Atrasado</MenuItem>
<MenuItem value="CONCLUIDO">Concluido</MenuItem>
</TextField>
</CardContent>
</Card>
    {items.isError&&<Alert severity="error">Nao foi possivel carregar os subprojetos.</Alert>}
    {items.isLoading?<Skeleton variant="rounded" height={360}/>:!items.data?.length?<Card>
<CardContent sx={{py:8,textAlign:'center'}}>
<AccountTreeOutlined sx={{fontSize:58,color:'#9db0c4'}}/>
<Typography variant="h6" mt={1}>Nenhum subprojeto cadastrado</Typography>
<Typography color="text.secondary" mb={2}>Cadastre a primeira iniciativa subordinada a um Projeto SAD.</Typography>
<Button component={Link} to="/subprojetos/novo" variant="outlined" startIcon={<Add/>}>Cadastrar subprojeto</Button>
</CardContent>
</Card>:<Stack spacing={2}>{Array.from(grouped.entries()).map(([parentProjectId,children])=>{const project=projects.data?.find(p=>p.id===parentProjectId);return <Card key={parentProjectId}>
<CardContent sx={{p:0}}>
<Stack direction="row" alignItems="center" gap={1.2} sx={{p:2,bgcolor:'#edf4fc',borderBottom:'1px solid #dbe5f0'}}>
<AccountTreeOutlined color="primary"/>
<Box>
<Typography fontWeight={900}>{project?.name||children[0].project_name}</Typography>
<Typography variant="caption" color="text.secondary">EAP 1 · {project?.code||children[0].project_code}</Typography>
</Box>
<Box flex={1}/>
<Button component={Link} to={`/projetos/${parentProjectId}/subprojetos/novo`} size="small" startIcon={<Add/>}>Adicionar</Button>
</Stack>
<TableContainer>
<Table size="small">
<TableHead>
<TableRow>
<TableCell>EAP</TableCell>
<TableCell>Subprojeto</TableCell>
<TableCell>Situacao</TableCell>
<TableCell>Responsavel</TableCell>
<TableCell align="right">Acoes</TableCell>
</TableRow>
</TableHead>
<TableBody>{children.map(item=>{const depth=Math.max(0,item.wbs_code.split('.').length-2);return <TableRow key={item.id} hover>
<TableCell>
<Typography fontFamily="monospace" fontWeight={900}>{item.wbs_code}</Typography>
</TableCell>
<TableCell>
<Box sx={{pl:depth*3,borderLeft:depth?'2px solid #d4e1ef':'none'}}>
<MuiLink component={Link} to={`/subprojetos/${item.id}`} fontWeight={850} underline="hover">{item.short_name||item.name}</MuiLink>
</Box>
</TableCell>
<TableCell>
<StatusChip status={item.status}/>
</TableCell>
<TableCell>{item.manager}</TableCell>
<TableCell align="right">
<Tooltip title="Visualizar">
<IconButton component={Link} to={`/subprojetos/${item.id}`} color="primary">
<VisibilityOutlined/>
</IconButton>
</Tooltip>
<Tooltip title="Cronograma de atividades">
<IconButton component={Link} to={`/subprojetos/${item.id}/cronograma`} color="secondary">
<CalendarMonthOutlined/>
</IconButton>
</Tooltip>
<Tooltip title="Editar">
<IconButton component={Link} to={`/subprojetos/${item.id}/editar`} color="primary">
<EditOutlined/>
</IconButton>
</Tooltip>
<Tooltip title="Excluir">
<IconButton color="error" onClick={()=>setDeleting(item)}>
<DeleteOutline/>
</IconButton>
</Tooltip>
</TableCell>
</TableRow>})}</TableBody>
</Table>
</TableContainer>
</CardContent>
</Card>})}</Stack>}
    <Dialog open={Boolean(deleting)} onClose={()=>setDeleting(null)}>
<DialogTitle>Excluir subprojeto</DialogTitle>
<DialogContent>
<Typography>Confirma a exclusao de <strong>{deleting?.name}</strong>?</Typography>{deleting?.children_count?<Alert severity="warning" sx={{mt:2}}>Este item possui subordinados e so podera ser excluido depois deles.</Alert>:<Alert severity="info" sx={{mt:2}}>A exclusao e logica e preserva o historico.</Alert>}</DialogContent>
<DialogActions>
<Button onClick={()=>setDeleting(null)}>Cancelar</Button>
<Button color="error" variant="contained" disabled={remove.isPending||Boolean(deleting?.children_count)} onClick={()=>deleting&&remove.mutate(deleting.id)}>Excluir</Button>
</DialogActions>
</Dialog>
  </Box>;
}
