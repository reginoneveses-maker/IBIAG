import {workspace,apiError} from '@/db/workspace';
import {loadFileIndex} from '@/db/file-index';
export async function GET(){try{const {db}=await workspace();const index=await loadFileIndex(db);return Response.json(index.files.map(({key,zipPath,...file})=>file),{headers:{'Cache-Control':'private, no-store'}})}catch(e){return apiError(e)}}
