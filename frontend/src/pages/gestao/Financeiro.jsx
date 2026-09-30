import { PageHeader, SubTabs } from "@/components/erp";
import { DocumentsPanel } from "@/components/DocumentsPanel";
import { CashFlow } from "@/components/CashFlow";
import Invoices from "@/pages/Invoices";
import Finance from "@/pages/Finance";

export default function Financeiro() {
  return (
    <div data-testid="financeiro-page">
      <PageHeader number="02 · Marketing, Financeiro e Contabilidade" title="Marketing, Financeiro & Contabilidade" subtitle="Notas fiscais, fluxo de caixa e materiais de marketing" />
      <SubTabs tabs={[
        { key: "nf_saida", label: "NF Saída", content: <Invoices kind="saida" embedded /> },
        { key: "nf_entrada", label: "NF Entrada", content: <Invoices kind="entrada" embedded /> },
        { key: "fluxo", label: "Fluxo de Caixa", content: <div><CashFlow /><Finance embedded /></div> },
        { key: "marketing", label: "Marketing", content: <DocumentsPanel category="marketing" title="Marketing" subtitle="Catálogos, fotos, apresentações e materiais institucionais" /> },
      ]} />
    </div>
  );
}
