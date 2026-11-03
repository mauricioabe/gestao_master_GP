import {useState} from 'react';
import {Close,CloudSyncOutlined,VisibilityOutlined,WorkOutline} from '@mui/icons-material';
import {Alert,Autocomplete,Box,Card,CardContent,Chip,Dialog,DialogContent,DialogTitle,Divider,FormControlLabel,FormHelperText,IconButton,LinearProgress,Skeleton,Stack,Switch,TextField,Typography} from '@mui/material';
import {useQuery} from '@tanstack/react-query';
import {api,Contract,ContractOptions,SubprojectContract,SubprojectContracts as LinkedContracts} from '../api';

const money=(value:number|null|undefined)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(value||0));
const percent=(value:number,total:number|null)=>total?Math.min(100,(value/total)*100):0;
const date=(value:string|null|undefined)=>value?new Intl.DateTimeFormat('pt-BR',{timeZone:'UTC'}).format(new Date(`${value}T00:00:00Z`)):'-';
const period=(value:string|null)=>value?`${value.slice(5,7)}/${value.slice(0,4)}`:'sem periodo';
const label=(contract:Contract)=>`${contract.contract_number||contract.external_contract_id} — ${contract.supplier_name||'Fornecedor nao informado'}`;

function Amount({title,value,color}:{title:string;value:number;color:string}){return <Box sx={{p:1,borderRadius:2,border:'1px solid #e3e8ef',textAlign:'center'}}>
<Typography variant="caption" color="text.secondary">{title}</Typography>
<Typography fontWeight={900} color={color} sx={{fontSize:14}}>{money(value)}</Typography>
</Box>}

function Bar({title,value,color}:{title:string;value:number;color:'primary'|'secondary'|'success'}){return <Box>
<Stack direction="row" justifyContent="space-between"><Typography variant="caption">{title}</Typography><Typography variant="caption" fontWeight={800}>{value.toLocaleString('pt-BR',{maximumFractionDigits:1})}%</Typography></Stack>
<LinearProgress color={color} variant="determinate" value={value} sx={{height:6,borderRadius:3}}/>
</Box>}

function ContractCard({contract,onView}:{contract:SubprojectContract;onView:()=>void}){
  const base=contract.committed||0;
  return <Box sx={{p:2,borderRadius:2,border:'1px solid #dfe6ee'}}>
<Stack direction="row" alignItems="center" gap={.6} mb={1} color="primary.main"><CloudSyncOutlined sx={{fontSize:16}}/><Typography variant="caption" fontWeight={900} letterSpacing={.35}>RADAR FINANCEIRO-ORÇAMENTÁRIO</Typography></Stack>
<Stack direction="row" justifyContent="space-between" gap={1} mb={1}>
<Box minWidth={0}>
<Typography fontWeight={900} color="primary.main">{contract.contract_number||contract.external_contract_id}</Typography>
<Typography fontWeight={750} noWrap title={contract.supplier_name||undefined}>{contract.supplier_name||'Fornecedor nao informado'}</Typography>
</Box>
<Stack direction="row" alignItems="center" gap={.5}>{contract.status&&<Chip size="small" variant="outlined" label={contract.status}/>}<IconButton size="small" color="primary" onClick={onView} aria-label={`Visualizar contrato ${contract.contract_number||contract.external_contract_id}`}><VisibilityOutlined fontSize="small"/></IconButton></Stack>
</Stack>
<Typography variant="body2" color="text.secondary" mb={1.5} sx={{display:'-webkit-box',WebkitLineClamp:2,WebkitBoxOrient:'vertical',overflow:'hidden'}}>{contract.contract_object||'Objeto nao informado'}</Typography>
<Box sx={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:1,mb:1.5}}>
<Amount title="Empenhado" value={contract.committed} color="primary.main"/>
<Amount title="Liquidado" value={contract.liquidated} color="warning.dark"/>
<Amount title="Pago" value={contract.paid} color="success.dark"/>
</Box>
<Stack spacing={1} mb={1.5}>
<Bar title="% Liquidado" value={percent(contract.liquidated,base)} color="secondary"/>
<Bar title="% Pago" value={percent(contract.paid,base)} color="success"/>
<Bar title="% Comprometido (vl. global)" value={percent(contract.committed,contract.global_value)} color="primary"/>
</Stack>
<Stack direction="row" justifyContent="space-between" flexWrap="wrap" gap={1}>
<Typography variant="caption" color="text.secondary">{contract.commitments} empenhos</Typography>
<Typography variant="caption" color="text.secondary">Vl. Global: <strong>{money(contract.global_value)}</strong></Typography>
<Typography variant="caption" color="text.secondary">Vig. ate {date(contract.end_date)}</Typography>
</Stack>
</Box>;
}

