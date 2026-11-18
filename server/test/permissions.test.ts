import { describe, expect, it } from 'vitest';
import { ALL_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS, isLocked, ROLES } from '../src/security/permissions.js';

describe('matrice de droits par défaut', () => {
  it('donne à chaque rôle le droit de pointer ses heures', () => {
    for (const r of ROLES) expect(DEFAULT_ROLE_PERMISSIONS[r]).toContain('temps.saisir');
  });
  it("réserve les heures des autres aux managers, directeurs et administrateurs", () => {
    const who = ROLES.filter((r) => DEFAULT_ROLE_PERMISSIONS[r].includes('temps.voir_equipe'));
    expect(who.sort()).toEqual(['Admin', 'Directeur', 'Manager']);
  });
  it("donne tout à l'administrateur", () => {
    expect(new Set(DEFAULT_ROLE_PERMISSIONS.Admin)).toEqual(new Set(ALL_PERMISSIONS));
  });
  it("verrouille l'administration des droits pour l'administrateur", () => {
    expect(isLocked('Admin', 'admin.droits')).toBe(true);
    expect(isLocked('Manager', 'finance.voir')).toBe(false);
  });
});
