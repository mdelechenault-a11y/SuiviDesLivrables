import { reactive } from 'vue';
import { api, type Session } from './api';

/** État de la session, partagé par toutes les vues. */
export const session = reactive<{ data: Session | null; charge: boolean }>({ data: null, charge: false });

export async function chargerSession(): Promise<Session | null> {
  try {
    session.data = await api<Session>('GET', '/api/auth/me');
  } catch {
    session.data = null;
  }
  session.charge = true;
  return session.data;
}

export function peut(permission: string): boolean {
  return !!session.data?.utilisateur.permissions.includes(permission);
}

export async function deconnecter() {
  await api('POST', '/api/auth/logout').catch(() => undefined);
  session.data = null;
}
