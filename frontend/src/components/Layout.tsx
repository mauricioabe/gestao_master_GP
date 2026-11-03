import {useState} from 'react';
import {AccountTreeOutlined,AssessmentOutlined,CalendarMonthOutlined,ChevronLeft,ChevronRight,DashboardOutlined,DescriptionOutlined,FolderSpecialOutlined,Menu as MenuIcon,NotificationsNoneOutlined,SettingsOutlined,TimelineOutlined} from '@mui/icons-material';
import {AppBar,Avatar,Badge,Box,Drawer,IconButton,List,ListItemButton,ListItemIcon,ListItemText,Stack,Toolbar,Tooltip,Typography,useMediaQuery,useTheme} from '@mui/material';
import {NavLink,Outlet} from 'react-router-dom';

const fullWidth=264;
const compactWidth=78;
const entries=[
  {to:'/',label:'Visao geral',icon:<DashboardOutlined/>,end:true},
  {to:'/projetos',label:'Projetos',icon:<FolderSpecialOutlined/>},
  {to:'/subprojetos',label:'Subprojetos',icon:<AccountTreeOutlined/>},
  {to:'/cronograma',label:'Cronogramas',icon:<CalendarMonthOutlined/>},
  {to:'/indicadores',label:'Indicadores',icon:<TimelineOutlined/>},
  {to:'/relatorios',label:'Relatorios',icon:<DescriptionOutlined/>},
];

export default function Layout(){
  const theme=useTheme();
  const mobile=useMediaQuery(theme.breakpoints.down('md'));
  const [open,setOpen]=useState(!mobile);
  const width=open?fullWidth:compactWidth;
  const nav=<><Box sx={{height:78,display:'flex',alignItems:'center',px:open?2.5:1.25,gap:1.4,borderBottom:'1px solid rgba(255,255,255,.1)'}}><Box sx={{width:42,height:42,borderRadius:2,display:'grid',placeItems:'center',background:'linear-gradient(145deg,#e4ad37,#ba7610)',fontWeight:900,color:'#071d3d',fontSize:18,flexShrink:0}}>SAD</Box>{open&&<Box><Typography fontWeight={900} letterSpacing={.4} lineHeight={1.05}>GESTAO DE</Typography><Typography fontWeight={900} color="#efbd55" lineHeight={1.1}>PROJETOS</Typography></Box>}</Box><List sx={{px:1.25,pt:2}}>{entries.map(item=><Tooltip key={item.to} title={open?'':item.label} placement="right"><ListItemButton component={NavLink} to={item.to} end={item.end} onClick={()=>mobile&&setOpen(false)} sx={{minHeight:48,borderRadius:2,mb:.7,px:1.6,color:'#bfd0e4','&.active':{color:'#fff',bgcolor:'rgba(45,111,172,.55)',boxShadow:'inset 3px 0 #e0a52d'},'&:hover':{bgcolor:'rgba(255,255,255,.08)'}}}><ListItemIcon sx={{minWidth:open?42:0,color:'inherit'}}>{item.icon}</ListItemIcon>{open&&<ListItemText primary={item.label} primaryTypographyProps={{fontWeight:700,fontSize:14}}/>}</ListItemButton></Tooltip>)}</List><Box sx={{flex:1}}/><Tooltip title={open?'Configuracoes':'Configuracoes'} placement="right"><ListItemButton sx={{mx:1.25,mb:2,borderRadius:2,color:'#8ea5bf'}}><ListItemIcon sx={{minWidth:open?42:0,color:'inherit'}}><SettingsOutlined/></ListItemIcon>{open&&<ListItemText primary="Configuracoes"/>}</ListItemButton></Tooltip></>;
  return <Box sx={{display:'flex',minHeight:'100vh'}}>
    <Drawer variant={mobile?'temporary':'permanent'} open={open} onClose={()=>setOpen(false)} sx={{width:mobile?0:width,flexShrink:0,'& .MuiDrawer-paper':{width:mobile?fullWidth:width,boxSizing:'border-box',border:0,color:'#fff',background:'linear-gradient(180deg,#071d3d 0%,#092c55 68%,#0b396b 100%)',transition:'width .2s ease',overflowX:'hidden'}}}>{nav}</Drawer>
    <Box sx={{flexGrow:1,minWidth:0,ml:0}}><AppBar position="sticky" color="inherit" elevation={0} sx={{borderBottom:'1px solid #e1e8f0',bgcolor:'rgba(255,255,255,.94)',backdropFilter:'blur(12px)'}}><Toolbar sx={{minHeight:'64px!important',px:{xs:2,md:3}}}><IconButton onClick={()=>setOpen(v=>!v)} edge="start" aria-label="Alternar menu">{mobile?<MenuIcon/>:open?<ChevronLeft/>:<ChevronRight/>}</IconButton><Box sx={{ml:2,flex:1}}><Typography variant="body2" color="text.secondary">Comando do Exercito</Typography><Typography fontWeight={800} lineHeight={1.1}>Programa SISFRON</Typography></Box><Stack direction="row" alignItems="center" spacing={1.5}><IconButton aria-label="Notificacoes"><Badge variant="dot" color="secondary"><NotificationsNoneOutlined/></Badge></IconButton><Box sx={{display:{xs:'none',sm:'block'},textAlign:'right'}}><Typography variant="body2" fontWeight={800}>Gestor SAD</Typography><Typography variant="caption" color="text.secondary">Administrador</Typography></Box><Avatar sx={{bgcolor:'primary.main',width:38,height:38,fontSize:14,fontWeight:800}}>GS</Avatar></Stack></Toolbar></AppBar><Box component="main" sx={{p:{xs:2,sm:3,lg:4},maxWidth:1600,mx:'auto'}}><Outlet/></Box></Box>
  </Box>;
}

