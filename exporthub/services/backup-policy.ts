// Explicit server opt-in only. Browser input and account role cannot enable storage writes.
export function automaticBackupsAllowed(value:unknown){return value==='true'}
