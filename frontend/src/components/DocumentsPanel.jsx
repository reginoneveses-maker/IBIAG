import Documentos from "@/pages/gestao/Documentos";

export const DocumentsPanel = ({ category, title, subtitle, testId }) => (
  <div data-testid={testId || `docs-${category}`}>
    <Documentos key={category} defaultSection={category} title={title} subtitle={subtitle} embedded />
  </div>
);
