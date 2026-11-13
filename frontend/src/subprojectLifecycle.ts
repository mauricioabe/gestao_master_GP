export const lifecycleStages={
  INICIACAO:'Iniciação',
  CONCEPCAO:'Concepção',
  CONTRATACAO:'Contratação',
  CONCEPCAO_CONTRATACAO:'Concp/Contç',
  EM_PRODUCAO:'Em produção',
  IMPLANTACAO:'Implantação',
  ENTREGA:'Entrega',
  ENCERRADO:'Encerrado',
} as const;

export type LifecycleStage=keyof typeof lifecycleStages;
