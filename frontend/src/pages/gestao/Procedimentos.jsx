import { PageHeader, SubTabs } from "@/components/erp";
import { DocumentsPanel } from "@/components/DocumentsPanel";

export default function Procedimentos() {
  return (
    <div data-testid="procedimentos-page">
      <PageHeader number="01 · Procedimentos" title="Procedimentos" subtitle="Procedimentos Operacionais Padrão da IBIAG" />
      <SubTabs tabs={[
        { key: "pops", label: "POPs", content: <DocumentsPanel category="pop" title="POPs" subtitle="Versões editáveis / vigentes dos procedimentos" /> },
        { key: "pops_assinados", label: "POPs Assinados", content: <DocumentsPanel category="pop_signed" title="POPs Assinados" subtitle="Cópias assinadas e datadas (PDF)" /> },
      ]} />
    </div>
  );
}
