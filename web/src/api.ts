/** Appels à l'API. La session est portée par un cookie httpOnly : aucun jeton côté navigateur. */

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public details?: string[],
  ) {
    super(message);
  }
}

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

export async function api<T>(method: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE', url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method,
    credentials: 'same-origin',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = res.headers.get('content-type')?.includes('application/json') ? await res.json() : null;
  if (!res.ok) {
    if (res.status === 401 && !url.endsWith('/api/auth/login')) onUnauthorized?.();
    throw new ApiError(res.status, data?.erreur ?? `Erreur ${res.status}`, data?.details);
  }
  return data as T;
}

export interface Filiale {
  id: number;
  code: string;
  nom: string;
}
export interface Utilisateur {
  id: number;
  identifiant: string;
  prenom: string;
  nom: string;
  email: string | null;
  role: string;
  permissions: string[];
  filiales: Filiale[];
}
export interface Session {
  utilisateur: Utilisateur;
  modeConnexion: 'ldap' | 'local';
}

export const fmtHeures = (h: number) => `${new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 }).format(h)} h`;
export const fmtEuros = (n: number) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n);
export const fmtDate = (s: string | null) => (s ? new Date(`${s}T00:00:00`).toLocaleDateString('fr-FR', { weekday: 'short', day: '2-digit', month: 'short' }) : '—');
export const isoDate = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
export function lundi(d = new Date()) {
  const x = new Date(d);
  x.setDate(x.getDate() - ((x.getDay() + 6) % 7));
  return x;
}
