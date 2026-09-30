import { PageHeader, SubTabs } from "@/components/erp";
import { DocumentsPanel } from "@/components/DocumentsPanel";
import Suppliers from "@/pages/Suppliers";
import Contracts from "@/pages/Contracts";
import Compras from "@/pages/gestao/Compras";
import Certificacoes from "@/pages/gestao/Certificacoes";

export default function FornecedoresHub() {
  return (
    <div data-testid="fornecedores-page">
      <PageHeader number="03 · Contratos, Compras e Certificações" title="Contratos, Compras & Certificações" subtitle="Relacionamento com fornecedores e conformidade" />
      <SubTabs tabs={[
        { key: "contratos", label: "Contratos Fornecedores", content: <Contracts embedded /> },
        { key: "compras", label: "Compras", content: <Compras /> },
        { key: "certificacoes", label: "Certificações", content: <Certificacoes /> },
        { key: "ibiag", label: "Certificação Orgânica IBIAG", content: <DocumentsPanel category="ibiag_organic" title="Certificação Orgânica IBIAG" subtitle="Certificado orgânico da IBIAG e todos os documentos usados no processo de certificação (plano de manejo, auditorias, formulários, laudos)" /> },
        { key: "fornecedores", label: "Cadastro", content: <Suppliers embedded /> },
      ]} />
    </div>
  );
}
