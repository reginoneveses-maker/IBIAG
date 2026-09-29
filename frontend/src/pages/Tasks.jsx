import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useLang } from "@/i18n";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent } from "@/components/ui/card";
import { Trash2, CheckSquare, Plus, Calendar } from "lucide-react";
import { toast } from "sonner";

const Tasks = () => {
  const { t } = useLang();
  const [tasks, setTasks] = useState([]);
  const [form, setForm] = useState({ title: "", description: "", due_date: "" });

  const load = () => api.get("/tasks").then(r => setTasks(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!form.title.trim()) return;
    await api.post("/tasks", form);
    setForm({ title: "", description: "", due_date: "" });
    toast.success(t("task_created"));
    load();
  };

  const toggle = async (id) => { await api.patch(`/tasks/${id}/toggle`); load(); };
  const del = async (id) => { await api.delete(`/tasks/${id}`); load(); };

  const pending = tasks.filter(x => !x.completed);
  const completed = tasks.filter(x => x.completed);

  return (
    <div className="space-y-6" data-testid="tasks-page">
      <div>
        <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-[#0F382C]/60 mb-2 flex items-center gap-1"><CheckSquare className="w-3 h-3" /> 06 · Tasks</div>
        <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-[#0F382C]">{t("tasks_title")}</h1>
        <p className="text-base text-[#0F382C]/70 mt-1">{t("tasks_subtitle")}</p>
      </div>

      <Card className="bg-white border-[#0F382C]/10">
        <CardContent className="p-4 space-y-3">
          <Input placeholder={t("task_title")} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} data-testid="task-title-input" />
          <Textarea placeholder={t("notes")} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} />
          <div className="flex flex-col sm:flex-row gap-2">
            <Input type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} className="sm:max-w-xs" data-testid="task-date-input" />
            <Button onClick={add} className="bg-[#0F382C] hover:bg-[#0A2920] text-white" data-testid="add-task-button"><Plus className="w-4 h-4 mr-1" />{t("new_task")}</Button>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <div className="text-xs font-mono-alt uppercase tracking-widest text-[#0F382C]/60">{t("pending_tasks")} ({pending.length})</div>
        {pending.length === 0 && <div className="text-sm text-[#0F382C]/50 italic">{t("no_tasks")}</div>}
        {pending.map(x => (
          <Card key={x.id} data-testid={`task-${x.id}`} className="bg-white border-[#0F382C]/10">
            <CardContent className="p-4 flex items-start gap-3">
              <Checkbox checked={x.completed} onCheckedChange={() => toggle(x.id)} data-testid={`toggle-${x.id}`} className="mt-1" />
              <div className="flex-1">
                <div className="font-semibold text-[#0F382C]">{x.title}</div>
                {x.description && <div className="text-sm text-[#0F382C]/70 mt-1 whitespace-pre-wrap">{x.description}</div>}
                {x.due_date && <div className="text-xs text-amber-700 mt-1 flex items-center gap-1"><Calendar className="w-3 h-3" />{x.due_date}</div>}
              </div>
              <button onClick={() => del(x.id)} data-testid={`del-task-${x.id}`} className="text-rose-600 hover:bg-rose-50 p-1 rounded"><Trash2 className="w-4 h-4" /></button>
            </CardContent>
          </Card>
        ))}

        {completed.length > 0 && (
          <>
            <div className="text-xs font-mono-alt uppercase tracking-widest text-[#0F382C]/60 pt-4">{t("completed_tasks")} ({completed.length})</div>
            {completed.map(x => (
              <Card key={x.id} className="bg-[#EFECE6]/50 border-[#0F382C]/10 opacity-70">
                <CardContent className="p-4 flex items-start gap-3">
                  <Checkbox checked={x.completed} onCheckedChange={() => toggle(x.id)} className="mt-1" />
                  <div className="flex-1">
                    <div className="font-semibold text-[#0F382C] line-through">{x.title}</div>
                    {x.due_date && <div className="text-xs text-[#0F382C]/50">{x.due_date}</div>}
                  </div>
                  <button onClick={() => del(x.id)} className="text-rose-600 hover:bg-rose-50 p-1 rounded"><Trash2 className="w-4 h-4" /></button>
                </CardContent>
              </Card>
            ))}
          </>
        )}
      </div>
    </div>
  );
};

export default Tasks;
