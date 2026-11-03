import {ConstructionOutlined} from '@mui/icons-material';
import {Box,Card,CardContent,Typography} from '@mui/material';

export default function ComingSoon({title,description}:{title:string;description:string}){return <Box><Typography variant="h4" mb={.75}>{title}</Typography><Typography color="text.secondary" mb={4}>Gestao de Projetos SAD</Typography><Card><CardContent sx={{py:8,textAlign:'center'}}><ConstructionOutlined sx={{fontSize:58,color:'secondary.main',mb:2}}/><Typography variant="h6">Modulo planejado</Typography><Typography color="text.secondary" maxWidth={560} mx="auto" mt={1}>{description}</Typography></CardContent></Card></Box>}

