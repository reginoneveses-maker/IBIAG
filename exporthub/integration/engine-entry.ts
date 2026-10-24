import {webcrypto} from 'node:crypto';
import {completionStateSchema,quoteDraftSchema,completedQuote} from '../services/quote-completion';
Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});
async function main(){let input='';for await(const chunk of process.stdin){input+=chunk;if(input.length>220000)process.exit(2)}
try{const request=JSON.parse(input);let result;if(request.kind==='draft')result=quoteDraftSchema.parse(request.data);else if(request.kind==='quote'){const state=completionStateSchema.parse(request.data);if(!state.confirmed)throw new Error('Confirme a revisão dos valores');result=completedQuote(state)}else throw new Error('Operação inválida');process.stdout.write(JSON.stringify({ok:true,data:result}))}catch{process.stdout.write(JSON.stringify({ok:false,error:'Revise os campos essenciais, as confirmações e a estrutura da cotação.'}));process.exitCode=1}

}
main().catch(()=>{process.stderr.write('Falha no motor de cotação');process.exitCode=2});
