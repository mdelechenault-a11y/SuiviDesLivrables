<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api, ApiError } from '../../api';
import { chargerSession } from '../../session';

interface Droits {
  roles: string[];
  permissions: Record<string, string>;
  matrice: Record<string, string[]>;
  verrouillees: Array<{ role: string; permission: string }>;
}

const d = ref<Droits | null>(null);
const message = ref('');
const erreur = ref('');

async function charger() {
  d.value = await api<Droits>('GET', '/api/admin/droits');
}
const verrouille = (role: string, p: string) => !!d.value?.verrouillees.some((v) => v.role === role && v.permission === p);
const coche = (role: string, p: string) => !!d.value?.matrice[role]?.includes(p);
function basculer(role: string, p: string) {
  if (!d.value || verrouille(role, p)) return;
  const l = d.value.matrice[role] ?? [];
  d.value.matrice[role] = l.includes(p) ? l.filter((x) => x !== p) : [...l, p];
}
async function enregistrer() {
  message.value = erreur.value = '';
  try {
    await api('PUT', '/api/admin/droits', { matrice: d.value!.matrice });
    message.value = 'Droits enregistrés. Ils s\'appliquent immédiatement à tous les utilisateurs.';
    await chargerSession();
  } catch (e) {
    erreur.value = e instanceof ApiError ? e.message : 'Enregistrement impossible.';
  }
}
onMounted(charger);
</script>

<template>
  <div class="page">
    <div class="top">
      <div><h1>Droits</h1><p>Ce que chaque rôle peut voir et faire. Le serveur vérifie ces droits à chaque action.</p></div>
      <button class="primary" @click="enregistrer">Enregistrer</button>
    </div>
    <p v-if="message" class="success">{{ message }}</p>
    <p v-if="erreur" class="error">{{ erreur }}</p>
    <section v-if="d" class="panel">
      <div class="scroll">
        <table>
          <thead>
            <tr><th>Permission</th><th v-for="r in d.roles" :key="r" style="text-align: center">{{ r }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="(label, p) in d.permissions" :key="p">
              <td>{{ label }}<br /><span class="mono muted" style="font-size: 11px">{{ p }}</span></td>
              <td v-for="r in d.roles" :key="r" style="text-align: center">
                <input
                  type="checkbox"
                  :checked="coche(r, String(p))"
                  :disabled="verrouille(r, String(p))"
                  :title="verrouille(r, String(p)) ? 'Toujours accordé' : ''"
                  :aria-label="`${label} pour ${r}`"
                  @change="basculer(r, String(p))"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="hint">Les cases grisées sont toujours accordées : chacun peut pointer ses heures, et l'administrateur garde la main sur les utilisateurs et les droits.</p>
    </section>
  </div>
</template>
