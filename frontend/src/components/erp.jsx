// Generic CRUD list page factory helpers
import { useEffect, useState, useRef } from "react";
import { api } from "@/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Trash2, Plus, Upload, Download, FileText } from "lucide-react";
import { toast } from "sonner";
import { fmtBRL } from "@/lib/api";

export const PageHeader = ({ number, title, subtitle, action }) => (
  <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
    <div>
      <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-[#0F382C]/60 mb-2">{number}</div>
      <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-[#0F382C]">{title}</h1>
      {subtitle && <p className="text-base text-[#0F382C]/70 mt-1">{subtitle}</p>}
    </div>
    {action}
  </div>
);

export const useUpload = () => {
  const inputRef = useRef();
  const [uploading, setUploading] = useState(false);
  const doUpload = (onDone) => {
    const el = inputRef.current;
    if (!el) return;
    el.onchange = async () => {
      const f = el.files?.[0]; if (!f) return;
      setUploading(true);
      try {
        const fd = new FormData(); fd.append("file", f);
        const r = await api.post("/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
        onDone(r.data);
      } catch (e) { toast.error("Upload falhou"); }
      finally { setUploading(false); el.value = ""; }
    };
    el.click();
  };
  const el = <input ref={inputRef} type="file" className="hidden" />;
  return { el, doUpload, uploading };
};

export { Button, Input, Textarea, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Trash2, Plus, Upload, Download, FileText, toast, fmtBRL };
