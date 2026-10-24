import Cockpit from '@/components/exporthub/Cockpit';
import {sectors} from '@/data/demo';
import {notFound} from 'next/navigation';
export default async function Page({params}:{params:Promise<{slug:string}>}){const {slug}=await params;if(!sectors.some(s=>s.id===slug))notFound();return <Cockpit key={slug} slug={slug}/>}
