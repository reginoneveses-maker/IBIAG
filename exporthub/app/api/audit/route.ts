import {workspace,apiError} from '@/db/workspace';
export async function GET(){try{const {db}=await workspace('admin');const rows=await db.prepare('SELECT id,at,actor,action,resource_type AS resourceType,resource_id AS resourceId FROM audit_events ORDER BY at DESC LIMIT 100').all();return Response.json(rows.results,{headers:{'Cache-Control':'private, no-store'}})}catch(e){return apiError(e)}}
