export class RequestDataError extends Error {constructor(public status:number,message:string){super(message)}}
// Enforce bytes while consuming the body, including chunked requests without Content-Length.
export async function readRequestJSON(request:Request,maxBytes:number):Promise<any>{
 const length=request.headers.get('content-length');
 if(length&&(!/^\d+$/.test(length)||Number(length)>maxBytes))throw new RequestDataError(413,'Dados maiores que o limite permitido.');
 const reader=request.body?.getReader();if(!reader)throw new RequestDataError(400,'Dados inválidos.');
 const chunks:Uint8Array[]=[];let size=0;
 try {while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>maxBytes){await reader.cancel();throw new RequestDataError(413,'Dados maiores que o limite permitido.')}chunks.push(value)}}finally{reader.releaseLock()}
 const bytes=new Uint8Array(size);let at=0;for(const chunk of chunks){bytes.set(chunk,at);at+=chunk.byteLength}
 try{const value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));if(!value||typeof value!=='object'||Array.isArray(value))throw new Error();return value;}catch{throw new RequestDataError(400,'Dados inválidos.')}
}
