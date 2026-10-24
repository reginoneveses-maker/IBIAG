export const MAX_PDF_BYTES=20*1024*1024,MAX_PDF_BATCH=20,MAX_BATCH_BYTES=100*1024*1024;
export function pdfSelectionError(files:readonly {name:string;size:number}[]){if(!files.length)return 'Selecione pelo menos um PDF.';if(files.length>MAX_PDF_BATCH)return 'Selecione até 20 PDFs por vez.';if(files.reduce((sum,f)=>sum+f.size,0)>MAX_BATCH_BYTES)return 'O conjunto selecionado deve ter até 100 MB.';return ''}
export function pdfFileError(file:{name:string;size:number},signature:string){if(!file.name.toLowerCase().endsWith('.pdf')||!file.size||file.size>MAX_PDF_BYTES)return 'Envie um PDF de até 20 MB.';if(signature!=='%PDF-')return 'O arquivo não tem uma assinatura PDF válida.';return ''}

export class PdfUploadError extends Error { constructor(message:string,readonly uncertain:boolean){super(message);this.name='PdfUploadError'} }
export async function uploadPdf(api:string,file:File,metadata:Record<string,string>,readResponse:<T>(response:Response)=>Promise<T>,request:typeof fetch=fetch){
 const validation=pdfFileError(file,await file.slice(0,5).text());if(validation)throw new PdfUploadError(validation,false);
 const form=new FormData();form.set('file',file);for(const [key,value] of Object.entries(metadata))form.set(key,value);
 let response:Response;try{response=await request(api,{method:'POST',body:form,signal:AbortSignal.timeout(300000)})}catch{throw new PdfUploadError('Não foi possível confirmar o envio. Confira os anexos antes de reenviar.',true)}
 if(!response.ok){let message='O servidor rejeitou o envio.';try{await readResponse(response)}catch(e){message=(e as Error).message}throw new PdfUploadError(message,response.status===408||response.status>=500)}
 try{const result=await readResponse<{id:string}>(response);if(!result||typeof result.id!=='string'||!result.id)throw new Error('Confirmação incompleta');return result.id}catch{throw new PdfUploadError('Confirmação incompleta. Confira os anexos antes de reenviar.',true)}
}
