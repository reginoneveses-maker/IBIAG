import { useEffect, useState } from "react";
import { FolderArchive, FileText, Search, Upload, ShieldCheck, Package, Truck, Wallet, Users, Building2 } from "lucide-react";

const categories = [
  ["Financeiro & Fiscal", Wallet, "NF-e, boletos, comprovantes, contas e documentos fiscais"],
  ["Produtos", Package, "Fichas técnicas, laudos, certificados e especificações"],
  ["Fornecedores", Truck, "Contratos, cadastros, certificados e documentos de fornecedores"],
  ["Clientes & Comercial", Users, "Propostas, contratos, pedidos e documentos de clientes"],
  ["Societário", Building2, "Documentos da empresa, registros e documentos administrativos"],
  ["Qualidade & Compliance", ShieldCheck, "Certificações, auditorias, licenças e controles"],
];

export default function Documentos() {
  return <div className="space-y-6">
    <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
      <div><p className="text-xs font-semibold uppercase tracking-[.18em] text-[#104496]/45">Gestão documental</p><h1 className="text-3xl font-bold text-[#104496] mt-1">Central de Documentos</h1><p className="text-sm text-slate-500 mt-2">Arquivos organizados por área e vinculados aos registros da empresa.</p></div>
      <button className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#104496] text-white text-sm font-semibold"><Upload className="w-4 h-4"/> Novo documento</button>
    </div>
    <div className="relative"><Search className="absolute left-3 top-3 w-4 h-4 text-slate-400"/><input className="w-full bg-white border rounded-xl pl-10 pr-4 py-2.5 text-sm" placeholder="Buscar por nome, categoria, empresa, produto ou fornecedor..." /></div>
    <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
      {categories.map(([name,Icon,desc]) => <div key={name} className="bg-white border border-slate-200 rounded-2xl p-5 hover:shadow-sm transition-shadow">
        <div className="w-10 h-10 rounded-xl bg-[#104496]/8 flex items-center justify-center mb-4"><Icon className="w-5 h-5 text-[#104496]"/></div>
        <h2 className="font-bold text-[#104496]">{name}</h2><p className="text-sm text-slate-500 mt-1 leading-relaxed">{desc}</p>
        <div className="mt-4 pt-4 border-t text-xs text-slate-400 flex items-center gap-2"><FolderArchive className="w-3.5 h-3.5"/> Pasta documental</div>
      </div>)}
    </div>
    <div className="bg-white border border-slate-200 rounded-2xl p-5">
      <div className="flex items-center gap-2"><FileText className="w-5 h-5 text-[#104496]"/><h2 className="font-bold text-[#104496]">Documentos recentes</h2></div>
      <p className="text-sm text-slate-500 mt-3">Os arquivos enviados aparecerão aqui com categoria, vínculo, responsável, data e histórico.</p>
    </div>
  </div>;
}