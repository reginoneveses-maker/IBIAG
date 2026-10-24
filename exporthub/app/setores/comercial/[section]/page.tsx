import Cockpit from '@/components/exporthub/Cockpit';
import {notFound} from 'next/navigation';
export default async function Page({params}:{params:Promise<{section:string}>}){const {section}=await params;if(!['crm','precificacao'].includes(section))notFound();return <Cockpit slug="comercial" commercialView={section as 'crm'|'precificacao'}/>}