function ContractField({label,value,helperText,multiline=false}:{label:string;value:string|number|null|undefined;helperText?:string;multiline?:boolean}){
  return <TextField label={label} value={value===null||value===undefined||value===''?'Não informado':value} helperText={helperText} multiline={multiline} minRows={multiline?3:undefined} fullWidth InputProps={{readOnly:true}} InputLabelProps={{shrink:true}}/>;
}

function ContractDetails({contract,onClose}:{contract:SubprojectContract|null;onClose:()=>void}){
  return <Dialog open={Boolean(contract)} onClose={onClose} fullWidth maxWidth="xl">
    {contract&&<>
      <DialogTitle sx={{pb:2}}><Stack direction="row" alignItems="flex-start" justifyContent="space-between" gap={2}><Stack direction="row" gap={1.5} alignItems="flex-start"><WorkOutline color="primary" sx={{mt:.4}}/><Box><Typography variant="h5" fontWeight={900}>Visualizar contrato {contract.contract_number||contract.external_contract_id}</Typography><Typography variant="body2" color="text.secondary" mt={1}>Campos técnicos de integração e auditoria são protegidos pelo sistema.</Typography></Box></Stack><IconButton onClick={onClose} aria-label="Fechar"><Close/></IconButton></Stack></DialogTitle>
      <Divider/>
      <DialogContent sx={{py:3}}>
        <Typography variant="h6" fontWeight={900} mb={2}>Identificação e situação</Typography>
        <Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:'1.1fr 1.1fr .7fr 1.1fr'},gap:2,alignItems:'start'}}>
          <ContractField label="Código do contrato" value={contract.external_contract_id} helperText="Chave protegida para preservar os vínculos."/>
          <ContractField label="Código completo do instrumento" value={contract.instrument_code} helperText="17 dígitos: UASG, tipo, número e ano."/>
          <ContractField label="UASG contratante" value={contract.contracting_uasg}/>
          <ContractField label="Abrangência" value={contract.coverage}/>
          <ContractField label="Tipo de contrato" value={contract.contract_type}/>
          <ContractField label="Status" value={contract.status}/>
          <ContractField label="Valor global" value={money(contract.global_value)}/>
          <ContractField label="Ação orçamentária" value={contract.budget_action}/>
          <Box sx={{gridColumn:{md:'1 / -1'}}}><ContractField label="Objeto" value={contract.contract_object} multiline/></Box>
          <Box sx={{gridColumn:{md:'span 2'}}}><ContractField label="Processo" value={contract.process_number}/></Box>
          <Box sx={{gridColumn:{md:'span 2'}}}><ContractField label="Fundamento legal" value={contract.legal_basis}/></Box>
        </Box>
      </DialogContent>
    </>}
  </Dialog>;
}

export const linkedContractsKey=(subprojectId:number)=>['subproject-contracts',subprojectId];
export const fetchLinkedContracts=(subprojectId:number)=>api.get<LinkedContracts>(`/subprojects/${subprojectId}/contracts`).then(r=>r.data);
export const saveLinkedContracts=(subprojectId:number,contracts:Contract[])=>api.put<LinkedContracts>(`/subprojects/${subprojectId}/contracts`,{external_contract_ids:contracts.map(item=>item.external_contract_id)});

