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

export default function App(){return <Routes><Route element={<Layout/>}><Route index element={<Dashboard/>}/><Route path="projetos" element={<Projects/>}/><Route path="projetos/novo" element={<ProjectForm/>}/><Route path="projetos/:id" element={<ProjectDetail/>}/><Route path="projetos/:id/editar" element={<ProjectForm/>}/><Route path="subprojetos" element={<Subprojects/>}/><Route path="subprojetos/novo" element={<SubprojectForm/>}/><Route path="projetos/:projectId/subprojetos/novo" element={<SubprojectForm/>}/><Route path="subprojetos/:id" element={<SubprojectDetail/>}/><Route path="subprojetos/:id/cockpit" element={<SubprojectCockpit/>}/><Route path="subprojetos/:id/editar" element={<SubprojectForm/>}/><Route path="subprojetos/:subprojectId/cronograma" element={<ScheduleActivities mode="milestones"/>}/><Route path="subprojetos/:subprojectId/cronograma-projeto" element={<ScheduleActivities mode="project"/>}/><Route path="cronograma" element={<ComingSoon title="Cronograma e marcos" description="A estrutura para atividades, dependencias e graficos de Gantt sera incorporada na proxima etapa."/>}/><Route path="indicadores" element={<ComingSoon title="Indicadores" description="Acompanhamento de desempenho e metas previsto para a evolucao incremental."/>}/><Route path="relatorios" element={<ComingSoon title="Relatorios gerenciais" description="Relatorios e exportacoes serao habilitados apos a validacao do cadastro inicial."/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Route></Routes>}
