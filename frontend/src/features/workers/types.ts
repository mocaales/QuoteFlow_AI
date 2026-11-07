// Mirrors backend WorkerRow (GET/PATCH /podjetja/{id}/delavci)
export type Worker = { id: string; uporabnik_id: string; e_posta: string; ime: string; priimek: string; aktivna: boolean; dodeljeno_ob: string };
export type WorkerInput = { e_posta: string };
// Mirrors backend invitation rows (/podjetja/{id}/delavci/povabila); stanje: povabljen | sprejeto | zavrnjeno | preklicano | poteklo
export type Invitation = { id: string; e_posta: string; stanje: string; poslano_ob: string; odloceno_ob?: string | null };
// GET /povabila: open invitations for the signed-in user
export type MyInvitation = { id: string; podjetje_id: string; podjetje_naziv: string; povabil: string; poslano_ob: string };
