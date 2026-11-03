import {Navigate,Route,Routes} from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import ProjectForm from './pages/ProjectForm';
import ProjectDetail from './pages/ProjectDetail';
import Subprojects from './pages/Subprojects';
import SubprojectForm from './pages/SubprojectForm';
import SubprojectDetail,{SubprojectCockpit} from './pages/SubprojectDetail';
import ComingSoon from './pages/ComingSoon';
import ScheduleActivities from './pages/ScheduleActivities';
import Login from './pages/Login';
import Users from './pages/Users';
import {can,isAuthenticated,MANAGE_PROJECTS,MANAGE_SUBPROJECTS,MANAGE_USERS} from './auth';

function AuthGuard({children}:{children:React.ReactNode}){return isAuthenticated()?children:<Navigate to="/login" replace/>}
function PermissionGuard({permission,children}:{permission:string;children:React.ReactNode}){return can(permission)?children:<Navigate to="/" replace/>}

export default function App(){return <Routes><Route path="login" element={isAuthenticated()?<Navigate to="/" replace/>:<Login/>}/><Route element={<AuthGuard><Layout/></AuthGuard>}><Route index element={<Dashboard/>}/><Route path="projetos" element={<Projects/>}/><Route path="projetos/novo" element={<PermissionGuard permission={MANAGE_PROJECTS}><ProjectForm/></PermissionGuard>}/><Route path="projetos/:id" element={<ProjectDetail/>}/><Route path="projetos/:id/editar" element={<PermissionGuard permission={MANAGE_PROJECTS}><ProjectForm/></PermissionGuard>}/><Route path="subprojetos" element={<Subprojects/>}/><Route path="subprojetos/novo" element={<PermissionGuard permission={MANAGE_SUBPROJECTS}><SubprojectForm/></PermissionGuard>}/><Route path="projetos/:projectId/subprojetos/novo" element={<PermissionGuard permission={MANAGE_SUBPROJECTS}><SubprojectForm/></PermissionGuard>}/><Route path="subprojetos/:id" element={<SubprojectDetail/>}/><Route path="subprojetos/:id/cockpit" element={<SubprojectCockpit/>}/><Route path="subprojetos/:id/editar" element={<PermissionGuard permission={MANAGE_SUBPROJECTS}><SubprojectForm/></PermissionGuard>}/><Route path="subprojetos/:subprojectId/cronograma" element={<ScheduleActivities mode="milestones"/>}/><Route path="subprojetos/:subprojectId/cronograma-projeto" element={<ScheduleActivities mode="project"/>}/><Route path="usuarios" element={<PermissionGuard permission={MANAGE_USERS}><Users/></PermissionGuard>}/><Route path="cronograma" element={<ComingSoon title="Cronograma e marcos" description="A estrutura para atividades, dependencias e graficos de Gantt sera incorporada na proxima etapa."/>}/><Route path="indicadores" element={<ComingSoon title="Indicadores" description="Acompanhamento de desempenho e metas previsto para a evolucao incremental."/>}/><Route path="relatorios" element={<ComingSoon title="Relatorios gerenciais" description="Relatorios e exportacoes serao habilitados apos a validacao do cadastro inicial."/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Route></Routes>}
