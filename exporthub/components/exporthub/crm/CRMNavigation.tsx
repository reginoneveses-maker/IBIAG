import {Handshake,Building2,Users,CalendarCheck,BarChart3,Settings2} from 'lucide-react';
export const crmSections=['negociacoes','empresas','contatos','tarefas','relatorios','configuracoes'] as const;
export default function CRMNavigation({current,counts}:{current:string;counts:{negociacoes:number;empresas:number;contatos:number;tarefas:number}}){
const items=[['negociacoes','Negociações',Handshake],['empresas','Empresas',Building2],['contatos','Contatos',Users],['tarefas','Tarefas',CalendarCheck],['relatorios','Relatórios',BarChart3],['configuracoes','Configurações',Settings2]] as const;
return <nav aria-label="Seções do CRM" className="crm-tab-list crm-main-tab-list">{items.map(([id,label,Icon])=><a key={id} id={'crm-nav-'+id} href={'/setores/comercial/crm?aba='+id} aria-current={current===id?'page':undefined} data-slot="tabs-trigger" data-state={current===id?'active':'inactive'}><Icon size={17}/>{label}{id in counts&&<span className={id==='tarefas'&&counts.tarefas?'crm-attention-count':''}>{counts[id as keyof typeof counts]}</span>}</a>)}</nav>
}
