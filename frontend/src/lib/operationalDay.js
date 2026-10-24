// Business dates follow the same timezone as the server, independent of the browser.
export function operationalDay(now=new Date()){
 return now.toLocaleDateString('en-CA',{timeZone:'America/Fortaleza'});
}
