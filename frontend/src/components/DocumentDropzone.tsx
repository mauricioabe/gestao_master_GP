import {useRef,useState} from 'react';
import {AttachFile,CloudUploadOutlined,DeleteOutline,OpenInNew} from '@mui/icons-material';
import {Alert,Box,Button,CircularProgress,IconButton,Stack,TextField,Typography} from '@mui/material';
import {api} from '../api';

type DocumentValue={name:string;url:string};
type UploadResult={name:string;filename:string;url:string;size:number};

const accept='.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.png,.jpg,.jpeg,.webp';
const fileLabel=(url:string)=>{
  if(!url.startsWith('/uploads/documents/'))return 'Link externo';
  const stored=decodeURIComponent(url.split('/').pop()||'');
  return stored.replace(/^[a-f0-9]{32}-/i,'');
};

export default function DocumentDropzone({documents,onChange}:{documents:DocumentValue[];onChange:(value:DocumentValue[])=>void}){
  const input=useRef<HTMLInputElement>(null);
  const [dragging,setDragging]=useState(false);
  const [uploading,setUploading]=useState(false);
  const [error,setError]=useState('');

  const upload=async(files:FileList|File[])=>{
    const selected=Array.from(files);
    if(!selected.length)return;
    setError('');setUploading(true);
    try{
      const uploaded:DocumentValue[]=[];
      for(const file of selected){
        const data=new FormData();data.append('file',file);
        const response=await api.post<UploadResult>('/uploads/documents',data);
        uploaded.push({name:response.data.name,url:response.data.url});
      }
      onChange([...documents,...uploaded]);
    }catch(err:any){setError(err.response?.data?.detail||'Nao foi possivel enviar o documento.')}
    finally{setUploading(false);if(input.current)input.current.value=''}
  };
  return <Stack spacing={1.5}>
    {error&&<Alert severity="error" onClose={()=>setError('')}>{error}</Alert>}
    <Box
      role="button" tabIndex={0}
      onKeyDown={event=>{if(event.key==='Enter'||event.key===' ')input.current?.click()}}
      onClick={()=>!uploading&&input.current?.click()}
      onDragEnter={event=>{event.preventDefault();setDragging(true)}}
      onDragOver={event=>event.preventDefault()}
      onDragLeave={event=>{event.preventDefault();setDragging(false)}}
      onDrop={event=>{event.preventDefault();setDragging(false);void upload(event.dataTransfer.files)}}
      sx={{border:'2px dashed',borderColor:dragging?'primary.main':'#b8c7d9',bgcolor:dragging?'#edf5ff':'#f8fafc',borderRadius:2.5,p:{xs:2.5,md:3.5},textAlign:'center',cursor:uploading?'wait':'pointer',transition:'all .18s ease','&:hover':{borderColor:'primary.main',bgcolor:'#f2f7fd'}}}
    >
      <input ref={input} hidden type="file" multiple accept={accept} onChange={event=>event.target.files&&void upload(event.target.files)}/>
      {uploading?<CircularProgress size={40}/>:<CloudUploadOutlined sx={{fontSize:48,color:'primary.main'}}/>}
      <Typography fontWeight={900} mt={1}>{uploading?'Enviando documentos...':'Arraste e solte os documentos aqui'}</Typography>
      <Typography variant="body2" color="text.secondary" mt={.5}>ou clique para selecionar arquivos</Typography>
      <Typography variant="caption" color="text.secondary" display="block" mt={1}>PDF, Office, texto ou imagem · ate 20 MB por arquivo</Typography>
    </Box>
    {documents.map((document,index)=><Box key={`${document.url}-${index}`} sx={{display:'grid',gridTemplateColumns:{xs:'1fr auto',md:'1fr 1fr auto'},gap:1.2,alignItems:'center',p:1.3,border:'1px solid #dce5ef',borderRadius:2,bgcolor:'#fff'}}>
      <TextField label="Nome do documento" value={document.name} onChange={event=>{const next=[...documents];next[index]={...document,name:event.target.value};onChange(next)}}/>
      <Stack direction="row" alignItems="center" gap={1} sx={{minWidth:0,display:{xs:'none',md:'flex'}}}><AttachFile fontSize="small" color="action"/><Typography variant="body2" noWrap title={fileLabel(document.url)}>{fileLabel(document.url)}</Typography>{document.url&&<IconButton size="small" component="a" href={document.url} target="_blank" rel="noreferrer" aria-label="Abrir documento"><OpenInNew fontSize="small"/></IconButton>}</Stack>
      <IconButton color="error" aria-label="Remover documento" onClick={()=>onChange(documents.filter((_,itemIndex)=>itemIndex!==index))}><DeleteOutline/></IconButton>
    </Box>)}
    {!documents.length&&<Typography variant="body2" color="text.secondary" textAlign="center">Nenhum documento enviado.</Typography>}
  </Stack>;
}