export function ContractPicker({projectId,value,onChange}:{projectId:number;value:Contract[];onChange:(contracts:Contract[])=>void}){
  const [allProjects,setAllProjects]=useState(false);
  const options=useQuery({queryKey:['subproject-contract-options',projectId,allProjects],queryFn:()=>api.get<ContractOptions>(`/projects/${projectId}/subproject-contract-options`,{params:{all_projects:allProjects,limit:300}}).then(r=>r.data),enabled:Boolean(projectId)});
  // Mantem na lista os contratos ja selecionados mesmo quando o filtro por projeto os oculta.
  const choices=[...value.filter(item=>!options.data?.items.some(option=>option.external_contract_id===item.external_contract_id)),...(options.data?.items||[])];
  if(!projectId)return <Alert severity="info">Selecione o Projeto SAD superior para listar os contratos.</Alert>;
  return <Stack spacing={1.5}>
<FormControlLabel control={<Switch checked={allProjects} onChange={e=>setAllProjects(e.target.checked)}/>} label={options.data?.radar_project||allProjects?'Mostrar contratos de todos os projetos':'Projeto nao localizado no Radar; exibindo todos os contratos'} disabled={!options.data?.radar_project&&!allProjects}/>
<Autocomplete multiple options={choices} loading={options.isLoading} value={value} filterSelectedOptions isOptionEqualToValue={(a,b)=>a.external_contract_id===b.external_contract_id} getOptionLabel={label} onChange={(_,values)=>onChange(values)} filterOptions={(list,state)=>{const term=state.inputValue.trim().toLowerCase();return term?list.filter(item=>[item.external_contract_id,item.contract_number,item.supplier_name,item.contract_object].some(text=>text?.toLowerCase().includes(term))):list}} renderInput={params=><TextField {...params} label="Contratos do Radar Financeiro" placeholder="Pesquise por numero, fornecedor ou objeto"/>} renderOption={(props,option)=><li {...props} key={option.external_contract_id}>
<Box>
<Typography variant="body2" fontWeight={800}>{option.contract_number||option.external_contract_id} · {option.supplier_name||'Sem fornecedor'}</Typography>
<Typography variant="caption" color="text.secondary">{option.contract_object||'Objeto nao informado'} · {money(option.global_value)}</Typography>
</Box>
</li>}/>
{options.isError&&<Alert severity="error">Nao foi possivel consultar os contratos do Radar Financeiro.</Alert>}
<FormHelperText sx={{ml:1}}>{options.data?.filtered_by_project?`Exibindo os contratos do projeto ${options.data.radar_project} no Radar Financeiro. `:''}A consulta e somente leitura; os vinculos sao gravados apenas na base de projetos.</FormHelperText>
</Stack>;
}

export default function SubprojectContracts({subprojectId}:{subprojectId:number}){
  const [selected,setSelected]=useState<SubprojectContract|null>(null);
  const linked=useQuery({queryKey:linkedContractsKey(subprojectId),queryFn:()=>fetchLinkedContracts(subprojectId)});
  const contracts=linked.data?.contracts||[];
  return <Card>
<CardContent>
<Box mb={2}>
<Typography variant="h6">Contratos vinculados</Typography>
<Typography variant="caption" color="text.secondary">Dados oficiais consultados no Radar Financeiro-Orçamentário · posição {period(linked.data?.period||null)}</Typography>
</Box>
{linked.isLoading?<Skeleton variant="rounded" height={160}/>:linked.isError?<Alert severity="error">Nao foi possivel consultar os contratos do Radar Financeiro.</Alert>:contracts.length===0?<Stack direction="row" gap={1.5} alignItems="center" color="text.secondary">
<WorkOutline/>
<Typography>Nenhum contrato vinculado. Use Editar para vincular contratos a este subprojeto.</Typography>
</Stack>:<Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:'1fr 1fr'},gap:2}}>{contracts.map(contract=>contract.available_in_radar?<ContractCard key={contract.external_contract_id} contract={contract} onView={()=>setSelected(contract)}/>:<Alert key={contract.external_contract_id} severity="warning"><Typography fontWeight={800}>Contrato {contract.external_contract_id}</Typography>O vínculo existe, mas o contrato não está disponível no Radar Financeiro-Orçamentário. Nenhum dado local foi usado para montar o card.</Alert>)}</Box>}
<ContractDetails contract={selected} onClose={()=>setSelected(null)}/>
</CardContent>
</Card>;
}
