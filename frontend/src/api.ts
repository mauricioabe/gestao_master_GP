import axios from 'axios';

export const api=axios.create({baseURL:'/api',timeout:15000});
api.interceptors.request.use(config=>{const token=localStorage.getItem('token');if(token)config.headers.Authorization=`Bearer ${token}`;return config});
api.interceptors.response.use(response=>response,error=>{if(error.response?.status===401&&!location.pathname.startsWith('/login')){localStorage.removeItem('token');localStorage.removeItem('role');localStorage.removeItem('userName');localStorage.removeItem('permissions');location.href='/login'}return Promise.reject(error)});

export type Contract={
  external_contract_id:string;contract_number:string|null;contract_object:string|null;
  supplier_name:string|null;global_value:number|null;status?:string|null;
  start_date?:string|null;end_date?:string|null;
  instrument_code?:string|null;contracting_uasg?:string|null;coverage?:string|null;
  contract_type?:string|null;budget_action?:string|null;process_number?:string|null;legal_basis?:string|null;
};
export type ContractOptions={radar_project:string|null;filtered_by_project:boolean;items:Contract[]};
export type SubprojectContract=Contract&{
  id:number;linked_at:string;available_in_radar:boolean;
  source_system:'RADAR_FINANCEIRO_ORCAMENTARIO';
  commitments:number;committed:number;liquidated:number;paid:number;
};
export type SubprojectContracts={period:string|null;contracts:SubprojectContract[]};
export type ProjectOm={id?:number;name:string;added_at?:string};
export type ProjectDocument={id?:number;name:string;url:string;added_at?:string};

export type Project={
  id:number;code:string;name:string;description:string|null;manager:string;
  status:string;phase:string;priority:string;start_date:string|null;end_date:string|null;
  progress:number;budget:number|null;cma:string|null;geographic_scope:string|null;
  objectives:string|null;active:boolean;duration_years:number|null;
  contracts:(Contract&{id:number;linked_at:string})[];
  oms:ProjectOm[];documents:ProjectDocument[];
  created_at:string;updated_at:string;
};

export type ProjectInput=Omit<Project,'id'|'active'|'duration_years'|'created_at'|'updated_at'|'contracts'|'oms'|'documents'>&{
  contracts:Contract[];oms:{name:string}[];documents:{name:string;url:string}[];
};

export type ProjectOptions={cmas:{code:string;name:string}[];oms:string[]};
export type DashboardData={
  total_projects:number;active_projects:number;delayed_projects:number;
  linked_contracts:number;average_progress:number;
  by_status:{status:string;total:number}[];
};
export type Subproject={
  id:number;project_id:number;parent_id:number|null;wbs_code:string;sort_order:number;
  code:string;name:string;short_name:string|null;description:string|null;objective:string;
  main_product:string;expected_deliverables:string|null;scope:string|null;out_of_scope:string|null;
  expected_benefits:string|null;manager:string;responsible_unit:string;status:string;priority:string;
  planned_start_date:string;planned_end_date:string;real_start_date:string|null;real_end_date:string|null;
  execution_percentage:number;budget:number|null;key_milestones:string|null;schedule_status:string|null;
  justification:string|null;active:boolean;project_name:string;project_code:string;parent_name:string|null;
  children_count:number;created_at:string;updated_at:string;
};

export type SubprojectInput=Omit<Subproject,'id'|'wbs_code'|'sort_order'|'active'|'project_name'|'project_code'|'parent_name'|'children_count'|'created_at'|'updated_at'>;
export type Activity={
  id:number;subproject_id:number;schedule_type:'MILESTONE'|'PROJECT';wbs_code:string;sort_order:number;name:string;duration_days:number;
  start_date:string;finish_date:string;resource_names:string|null;execution_percentage:number;planned_value:number|string;actual_value:number|string;delivery_status:'ENCERRADA'|'EM_EXECUCAO'|'CANCELADA'|'EM_PLANEJAMENTO';predecessor_id:number|null;
  predecessor_wbs:string|null;parent_id:number|null;depth:number;is_summary:boolean;source_system:string|null;source_key:string|null;active:boolean;created_at:string;updated_at:string;
};

export type ActivityInput=Pick<Activity,'name'|'start_date'|'finish_date'|'resource_names'|'execution_percentage'|'planned_value'|'actual_value'|'delivery_status'|'predecessor_id'>;

export type CffStage={
  id:number;cff_id:number;contract_id:string;contract_number:string|null;cff_version:number;
  stage_number:string|null;name:string;stage_value:number|null;readiness_letter_date:string|null;import_start_date:string;import_finish_date:string;
  bank_order:string|null;paid_value:number|string;payment_status:string;payment_message:string;payment_verified_at:string|null;
  execution_percentage:number;importable:boolean;imported:boolean;imported_activity_id:number|null;
};
export type CffPreview={linked_contracts:number;cff_files:number;stages:CffStage[]};
export type CffImportResult={imported:number;updated:number;skipped:number;activities:Activity[]};
