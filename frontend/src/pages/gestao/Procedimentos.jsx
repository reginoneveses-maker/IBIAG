import { PageHeader, SubTabs } from "@/components/erp";
import { DocumentsPanel } from "@/components/DocumentsPanel";

export default function Procedimentos() {
  return (
    <div data-testid="procedimentos-page">
      <PageHeader number="01 · Procedimentos" title="Procedimentos" subtitle="Procedimentos da IBIAG e dos fornecedores presentes no acervo" />
      <SubTabs tabs={[
        { key: "pops", label: "POPs", content: <DocumentsPanel category="pop" title="POPs" subtitle="Procedimentos cadastrados. A vigência deve ser conferida no documento." /> },
        { key: "pops_assinados", label: "POPs Assinados", content: <DocumentsPanel category="pop_signed" title="POPs Assinados" subtitle="Documentos classificados como assinados após conferência" /> },
      ]} />
    </div>
  );
}
