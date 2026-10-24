'use client';
import {useEffect,useState} from 'react';
export default function RuntimeStatus({signInPath}:{signInPath:string}){
const [ready,setReady]=useState(false),[needsSignIn,setNeedsSignIn]=useState(false);
useEffect(()=>{setReady(true);const controller=new AbortController(),requireSignIn=()=>setNeedsSignIn(true);window.addEventListener('exporthub:signin-required',requireSignIn);fetch('/api/me',{cache:'no-store',signal:controller.signal}).then(r=>{if(r.status===401)setNeedsSignIn(true)}).catch(()=>{});return()=>{controller.abort();window.removeEventListener('exporthub:signin-required',requireSignIn)}},[]);
return <div className="runtime-status" role="status">{needsSignIn?<><strong>Entre com sua conta para acessar e salvar os registros.</strong> <a href={signInPath} target="_top">Entrar novamente</a> · </>:ready?'Interface ativa · registros no sistema ':'Ativando interface… '}<a href="/">Início</a> · <a href="/produtos">Produtos</a> · <a href="/setores/comercial/crm">CRM</a> · <a href="/setores/comercial/precificacao">Calculadora</a> · <a href="/saude">Saúde do sistema</a></div>}
