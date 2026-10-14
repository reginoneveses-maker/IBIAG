'use client';
import {useEffect,useState} from 'react';
import {readApiResponse} from '@/services/workspace';
import PdfUploader from '../PdfUploader';
import {FileText,Download} from 'lucide-react';
import {dateLabel} from '@/services/crm';
type FileRecord={id:string;filename:string;size:number;createdAt:string};
export default function DealFiles({opportunityId,sectorRecord=false}:{opportunityId:string;sectorRecord?:boolean}){const api=sectorRecord?'/api/sector-files':'/api/crm/files',fileKey=sectorRecord?'recordId':'opportunityId';const [files,setFiles]=useState<FileRecord[]>([]),[ready,setReady]=useState(false),[error,setError]=useState('');async function load(){setError('');try{const r=await fetch(api+'?'+(sectorRecord?'record':'opportunity')+'='+encodeURIComponent(opportunityId),{cache:'no-store'}),data=await readApiResponse<FileRecord[]>(r);setFiles(data);setReady(true)}catch(e){setError((e as Error).message)}}useEffect(()=>{load()},[opportunityId,sectorRecord]);return <section><h3>{sectorRecord?'Documentos deste processo':'Anexos da negociação'}</h3><p className="form-note">Propostas, contratos, pedidos ou outros documentos em PDF. Specs técnicos continuam organizados por produto, separados em IBIAG e original.</p><PdfUploader api={api} metadata={{[fileKey]:opportunityId}} scopeKey={api+opportunityId} onUploaded={load}/>
{error?<div role="alert"><p>{error}</p><button className="btn" onClick={load}>Tentar novamente</button></div>:ready?files.length?files.map(f=><a className="crm-file-row" key={f.id} href={api+'/'+f.id} download><FileText size={22}/><span><b>{f.filename}</b><small>{dateLabel(f.createdAt)} · {(f.size/1024).toFixed(0)} KB</small></span><Download size={18}/></a>):<p>Nenhum documento anexado.</p>:<p>Carregando anexos…</p>}</section>}
